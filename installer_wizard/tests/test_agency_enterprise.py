import json
import unittest
from unittest.mock import patch

from agenti.agency.office import ROLE_PROFILES, _build_ceo, _profile
from agenti.agency.tools import Context, call


class TestAgencyEnterprise(unittest.IsolatedAsyncioTestCase):
    def test_enterprise_roles_registered(self):
        for role_key in ("customer", "finance", "sales", "integrations"):
            self.assertIn(role_key, ROLE_PROFILES)
            prof = _profile(role_key, "")
            self.assertTrue(len(prof["skills"]) >= 4)
            self.assertIn("NunzioTech", prof["prompt"])

    def test_ceo_omnichannel_dispatching_skills(self):
        ceo = _build_ceo({}, "Automate company", "Executive Plan", [], [])
        self.assertEqual(ceo["role"], "ceo")
        self.assertIn("omnichannel-dispatching", ceo["skills"])
        self.assertIn("invoice-compliance", ceo["skills"])
        self.assertIn("enterprise-mcp", ceo["skills"])

    async def test_read_invoice_sdi_xml(self):
        xml_sample = (
            '<p:FatturaElettronica xmlns:p="http://ivaservizi.agenziaentrate.gov.it">\n'
            '  <FatturaElettronicaHeader>\n'
            '    <CedentePrestatore><DatiAnagrafici><Denominazione>Fornitore SRL</Denominazione><IdCodice>12345678901</IdCodice></DatiAnagrafici></CedentePrestatore>\n'
            '  </FatturaElettronicaHeader>\n'
            '  <FatturaElettronicaBody>\n'
            '    <DatiGenerali><DatiGeneraliDocumento><Numero>FATT-99</Numero><Data>2026-11-20</Data><ImportoTotaleDocumento>1220.00</ImportoTotaleDocumento></DatiGeneraliDocumento></DatiGenerali>\n'
            '    <DatiPagamento><DettaglioPagamento><IBAN>IT60X0542811101000000123456</IBAN></DettaglioPagamento></DatiPagamento>\n'
            '  </FatturaElettronicaBody>\n'
            '</p:FatturaElettronica>'
        )
        ctx = Context(project_id="test_p", folder="/tmp/test_proj")
        with patch("agenti.agency.workspace.read") as mock_read:
            mock_read.return_value = xml_sample
            res_str = await call(ctx, "read_invoice", {"path": "fattura.xml"})
            res = json.loads(res_str)
            self.assertEqual(res["format"], "sdi_xml")
            self.assertEqual(res["fornitore"], "Fornitore SRL")
            self.assertEqual(res["totale"], 1220.00)
            self.assertEqual(res["numero_fattura"], "FATT-99")
            self.assertEqual(res["iban"], "IT60X0542811101000000123456")

    async def test_create_invoice_generation(self):
        ctx = Context(project_id="test_p", folder="/tmp/test_proj")
        with patch("agenti.agency.workspace.write") as mock_write:
            res_str = await call(ctx, "create_invoice", {
                "customer_name": "Cliente SPA",
                "vat_id": "IT98765432109",
                "total_net": 1000.0,
                "vat_rate": 22.0,
                "number": "2026/042",
                "iban": "IT60X0542811101000000123456",
            })
            res = json.loads(res_str)
            self.assertEqual(res["status"], "created")
            self.assertEqual(res["net"], 1000.0)
            self.assertEqual(res["vat"], 220.0)
            self.assertEqual(res["total"], 1220.0)
            self.assertTrue(mock_write.called)
            written_content = mock_write.call_args[0][2]
            self.assertIn("Cliente SPA", written_content)
            self.assertIn("1220.00", written_content)

    async def test_whatsapp_send_validation(self):
        ctx = Context(project_id="test_p", folder="/tmp/test_proj")
        res_str = await call(ctx, "whatsapp_send", {
            "recipient": "+39 333 1234567",
            "message": "Conferma ordine #1042 registrato con successo.",
        })
        res = json.loads(res_str)
        self.assertEqual(res["status"], "queued")
        self.assertEqual(res["channel"], "whatsapp_business")
        self.assertEqual(res["recipient"], "+393331234567")

        err_str = await call(ctx, "whatsapp_send", {
            "recipient": "123",
            "message": "test",
        })
        self.assertIn("error: invalid phone number", err_str)

    async def test_twilio_voice_dispatch(self):
        ctx = Context(project_id="test_p", folder="/tmp/test_proj")
        res_str = await call(ctx, "twilio_voice_dispatch", {
            "phone_number": "+39 02 12345678",
            "speech_script": "Buongiorno, la contatto per confermare il suo appuntamento.",
        })
        res = json.loads(res_str)
        self.assertEqual(res["status"], "call_dispatched")
        self.assertEqual(res["provider"], "twilio_voice")
        self.assertIn("<Say language=\"it-IT\">", res["twiml_payload"])

    async def test_email_dispatch_and_pec(self):
        ctx = Context(project_id="test_p", folder="/tmp/test_proj")
        res_str = await call(ctx, "email_dispatch", {
            "to": "commerciale@fornitore.it",
            "subject": "Ordine Materiali #2026",
            "body": "Gentile Fornitore, alleghiamo la conferma d'ordine.",
            "is_pec": False,
        })
        res = json.loads(res_str)
        self.assertEqual(res["status"], "sent")
        self.assertEqual(res["channel"], "business_email")

        res_pec_str = await call(ctx, "email_dispatch", {
            "to": "fornitore@pec.it",
            "subject": "Fattura Elettronica",
            "body": "Invio formale fattura.",
            "is_pec": True,
        })
        res_pec = json.loads(res_pec_str)
        self.assertEqual(res_pec["channel"], "pec_smtp")

    async def test_mcp_gateway(self):
        ctx = Context(project_id="test_p", folder="/tmp/test_proj")
        res_str = await call(ctx, "mcp_gateway", {
            "server": "google-workspace",
            "tool_name": "calendar_create_event",
            "payload": {"summary": "Meeting CEO"},
        })
        res = json.loads(res_str)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["mcp_server"], "google-workspace")
        self.assertEqual(res["tool"], "calendar_create_event")


if __name__ == "__main__":
    unittest.main()
