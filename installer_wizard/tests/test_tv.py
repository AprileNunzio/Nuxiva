import asyncio
import tempfile
import unittest
from pathlib import Path

from sealed import SealedFile

from features.nodes.inbox import Inbox
from features.tv import m3u, relay, targets
from features.tv.store import TvStore

PLAYLIST = """#EXTM3U url-tvg="http://epg.example/x.xml"
#EXTINF:-1 tvg-id="rai1.it" tvg-logo="http://logo.example/rai1.png" group-title="Italia",Rai 1 HD
http://iptv.example/live/user/pass/1.m3u8
#EXTINF:-1 group-title="Italia",Rai 10
http://iptv.example/live/user/pass/10.ts
#EXTINF:-1,Bad <script>
javascript:alert(1)
#EXTINF:-1 tvg-logo="ftp://x",Canale 5 (backup)
https://cdn.example/c5/index.m3u8
"""


class M3uTest(unittest.TestCase):
    def test_parse_skips_unsafe_and_keeps_metadata(self):
        rows = m3u.parse(PLAYLIST)
        self.assertEqual([r["name"] for r in rows], ["Rai 1 HD", "Rai 10", "Canale 5 (backup)"])
        self.assertEqual((rows[0]["group"], rows[0]["tvg_id"], rows[0]["logo"]), ("Italia", "rai1.it", "http://logo.example/rai1.png"))
        self.assertEqual(rows[2]["logo"], "")

    def test_not_a_playlist(self):
        with self.assertRaises(m3u.PlaylistError):
            m3u.parse("<html>login</html>")

    def test_find_respects_numbers_and_quality_tags(self):
        rows = m3u.parse(PLAYLIST)
        self.assertEqual(m3u.find(rows, "metti rai 1 sul pc")["name"], "Rai 1 HD")
        self.assertEqual(m3u.find(rows, "guarda rai 10")["name"], "Rai 10")
        self.assertEqual(m3u.find(rows, "canale 5")["name"], "Canale 5 (backup)")
        self.assertIsNone(m3u.find(rows, "accendi la luce"))


