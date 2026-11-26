import asyncio
import unittest

from agenti.cloud import servers
from agenti.cloud.catalog import FLAVORS
from agenti.cloud.studio import FLAVOR, harden, private_host, studio_addresses


class StudioAddressTests(unittest.TestCase):
    def test_private_addresses_gain_the_default_port_and_version(self):
        self.assertEqual(studio_addresses("http://192.168.1.20"), ("http://192.168.1.20:8888", "http://192.168.1.20:8888/v1"))
        self.assertEqual(studio_addresses("http://127.0.0.1:8000/v1/"), ("http://127.0.0.1:8000", "http://127.0.0.1:8000/v1"))
        self.assertEqual(servers.addresses(FLAVOR, "10.0.0.7:8888"), ("http://10.0.0.7:8888", "http://10.0.0.7:8888/v1"))

    def test_public_hosts_need_tls_and_credentials_in_urls_are_refused(self):
        with self.assertRaises(ValueError):
            studio_addresses("http://8.8.8.8:8888")
        with self.assertRaises(ValueError):
            studio_addresses("http://studio.example.org")
        with self.assertRaises(ValueError):
            studio_addresses("http://user:pw@127.0.0.1:8888")
        self.assertEqual(studio_addresses("https://studio.example.org")[1], "https://studio.example.org/v1")

    def test_private_host_classification(self):
        for host in ("localhost", "127.0.0.1", "10.1.2.3", "172.16.0.9", "192.168.0.2", "100.100.1.1", "[fd00::1]"):
            self.assertTrue(private_host(host), host)
        for host in ("8.8.8.8", "169.254.1.1", "example.org", "[2606:4700::1111]"):
            self.assertFalse(private_host(host), host)


class StudioHardeningTests(unittest.TestCase):
    def test_server_tools_are_always_switched_off_for_the_studio(self):
        body = {"model": "m", "enable_tools": True, "enabled_tools": ["terminal"], "tools": [{}], "session_id": "x"}
        hardened = harden(body, {"flavor": FLAVOR})
        self.assertEqual(hardened, {"model": "m", "enable_tools": False})

    def test_other_servers_are_left_untouched(self):
        body = {"model": "m", "tools": [{}]}
        self.assertEqual(harden(dict(body), {"flavor": "openai"}), body)

    def test_the_flavor_is_offered_and_needs_a_key(self):
        self.assertIn(FLAVOR, FLAVORS)
        result = asyncio.run(servers.test(FLAVOR, "http://127.0.0.1:8888", ""))
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
