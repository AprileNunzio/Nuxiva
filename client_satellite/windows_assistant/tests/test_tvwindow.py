import unittest

from app import tvwindow


class TrustedUrlTest(unittest.TestCase):
    def test_only_nuxiva_tv_pages_open(self):
        self.assertTrue(tvwindow.trusted("http://192.168.1.10:8080/tv/watch?c=ab&t=1", "nuxiva.local:8443"))
        self.assertTrue(tvwindow.trusted("http://nuxiva.local:8080/tv/watch?c=ab", "nuxiva.local:8443"))
        for url in ("https://evil.example/tv/watch?c=1", "http://192.168.1.10:8080/admin", "file:///C:/x",
                    "http://192.168.1.10/tv/watch", "javascript:alert(1)"):
            self.assertFalse(tvwindow.trusted(url, "nuxiva.local:8443"), url)


class WidgetsUrlTest(unittest.TestCase):
    def test_only_the_one_time_screen_link_is_built(self):
        self.assertEqual(tvwindow.widgets_url("https://nuxiva.local:8443/", "/screen/open?t=abc"),
                         "https://nuxiva.local:8443/screen/open?t=abc")
        for path in ("https://evil.example/screen/open?t=a", "//evil.example/screen/open?t=a", "/admin", "/screen/open"):
            with self.assertRaises(ValueError):
                tvwindow.widgets_url("https://nuxiva.local:8443", path)


if __name__ == "__main__":
    unittest.main()