class RelayTest(unittest.TestCase):
    def test_segment_urls_are_signed(self):
        path = relay.encode("abcd", "http://cdn.example/s1.ts", "tok")
        q = dict(p.split("=", 1) for p in path.split("?", 1)[1].split("&"))
        self.assertEqual(relay.decode("abcd", q["u"], q["s"]), "http://cdn.example/s1.ts")
        with self.assertRaises(relay.RelayError):
            relay.decode("other", q["u"], q["s"])

    def test_rewrite_keeps_tags_and_blocks_internal_hosts(self):
        text = '#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI="key.bin"\nseg1.ts\nhttp://192.168.1.1/admin\n'
        out = relay.rewrite(text, "http://cdn.example/live/index.m3u8", "abcd", "tok", "http://cdn.example/live/index.m3u8")
        lines = out.splitlines()
        self.assertTrue(lines[1].startswith("#EXT-X-KEY:METHOD=AES-128,URI=\"/api/tv/seg/abcd?"))
        self.assertTrue(lines[2].startswith("/api/tv/seg/abcd?"))
        self.assertEqual(lines[3], "#rimosso")

    def test_dash_manifest_is_routed_through_signed_relay(self):
        text = ('<?xml version="1.0"?>\n<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" xmlns:cenc="urn:mpeg:cenc:2013" type="dynamic">'
                '<Location>https://cdn.example/live/Manifest.mpd</Location><PatchLocation>patch.mpp</PatchLocation>'
                '<UTCTiming schemeIdUri="urn:mpeg:dash:utc:http-xsdate:2014" value="https://time.example/now"/>'
                '<Period><AdaptationSet><ContentProtection cenc:default_KID="00"/>'
                '<SegmentTemplate media="$RepresentationID$/seg-$Number$.m4s" initialization="/abs/$RepresentationID$/init.mp4"/>'
                '<Representation id="v1"><BaseURL>http://192.168.1.1/admin/</BaseURL></Representation>'
                '<Representation id="v2"><BaseURL>https://edge.example/v2/</BaseURL>'
                '<SegmentList><SegmentURL media="https://edge.example/v2/s1.m4s"/></SegmentList></Representation>'
                '</AdaptationSet></Period></MPD>')
        out = relay.rewrite_dash(text, "https://cdn.example/live/Manifest.mpd?x=1", "abcd", "1.tok", "https://cdn.example/live/Manifest.mpd")
        self.assertIn('xmlns="urn:mpeg:dash:schema:mpd:2011"', out)
        self.assertIn("cenc:default_KID", out)
        self.assertNotIn("PatchLocation", out)
        self.assertNotIn("192.168.1.1", out)
        root = relay.ET.fromstring(out)
        ns = "{urn:mpeg:dash:schema:mpd:2011}"
        base = root.find(f"{ns}BaseURL").text
        self.assertTrue(base.startswith("/api/tv/dash/abcd/1.tok/"))
        self.assertTrue(base.endswith("/live/"))
        self.assertTrue(root.find(f"{ns}Location").text.startswith("/api/tv/seg/abcd?"))
        self.assertTrue(root.find(f"{ns}UTCTiming").get("value").startswith("/api/tv/seg/abcd?"))
        template = root.find(f"{ns}Period/{ns}AdaptationSet/{ns}SegmentTemplate")
        self.assertEqual(template.get("media"), "$RepresentationID$/seg-$Number$.m4s")
        self.assertTrue(template.get("initialization").startswith("/api/tv/dash/abcd/1.tok/"))
        self.assertTrue(template.get("initialization").endswith("/abs/$RepresentationID$/init.mp4"))
        reps = root.findall(f"{ns}Period/{ns}AdaptationSet/{ns}Representation")
        self.assertIsNone(reps[0].find(f"{ns}BaseURL"))
        edge = reps[1].find(f"{ns}BaseURL").text
        self.assertTrue(edge.endswith("/v2/"))
        self.assertNotEqual(edge.split("/")[6], base.split("/")[6])
        segment = reps[1].find(f"{ns}SegmentList/{ns}SegmentURL").get("media")
        self.assertTrue(segment.startswith(edge.rsplit("/v2/", 1)[0]))

    def test_dash_target_requires_signature_and_same_origin(self):
        prefix = relay.dash_prefix("abcd", "https://cdn.example", "1.tok")
        base = prefix.split("/")[6]
        self.assertEqual(relay.dash_target("abcd", base, "live/v1/seg-7.m4s", "k=1"), "https://cdn.example/live/v1/seg-7.m4s?k=1")
        self.assertEqual(relay.dash_target("abcd", base, "live/a b.m4s"), "https://cdn.example/live/a%20b.m4s")
        self.assertEqual(relay.dash_target("abcd", base, "/evil.example/x"), "https://cdn.example/evil.example/x")
        forged = base[:-1] + ("1" if base.endswith("0") else "0")
        for cid, bad, rest in (("other", base, "x"), ("abcd", forged, "x"), ("abcd", "nope", "x"), ("abcd", base, "a\\b"), ("abcd", base, "a\r\nb")):
            with self.assertRaises(relay.RelayError):
                relay.dash_target(cid, bad, rest)

    def test_dash_rejects_entities_and_foreign_documents(self):
        for text in ('<!DOCTYPE MPD [<!ENTITY a "x">]><MPD xmlns="urn:mpeg:dash:schema:mpd:2011">&a;</MPD>',
                     '<html><body/></html>', '<MPD><unclosed></MPD>'):
            with self.assertRaises(relay.RelayError):
                relay.rewrite_dash(text, "https://cdn.example/a.mpd", "abcd", "1.tok", "https://cdn.example/a.mpd")
        self.assertTrue(relay.is_dash("https://cdn.example/x/Manifest.mpd", "text/plain"))
        self.assertTrue(relay.is_dash("https://cdn.example/x", "application/dash+xml; charset=utf-8"))
        self.assertFalse(relay.is_dash("https://cdn.example/x.m3u8", "application/vnd.apple.mpegurl"))

    def test_private_origin_may_use_private_segments(self):
        self.assertTrue(relay.allowed("http://192.168.1.5/live.m3u8", "http://192.168.1.5/seg.ts"))
        self.assertFalse(relay.allowed("http://cdn.example/a.m3u8", "http://127.0.0.1/x"))
        self.assertFalse(relay.allowed("http://cdn.example/a.m3u8", "file:///etc/passwd"))


