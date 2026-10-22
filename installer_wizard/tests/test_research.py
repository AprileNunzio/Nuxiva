import time
import unittest
import unittest.mock

import httpx

from features.research import extract, providers, ranking, safeweb, service
from features.research.report import render

PUBLIC = ["93.184.216.34"]

DDG_HTML = '''
<div class="result"><a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.ansa.it%2Fnapoli.html&rut=x">Napoli, la prossima partita</a>
<a class="result__snippet" href="x">Il Napoli giocherà sabato <b>alle 20:45</b> al Maradona.</a></div>
<div class="result"><a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.pinterest.com%2Fpin%2F1&rut=x">Pin</a>
<a class="result__snippet" href="x">spam</a></div>
'''

RSS = '''<?xml version="1.0"?><rss><channel>
<item><title>Napoli, sabato la sfida - ANSA</title><link>https://news.google.com/x</link><pubDate>Wed, 21 Oct 2026 10:00:00 GMT</pubDate><source url="https://www.ansa.it">ANSA</source></item>
</channel></rss>'''


def page(text, url="https://www.ansa.it/a", modified=""):
    return safeweb.Page(url, 200, "text/html", text, modified)


class SafeWebTest(unittest.IsolatedAsyncioTestCase):
    async def test_internal_and_odd_addresses_are_blocked(self):
        for url in ("http://127.0.0.1/", "http://localhost/", "http://10.0.0.5/x", "http://169.254.169.254/latest", "file:///etc/passwd",
                    "ftp://example.com/", "https://user:pw@example.com/", "https://example.com:8443/", "http://[::1]/", "gopher://x"):
            with self.subTest(url=url), unittest.mock.patch.object(safeweb, "_resolve", lambda host: ["127.0.0.1"] if host == "localhost" else PUBLIC):
                with self.assertRaises(safeweb.WebError) as caught:
                    await safeweb.check(url)
                self.assertEqual(caught.exception.code, "blocked_url")

    async def test_hostname_resolving_to_a_private_address_is_blocked(self):
        with unittest.mock.patch.object(safeweb, "_resolve", lambda host: ["192.168.1.9"]):
            with self.assertRaises(safeweb.WebError):
                await safeweb.check("https://evil.example.com/")
        with unittest.mock.patch.object(safeweb, "_resolve", lambda host: PUBLIC):
            await safeweb.check("https://example.com/")

    def client(self, handler):
        real = httpx.AsyncClient
        return unittest.mock.patch.object(safeweb.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))

    async def test_redirect_to_internal_host_is_refused(self):
        def handler(request):
            if request.url.host == "example.com":
                return httpx.Response(302, headers={"location": "http://10.0.0.1/admin"})
            return httpx.Response(200, text="secret", headers={"content-type": "text/html"})

        with unittest.mock.patch.object(safeweb, "_resolve", lambda host: PUBLIC), self.client(handler):
            with self.assertRaises(safeweb.WebError) as caught:
                await safeweb.fetch("https://example.com/")
        self.assertEqual(caught.exception.code, "blocked_url")

    async def test_size_and_type_are_limited(self):
        big = httpx.Response(200, content=b"a" * 50_000, headers={"content-type": "text/html"})
        binary = httpx.Response(200, content=b"\x00", headers={"content-type": "application/octet-stream"})
        with unittest.mock.patch.object(safeweb, "_resolve", lambda host: PUBLIC):
            with self.client(lambda r: big):
                self.assertEqual(len((await safeweb.fetch("https://example.com/", max_bytes=1000)).text), 1000)
            with self.client(lambda r: binary):
                with self.assertRaises(safeweb.WebError) as caught:
                    await safeweb.fetch("https://example.com/")
        self.assertEqual(caught.exception.code, "bad_type")


class ExtractTest(unittest.TestCase):
    HTML = ('<html><head><title>Napoli, partita</title><meta property="article:published_time" content="2026-10-21T08:00:00+00:00"></head>'
            '<body><nav>menu menu menu menu menu menu menu menu menu menu menu</nav><script>var x=1;</script>'
            '<p>Il Napoli giocherà sabato alle 20:45 al Maradona contro l\'Inter nel big match della giornata.</p>'
            '<p>Pubblicità e altro testo non pertinente che riempie la pagina con parole generiche.</p></body></html>')

    def test_readable_skips_navigation_and_scripts(self):
        text = extract.readable(self.HTML)
        self.assertIn("Maradona", text)
        self.assertNotIn("menu", text)
        self.assertNotIn("var x", text)

    def test_date_and_excerpt(self):
        self.assertAlmostEqual(extract.published_of(self.HTML), 1792569600.0, delta=1)
        self.assertEqual(extract.title_of(self.HTML), "Napoli, partita")
        self.assertIn("Maradona", extract.excerpt(extract.readable(self.HTML), "quando gioca il Napoli"))
        self.assertIsNone(extract.published_of("<html></html>"))
        self.assertIsNone(extract.parse_date("not a date"))


