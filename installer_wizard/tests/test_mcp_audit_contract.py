import unittest

from agenti.mcpclient.api import normalized_audit


class AuditContractTest(unittest.TestCase):
    def test_null_records_become_an_empty_list(self):
        out = normalized_audit({"intact": True, "count": 0, "head": "", "records": None})
        self.assertEqual(out["records"], [])

    def test_missing_fields_get_safe_defaults(self):
        out = normalized_audit({})
        self.assertEqual(out, {"intact": False, "error": None, "count": 0, "head": "", "records": []})

    def test_non_object_payload_is_neutralised(self):
        for payload in (None, [], "x", 3):
            self.assertEqual(normalized_audit(payload)["records"], [])

    def test_valid_report_is_preserved(self):
        report = {"schema_version": 1, "intact": True, "error": None, "count": 2, "head": "ab", "records": [{"seq": 1}, {"seq": 2}]}
        self.assertEqual(normalized_audit(report), report)

    def test_invalid_counts_are_rejected(self):
        for count in (-1, True, "3", 1.5, None):
            self.assertEqual(normalized_audit({"count": count})["count"], 0)


if __name__ == "__main__":
    unittest.main()
