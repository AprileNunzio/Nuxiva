import unittest

from server.core.orchestrator.browser_reply import browser_query, browser_speech


class BrowserReplyTest(unittest.TestCase):
    def test_domain_is_extracted_instead_of_the_whole_sentence(self):
        self.assertEqual(browser_query("aprimi il sito nunziotech.com su google chrome"), "nunziotech.com")
        self.assertEqual(browser_query("vai su https://example.org/guida."), "https://example.org/guida")

    def test_command_words_and_browser_tail_are_removed(self):
        self.assertEqual(browser_query("apri il sito di repubblica"), "repubblica")
        self.assertEqual(browser_query("vai su youtube su chrome"), "youtube")

    def test_speech_never_claims_a_search_that_failed(self):
        self.assertNotIn("Ho cercato", browser_speech("nunziotech.com", False))
        self.assertIn("nunziotech.com", browser_speech("nunziotech.com", True))
        self.assertNotIn("Ho aperto il browser", browser_speech("nunziotech.com", True))


if __name__ == "__main__":
    unittest.main()
