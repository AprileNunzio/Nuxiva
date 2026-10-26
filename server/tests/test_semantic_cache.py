import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from server.config.env import settings
from server.core.memory.cache_policy import CacheScope, PureResultPolicy
from server.core.memory.semantic_cache import SemanticCache

ANSWERS = {"2+2": 4, "due più due": 4, "3+3": 6, "2+3": 5, "4+4": 8}


def verified_math(query, result, context):
    return query.strip() in ANSWERS and result == pure_result(ANSWERS[query.strip()])


def pure_result(value):
    return {"agent_id": "pure_math", "speech_output": str(value), "result_data": {"value": value}}


class TestSemanticCache(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "semantic_cache.json"
        self.now = 10000.0
        self.scope = CacheScope("alice", "kiosk", {"locale": "it", "knowledge_revision": 1}, "revision-1")
        self.policy = PureResultPolicy("pure-math.v1", verified_math, ttl_seconds=30)
        self.flags = mock.patch.multiple(settings, SEMANTIC_CACHE_ENABLED=True, NUXIVA_SECRET_KEY="cache-test-secret-identity")
        self.flags.start()
        self.addCleanup(self.flags.stop)
        self.cache = self.new_cache()

    def new_cache(self, **kwargs):
        return SemanticCache(storage_path=str(self.path), clock=lambda: self.now, **kwargs)

    async def record(self, query="2+2", result=None, embedding=None, **kwargs):
        return await self.cache.record_success(query, pure_result(ANSWERS[query]) if result is None else result,
                                                embedding=embedding, scope=kwargs.get("scope", self.scope),
                                                policy=kwargs.get("policy", self.policy))

    async def lookup(self, query="2+2", embedding=None, **kwargs):
        return await self.cache.lookup(query, embedding, scope=kwargs.get("scope", self.scope),
                                       policy=kwargs.get("policy", self.policy))

    async def test_exact_match_requires_a_code_verifier_and_explicit_scope(self):
        self.assertIsNotNone(await self.record())
        hit = await self.lookup()
        self.assertTrue(hit.hit)
        self.assertEqual(hit.strategy, "exact")
        self.assertEqual(hit.action_result, pure_result(4))
        self.assertFalse((await self.cache.lookup("2+2")).hit)
        self.assertFalse((await self.lookup(policy={"pure": True, "verified": True})).hit)
        self.assertIsNone(await self.cache.record_success("3+3", pure_result(6)))

    async def test_user_device_context_and_revision_are_isolated(self):
        await self.record(embedding=[1.0, 0.0])
        scopes = [CacheScope("bob", "kiosk", self.scope.context, self.scope.revision),
                  CacheScope("alice", "phone", self.scope.context, self.scope.revision),
                  CacheScope("alice", "kiosk", {"locale": "en", "knowledge_revision": 1}, self.scope.revision),
                  CacheScope("alice", "kiosk", self.scope.context, "revision-2")]
        semantic = PureResultPolicy("pure-math.v1", verified_math, 30, allow_semantic=True)
        for scope in scopes:
            with self.subTest(scope=scope):
                self.assertFalse((await self.lookup(scope=scope)).hit)
                self.assertFalse((await self.lookup("due più due", [1.0, 0.0], scope=scope, policy=semantic)).hit)

    async def test_context_digest_is_canonical_and_does_not_expose_secrets(self):
        context = {"nested": {"token": "private-context-token", "revision": 2}, "locale": "it"}
        scope = CacheScope("private-user-id", "private-device-id", context, "private-revision")
        await self.record(scope=scope)
        reordered = CacheScope(scope.user_id, scope.device_id, {"locale": "it", "nested": {"revision": 2, "token": "private-context-token"}}, scope.revision)
        self.assertTrue((await self.lookup(scope=reordered)).hit)
        keys = " ".join(self.cache._entries)
        for value in ("private-context-token", "private-user-id", "private-device-id", "2+2"):
            self.assertNotIn(value, keys)
            self.assertNotIn(value.encode(), self.path.read_bytes())
        self.assertTrue(all(len(key) == 64 for key in self.cache._entries))

    async def test_changed_context_snapshot_invalidates_an_existing_scope_object(self):
        context = {"knowledge_revision": 1}
        scope = CacheScope("alice", "kiosk", context, "revision-1")
        await self.record(scope=scope)
        context["knowledge_revision"] = 2
        self.assertFalse((await self.lookup(scope=scope)).hit)

    async def test_ttl_expires_without_sliding_extension_and_survives_restart(self):
        await self.record()
        self.now += 29
        self.assertTrue((await self.lookup()).hit)
        reloaded = self.new_cache()
        self.assertTrue(reloaded.lookup_sync("2+2", scope=self.scope, policy=self.policy).hit)
        self.now += 1
        self.assertFalse((await self.lookup()).hit)
        self.assertFalse(reloaded.lookup_sync("2+2", scope=self.scope, policy=self.policy).hit)
        self.assertEqual(self.cache.stats()["entries_count"], 0)

    async def test_shortened_policy_ttl_is_respected_on_lookup(self):
        await self.record()
        self.now += 5
        shorter = PureResultPolicy("pure-math.v1", verified_math, ttl_seconds=2)
        self.assertFalse((await self.lookup(policy=shorter)).hit)

    async def test_semantic_reuse_is_opt_in_and_reverified_for_the_current_query(self):
        await self.record(embedding=[0.8, 0.6, 0.0])
        self.assertFalse((await self.lookup("due più due", [0.79, 0.61, 0.0])).hit)
        policy = PureResultPolicy("pure-math.v1", verified_math, 30, allow_semantic=True)
        hit = await self.lookup("due più due", [0.79, 0.61, 0.0], policy=policy)
        self.assertTrue(hit.hit)
        self.assertEqual(hit.strategy, "semantic")
        self.assertFalse((await self.lookup("3+3", [0.8, 0.6, 0.0], policy=policy)).hit)

    async def test_similarity_candidates_with_different_dimensions_do_not_crash(self):
        await self.record(embedding=[1.0, 0.0])
        await self.record("3+3", embedding=[1.0, 0.0, 0.0])
        policy = PureResultPolicy("pure-math.v1", verified_math, 30, allow_semantic=True)
        self.assertTrue((await self.lookup("due più due", [1.0, 0.0], policy=policy)).hit)
        self.assertFalse((await self.lookup("due più due", [1.0, 0.0, 0.0], policy=policy)).hit)

    async def test_invalid_or_nonfinite_embeddings_are_rejected(self):
        await self.record()
        for vector in ([math.nan], [math.inf], [0.0, 0.0], [True], ["invalid"], [1.0] * 4097):
            with self.subTest(vector_length=len(vector)):
                self.assertIsNone(await self.record(embedding=vector))
                self.assertFalse((await self.lookup(embedding=vector)).hit)
        self.assertIsNotNone(await self.record(embedding=[1e308, 1e308]))
        self.assertTrue(math.isfinite(self.cache._cosine_similarity([1e308, 1e308], [1e308, 1e308])))

    async def test_actions_tools_surfaces_and_variable_sensor_data_are_never_recorded(self):
        permissive_code = PureResultPolicy("test-only-structural-guard", lambda *args: True)
        results = [{"agent_id": "home_assistant", "speech_output": "Luce accesa"},
                   {"agent_id": "browser_agent", "speech_output": "Ho aperto il browser"},
                   {"speech_output": "ok", "result_data": {"action": "turn_on"}},
                   {"speech_output": "ok", "result_data": {"surface": "whiteboard"}},
                   {"speech_output": "ok", "result_data": {"tool_calls": ["switch"]}},
                   {"speech_output": "20", "result_data": {"temperature": 20}},
                   {"speech_output": "20", "sensor": "temperature"},
                   {"action_vector": [1.0], "reward_score": 0.99}]
        for result in results:
            with self.subTest(result=result):
                self.assertIsNone(await self.cache.record_success("accendi luce", result, scope=self.scope, policy=permissive_code))
        self.assertEqual(self.cache.stats()["entries_count"], 0)

    async def test_failed_verification_is_not_recorded_and_changed_verifier_blocks_reuse(self):
        self.assertIsNone(await self.record(result=pure_result(5)))
        await self.record()
        changed = PureResultPolicy("pure-math.v1", lambda *args: False)
        self.assertFalse((await self.lookup(policy=changed)).hit)

    async def test_settings_disabled_bypasses_lookup_record_and_disk_load(self):
        await self.record()
        with mock.patch.object(settings, "SEMANTIC_CACHE_ENABLED", False):
            self.assertFalse((await self.lookup()).hit)
            self.assertIsNone(await self.record("3+3"))
            with mock.patch("server.core.memory.cache_storage.EncryptedCacheStorage.load") as load:
                self.new_cache()
            load.assert_not_called()

    async def test_cache_count_and_storage_size_are_bounded(self):
        self.cache = self.new_cache(max_entries=2, max_storage_bytes=4096)
        await self.record("2+2")
        await self.record("3+3")
        await self.record("2+3")
        self.assertLessEqual(self.cache.stats()["entries_count"], 2)
        self.assertFalse((await self.lookup("2+2")).hit)
        self.assertLessEqual(self.path.stat().st_size, 4096)
        oversized = {"speech_output": "x" * 40000}
        self.assertIsNone(await self.record(result=oversized, policy=PureResultPolicy("test-only-size", lambda *args: True)))

    async def test_invalidating_one_scope_preserves_other_users(self):
        bob = CacheScope("bob", "phone", {}, "revision-1")
        await self.record()
        await self.record(scope=bob)
        self.assertEqual(self.cache.invalidate(scope=self.scope), 1)
        self.assertFalse((await self.lookup()).hit)
        self.assertTrue((await self.lookup(scope=bob)).hit)
        self.assertEqual(self.cache.invalidate(policy_id=self.policy.policy_id), 1)
        self.assertEqual(self.new_cache().stats()["entries_count"], 0)

    async def test_plaintext_legacy_and_encrypted_unscoped_records_are_not_reused(self):
        self.path.write_text(json.dumps([{"query": "accendi luce", "action_result": {"speech_output": "Luce accesa"}}]))
        with self.assertLogs("nuxiva.semantic_cache", level="WARNING"):
            legacy = self.new_cache()
        self.assertEqual(legacy.stats()["entries_count"], 0)
        self.cache._storage.save([{"query": "2+2", "action_result": pure_result(4), "created_at": self.now}])
        with self.assertLogs("nuxiva.semantic_cache", level="WARNING"):
            legacy = self.new_cache()
        self.assertEqual(legacy.stats()["entries_count"], 0)

    async def test_ciphertext_tampering_or_secret_rotation_makes_records_unusable(self):
        await self.record()
        encrypted = bytearray(self.path.read_bytes())
        encrypted[len(encrypted) // 2] ^= 1
        self.path.write_bytes(encrypted)
        with self.assertLogs("nuxiva.semantic_cache", level="WARNING"):
            self.assertEqual(self.new_cache().stats()["entries_count"], 0)
        await self.record()
        with mock.patch.object(settings, "NUXIVA_SECRET_KEY", "rotated-test-key"), \
                self.assertLogs("nuxiva.semantic_cache", level="WARNING"):
            self.assertEqual(self.new_cache().stats()["entries_count"], 0)

    async def test_failed_atomic_replace_preserves_previous_cache_and_logs_io_failure(self):
        await self.record()
        original = self.path.read_bytes()
        with mock.patch("server.core.memory.cache_storage.os.replace", side_effect=OSError("unavailable")), \
                self.assertLogs("nuxiva.semantic_cache", level="ERROR"):
            await self.record("3+3")
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(Path(self.temporary.name).glob(".semantic-cache-*.tmp")), [])
        self.assertTrue(self.new_cache().lookup_sync("2+2", scope=self.scope, policy=self.policy).hit)

    async def test_returned_payload_cannot_mutate_the_stored_result(self):
        result = pure_result(4)
        await self.record(result=result)
        result["result_data"]["value"] = 5
        hit = await self.lookup()
        hit.action_result["result_data"]["value"] = 6
        self.assertEqual((await self.lookup()).action_result, pure_result(4))

    async def test_invalid_scope_is_rejected_without_leaking_context_to_logs(self):
        invalid = CacheScope("alice", "kiosk", {"secret": "private-value", "bad": math.nan}, "revision-1")
        with self.assertLogs("nuxiva.semantic_cache", level="WARNING") as logs:
            self.assertIsNone(await self.record(scope=invalid))
        self.assertNotIn("private-value", " ".join(logs.output))
        self.assertIsNone(await self.record(scope=CacheScope("", "kiosk", {}, "revision-1")))

    async def test_stats_only_count_real_hits(self):
        await self.record()
        await self.lookup()
        await self.lookup("3+3")
        stats = self.cache.stats()
        self.assertEqual(stats["entries_count"], 1)
        self.assertEqual(stats["total_lookups"], 2)
        self.assertEqual(stats["total_hits"], 1)
        self.assertEqual(stats["hit_rate"], 0.5)
