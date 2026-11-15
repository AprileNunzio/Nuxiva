import errno
import socket
import ssl
import threading
import unittest

from connection import diagnose
from connection.client import ServerError, first_contact


class KindTest(unittest.TestCase):
    def test_windows_timeout_code_is_a_timeout(self):
        exc = OSError(10060, "timeout")
        exc.winerror = 10060
        self.assertEqual(diagnose.kind_of(exc), "timeout")

    def test_builtin_errors_are_classified(self):
        self.assertEqual(diagnose.kind_of(TimeoutError()), "timeout")
        self.assertEqual(diagnose.kind_of(ConnectionRefusedError(errno.ECONNREFUSED, "no")), "refused")
        self.assertEqual(diagnose.kind_of(socket.gaierror(-2, "name")), "dns")
        self.assertEqual(diagnose.kind_of(ssl.SSLError("x")), "tls")
        self.assertEqual(diagnose.kind_of(OSError(errno.ENETUNREACH, "net")), "unreachable")
        self.assertEqual(diagnose.kind_of(OSError("boh")), "other")

    def test_timeout_message_names_host_port_and_a_command(self):
        text = diagnose.explain(TimeoutError(), "192.168.1.100", 443)
        self.assertIn("192.168.1.100:443", text)
        self.assertNotIn("10060", text)

    def test_loopback_address_is_called_out(self):
        text = diagnose.explain(TimeoutError(), "127.0.0.1", 8443)
        self.assertIn("127.0.0.1:8443", text)


class ProbeTest(unittest.TestCase):
    def test_probe_reports_open_and_closed_ports(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        threading.Thread(target=lambda: listener.accept(), daemon=True).start()
        try:
            lines = diagnose.probe(f"https://127.0.0.1:{port}", timeout=1.0)
        finally:
            listener.close()
        self.assertTrue(any(str(port) in line for line in lines))
        self.assertGreaterEqual(len(lines), 3)

    def test_probe_without_host_does_not_raise(self):
        self.assertEqual(len(diagnose.probe("")), 1)


class ClientTest(unittest.TestCase):
    def test_a_refused_connection_becomes_an_error_with_the_address(self):
        probe = socket.socket()
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()
        with self.assertRaises(ServerError) as caught:
            first_contact(f"https://127.0.0.1:{port}", timeout=1.0)
        self.assertIn(str(port), str(caught.exception))


if __name__ == "__main__":
    unittest.main()
