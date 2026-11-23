import unittest

from intents import senses, site


class SiteIntentTest(unittest.TestCase):
    def test_site_on_named_browser_is_opened_not_searched(self):
        intent = site.parse("aprimi il sito nunziotech.com su google chrome")
        self.assertEqual((intent.url, intent.host, intent.browser), ("https://nunziotech.com", "nunziotech.com", "chrome"))

    def test_languages_and_browsers(self):
        cases = {
            "Apri https://example.com/guida": ("https://example.com/guida", ""),
            "vai su www.example.org con firefox": ("https://www.example.org", "firefox"),
            "open github.com in edge": ("https://github.com", "edge"),
            "ouvre le site exemple.fr dans brave": ("https://exemple.fr", "brave"),
            "abre el sitio ejemplo.es en opera": ("https://ejemplo.es", "opera"),
            "aprimi il sito nunziotech.com.": ("https://nunziotech.com", ""),
        }
        for text, expected in cases.items():
            intent = site.parse(text)
            self.assertIsNotNone(intent, text)
            self.assertEqual((intent.url, intent.browser), expected, text)

    def test_files_apps_and_chat_are_not_sites(self):
        for text in ("apri il file report.docx", "apri chrome", "bene grazie e a te?", "apri il sito foo.dwg",
                     "apri nunziotech.com e google.com", "come va oggi?", "apri C:\\dati\\nunziotech.com"):
            self.assertIsNone(site.parse(text), text)

    def test_credentials_and_unsafe_targets_are_rejected(self):
        for text in ("apri https://user:pw@evil.com", "apri http://evil.com:99999", "apri javascript:alert(1)",
                     "apri " + "a" * 400 + ".com"):
            self.assertIsNone(site.parse(text), text)


class SensesIntentTest(unittest.TestCase):
    def test_webcam_only_when_asked(self):
        self.assertTrue(senses.asks_webcam("Guardami dalla webcam"))
        self.assertTrue(senses.asks_webcam("can you see me?"))
        self.assertFalse(senses.asks_webcam("aprimi il sito nunziotech.com su google chrome"))
        self.assertFalse(senses.asks_webcam("bene grazie e a te?"))

    def test_screen_hint(self):
        self.assertTrue(senses.asks_screen("Guarda il mio schermo e dimmi cosa vedi"))
        self.assertFalse(senses.asks_screen("apri nunziotech.com"))


if __name__ == "__main__":
    unittest.main()