class StoreTest(unittest.TestCase):
    def test_add_find_favorite_remove(self):
        with tempfile.TemporaryDirectory() as root:
            store = TvStore(SealedFile(Path(root) / "tv.vault", Path(root) / "tv.key"))
            entry = store.add("Prova", text=PLAYLIST)
            self.assertEqual(entry["count"], 3)
            self.assertNotIn("url", store.playlists()[0])
            ch = store.find("rai 1")
            store.set_favorite(ch["id"], True)
            again = TvStore(SealedFile(Path(root) / "tv.vault", Path(root) / "tv.key"))
            self.assertEqual(again.favorites(), [ch["id"]])
            self.assertNotIn(b"iptv.example", (Path(root) / "tv.vault").read_bytes())
            tuners = again.tuners()
            self.assertIsInstance(tuners, list)
            # Aggiunta manuale di tuner reale specificato dall'utente
            tuner = again.add_tuner("HDHomeRun Salotto", "hdhomerun", "192.168.1.150:65001")
            self.assertEqual(tuner["name"], "HDHomeRun Salotto")
            scanned = again.scan_tuner(tuner["id"])
            self.assertEqual(scanned["status"], "online")
            # Impostazioni VPN obbligatoria
            settings = again.update_settings({"vpn_required": True, "vpn_profile": "wg-home"})
            self.assertTrue(settings["vpn_required"])
            self.assertEqual(settings["vpn_profile"], "wg-home")
            # EPG per canale
            epg_data = again.epg(ch["id"])
            self.assertEqual(epg_data["channel_id"], ch["id"])
            self.assertIn("available", epg_data)
            again.remove(entry["id"])
            self.assertEqual(again.channels(), [])


class TargetTest(unittest.TestCase):
    ROWS = [{"id": "display", "kind": "display", "name": "Schermi di Nuxiva", "online": True},
            {"id": "pc:studio-pc", "kind": "pc", "name": "Studio PC", "online": True},
            {"id": "cast:abc", "kind": "cast", "name": "Salotto TV", "online": True}]

    def test_resolve_phrases(self):
        self.assertEqual(targets.resolve("metti rai 1 sul pc", self.ROWS)["id"], "pc:studio-pc")
        self.assertEqual(targets.resolve("rai 1 sulla salotto tv", self.ROWS)["id"], "cast:abc")
        self.assertEqual(targets.resolve("rai 1 sul chromecast", self.ROWS)["id"], "cast:abc")
        self.assertIsNone(targets.resolve("metti rai 1", self.ROWS))

    def test_target_ids_are_validated(self):
        for bad in ("pc:../../x", "shell:rm", "display:999"):
            self.assertFalse(targets.TARGET.match(bad), bad)


class InboxTest(unittest.IsolatedAsyncioTestCase):
    async def test_long_poll_wakes_on_push(self):
        box = Inbox()
        waiter = asyncio.create_task(box.wait("pc1", 2))
        await asyncio.sleep(0.05)
        box.push("pc1", {"type": "tv", "url": "http://x/tv/watch?c=1"})
        self.assertEqual((await waiter)[0]["type"], "tv")
        self.assertEqual(await box.wait("pc1", 0.05), [])


if __name__ == "__main__":
    unittest.main()
