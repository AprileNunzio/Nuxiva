import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
SYS_DIRS = [ROOT, BACKEND]
for p in SYS_DIRS:
    import sys
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from config import FEATURES_DIR, SKILLS_DIR, STATE_DIR, UI_LANGUAGES, WEB_DIR, WIDGETS_DIR
from features.locale.colocated.domain import Locale, Scope, tokens_of
from features.locale.colocated.errors import ScopeRejected
from features.locale.colocated.repository import LanguageFileRepository
from features.locale.colocated.resolver import BundleResolver
from features.locale.colocated.roots import ScopeRoots


class ColocatedI18nCatalogTests(unittest.TestCase):
    def setUp(self):
        self.roots = ScopeRoots({
            "features": (FEATURES_DIR, STATE_DIR / "features"),
            "web": (WEB_DIR,),
            "skills": (SKILLS_DIR,),
            "widgets": (WIDGETS_DIR,),
        })
        self.repository = LanguageFileRepository()
        self.resolver = BundleResolver(self.roots, self.repository, ("en", "it"))

    def test_scope_validation_prevents_directory_traversal(self):
        invalid_scopes = [
            "../features/cameras",
            "features/../../etc",
            "features//cameras",
            "/features/cameras",
            "features/cameras/",
            "unknown_root/cameras",
        ]
        for scope_str in invalid_scopes:
            with self.subTest(scope=scope_str):
                with self.assertRaises((ScopeRejected, Exception)):
                    parsed = Scope.parse(scope_str)
                    list(self.roots.candidates(parsed, "it"))

    def test_cameras_colocated_bundle_keys_and_tokens_parity(self):
        scope = Scope.parse("features/cameras")
        languages = ["it", "en", "fr"]
        dictionaries = {}

        for code in languages:
            locale = Locale.parse(code, frozenset(UI_LANGUAGES))
            bundle = self.resolver.resolve(scope, locale)
            dictionaries[code] = bundle.dictionary
            self.assertEqual(len(bundle.fallback_keys), 0)

        base_keys = set(dictionaries["it"].keys())
        for code in ["en", "fr"]:
            with self.subTest(lang=code):
                self.assertEqual(set(dictionaries[code].keys()), base_keys)

        for key in base_keys:
            it_tokens = tokens_of(dictionaries["it"][key])
            for code in ["en", "fr"]:
                with self.subTest(key=key, lang=code):
                    self.assertEqual(tokens_of(dictionaries[code][key]), it_tokens)

    def test_all_declared_colocated_language_files_follow_contract(self):
        for lang_dir in ROOT.rglob("language"):
            if not lang_dir.is_dir() or "node_modules" in lang_dir.parts:
                continue
            for json_file in lang_dir.glob("*.json"):
                origin = f"{json_file.parent.parent.name}/{json_file.name}"
                try:
                    data = json.loads(json_file.read_text(encoding="utf-8"))
                except Exception as exc:
                    self.fail(f"Corrupted JSON in {origin}: {exc}")

                if "dictionary" in data:
                    self.assertIsInstance(data["dictionary"], dict, f"dictionary must be dict in {origin}")
                    if "meta" in data and isinstance(data["meta"], dict):
                        decl = data["meta"].get("locale")
                        if decl:
                            self.assertEqual(decl, json_file.stem, f"locale mismatch in {origin}")


if __name__ == "__main__":
    unittest.main()