class RankingTest(unittest.TestCase):
    def test_trust_and_blocking(self):
        self.assertGreater(ranking.reliability("ansa.it"), ranking.reliability("sconosciuto.xyz"))
        self.assertEqual(ranking.reliability("comune.roma.gov.it"), 0.9)
        self.assertTrue(ranking.blocked("it.pinterest.com"))
        self.assertFalse(ranking.blocked("ansa.it"))
        self.assertEqual(ranking.label(0.9), "alta")
        self.assertEqual(ranking.domain_of("https://www.ansa.it/x"), "ansa.it")

    def test_recent_beats_old_at_equal_trust(self):
        now = time.time()
        self.assertGreater(ranking.score("ansa.it", now - 3600, now), ranking.score("ansa.it", now - 400 * 86400, now))
        self.assertGreater(ranking.freshness(now - 3600, now), ranking.freshness(None, now))


class ProviderTest(unittest.IsolatedAsyncioTestCase):
    async def test_duckduckgo_and_news_parsing(self):
        with unittest.mock.patch.object(providers.safeweb, "fetch", unittest.mock.AsyncMock(return_value=page(DDG_HTML))):
            hits = await providers.duckduckgo("napoli", "it", 0)
        self.assertEqual(hits[0].url, "https://www.ansa.it/napoli.html")
        self.assertIn("alle 20:45", hits[0].snippet)
        with unittest.mock.patch.object(providers.safeweb, "fetch", unittest.mock.AsyncMock(return_value=page(RSS))):
            news = await providers.news("napoli", "it", 0)
        self.assertEqual((news[0].source, news[0].via), ("www.ansa.it", "news"))
        self.assertIsNotNone(news[0].published)

    async def test_entity_expansion_is_refused(self):
        bomb = page('<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><rss></rss>')
        with unittest.mock.patch.object(providers.safeweb, "fetch", unittest.mock.AsyncMock(return_value=bomb)):
            with self.assertRaises(safeweb.WebError):
                await providers.news("x", "it", 0)


class ServiceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        service._cache.clear()
        self.addCleanup(service._cache.clear)

    def patched(self, news=None, web=None, article=None):
        async def provide(rows, *args):
            if isinstance(rows, Exception):
                raise rows
            return rows

        async def fetch(url, **kwargs):
            if article is None:
                raise safeweb.WebError("unreachable")
            return article

        return [unittest.mock.patch.object(providers, "news", lambda *a: provide(news or [], *a)),
                unittest.mock.patch.object(providers, "duckduckgo", lambda *a: provide(web or [], *a)),
                unittest.mock.patch.object(providers, "searxng", lambda *a: provide([], *a)),
                unittest.mock.patch.object(safeweb, "fetch", fetch)]

    async def run_with(self, patches, *args, **kwargs):
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        return await service.research(*args, **kwargs)

    async def test_ranked_sources_with_dates_and_no_social(self):
        now = time.time()
        web = [providers.Hit("Pin", "https://www.pinterest.com/p", "", "pinterest.com", None, "web"),
               providers.Hit("Napoli, la prossima partita", "https://www.ansa.it/napoli.html", "snippet", "ansa.it", None, "web")]
        news = [providers.Hit("Napoli sabato - Blog", "https://blog.example.xyz", "", "blog.example.xyz", now - 90 * 86400, "news"),
                providers.Hit("Napoli sabato alle 20:45 - ANSA", "https://www.ansa.it", "", "ansa.it", now - 3600, "news")]
        article = page(TestArticle.HTML)
        result = await self.run_with(self.patched(news, web, article), "quando gioca il Napoli?")
        self.assertEqual(result["status"], "ok")
        domains = [s["domain"] for s in result["sources"]]
        self.assertNotIn("pinterest.com", domains)
        self.assertEqual(domains[0], "ansa.it")
        self.assertEqual(result["sources"][0]["reliability"], "alta")
        self.assertIn("Maradona", "".join(s["excerpt"] for s in result["sources"]))

    async def test_nothing_found_and_network_down_are_explicit(self):
        empty = await self.run_with(self.patched(), "domanda senza risultati")
        self.assertEqual(empty["status"], "no_results")
        self.assertIn("nessuna fonte affidabile", render(empty))
        service._cache.clear()
        down = await self.run_with(self.patched(safeweb.WebError("unreachable"), safeweb.WebError("unreachable")), "altra domanda")
        self.assertEqual(down["status"], "unavailable")
        self.assertIn("non la fornisco", render(down))

    async def test_days_filter_drops_known_old_sources(self):
        now = time.time()
        news = [providers.Hit("Vecchia notizia - ANSA", "https://www.ansa.it", "", "ansa.it", now - 30 * 86400, "news")]
        result = await self.run_with(self.patched(news), "notizia", days=3)
        self.assertEqual(result["status"], "no_results")

    def test_personal_data_never_leaves_the_house(self):
        cleaned = service.scrub("scrivi a mario@example.com o chiama +39 333 123 4567 IBAN IT60X0542811101000000123456 ip 192.168.1.5 sul Napoli")
        for leaked in ("mario", "333", "IT60", "192.168"):
            self.assertNotIn(leaked, cleaned)
        self.assertIn("Napoli", cleaned)


class TestArticle:
    HTML = ExtractTest.HTML


if __name__ == "__main__":
    unittest.main()


class SettingsTest(unittest.TestCase):
    def test_setting_falls_back_and_clamps(self):
        from features.research import service
        with unittest.mock.patch.object(service, "env_get", return_value="abc"):
            self.assertEqual(service._setting("X", 5, 1, 8), 5)
        with unittest.mock.patch.object(service, "env_get", return_value="99"):
            self.assertEqual(service._setting("X", 5, 1, 8), 8)
