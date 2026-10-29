import importlib
import unittest


def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite()
    for name in ['identification', 'repositories', 'dkms_cases', 'catalog_gpu', 'agent_cases', 'security_cases', 'lifecycle_cases']:
        module = importlib.import_module(__package__ + ".hardware_cases." + name)
        suite.addTests(loader.loadTestsFromModule(module))
    return suite
