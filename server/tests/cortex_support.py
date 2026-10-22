import unittest

from server.core.core_platform.native_bridge import load_native

NATIVE_AVAILABLE = load_native().is_ok
requires_native = unittest.skipUnless(NATIVE_AVAILABLE, "nuxiva_native with cortex support is not installed")
SECRET = "unit-test-master-secret-0123456789abcdef"
