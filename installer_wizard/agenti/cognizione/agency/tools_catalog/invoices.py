import json
import re

from agenti.agency import workspace


async def _read_invoice(ctx, args: dict) -> str:
    path = str(args.get("path", "")).strip()[:240]
    content = workspace.read(ctx.folder, path, 50000)
    if "<FatturaElettronica" in content:
        cedente = re.search(r"<Denominazione>([^<]+)</Denominazione>", content)
        piva = re.search(r"<IdCodice>([^<]+)</IdCodice>", content)
        totale = re.search(r"<ImportoTotaleDocumento>([^<]+)</ImportoTotaleDocumento>", content)
        numero = re.search(r"<Numero>([^<]+)</Numero>", content)
        data = re.search(r"<Data>([^<]+)</Data>", content)
        iban = re.search(r"<IBAN>([^<]+)</IBAN>", content)
        return json.dumps({
            "format": "sdi_xml",
            "fornitore": cedente.group(1) if cedente else "N/D",
            "piva": piva.group(1) if piva else "N/D",
            "numero_fattura": numero.group(1) if numero else "N/D",
            "data": data.group(1) if data else "N/D",
            "totale": float(totale.group(1)) if totale else 0.0,
            "iban": iban.group(1) if iban else None,
        }, ensure_ascii=False)
    try:
        data = json.loads(content)
        return json.dumps({"format": "structured_json", "data": data}, ensure_ascii=False)
    except Exception:
        return json.dumps({"format": "raw_text", "preview": content[:1000]}, ensure_ascii=False)


async def _create_invoice(ctx, args: dict) -> str:
    customer = str(args.get("customer_name", "")).strip()[:120]
    vat_id = str(args.get("vat_id", "")).strip()[:32]
    net_amount = float(args.get("total_net", 0.0))
    vat_rate = float(args.get("vat_rate", 22.0))
    vat_amount = round(net_amount * (vat_rate / 100.0), 2)
    gross_total = round(net_amount + vat_amount, 2)
    invoice_num = str(args.get("number") or "2026-001")
    iban = str(args.get("iban") or "")[:34]
    xml_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<p:FatturaElettronica versione="FPR12" xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2">\n'
        '  <FatturaElettronicaHeader>\n'
        f'    <CessionarioCommittente><DatiAnagrafici><Denominazione>{customer}</Denominazione><CodiceFiscale>{vat_id}</CodiceFiscale></DatiAnagrafici></CessionarioCommittente>\n'
        '  </FatturaElettronicaHeader>\n'
        '  <FatturaElettronicaBody>\n'
        f'    <DatiGenerali><DatiGeneraliDocumento><TipoDocumento>TD01</TipoDocumento><Divisa>EUR</Divisa><Numero>{invoice_num}</Numero><ImportoTotaleDocumento>{gross_total:.2f}</ImportoTotaleDocumento></DatiGeneraliDocumento></DatiGenerali>\n'
        f'    <DatiBeniServizi><DatiRiepilogo><AliquotaIVA>{vat_rate:.2f}</AliquotaIVA><ImponibileImporto>{net_amount:.2f}</ImponibileImporto><Imposta>{vat_amount:.2f}</Imposta></DatiRiepilogo></DatiBeniServizi>\n'
        f'    <DatiPagamento><DettaglioPagamento><IBAN>{iban}</IBAN></DettaglioPagamento></DatiPagamento>\n'
        '  </FatturaElettronicaBody>\n'
        '</p:FatturaElettronica>'
    )
    rel_path = f"invoices/fattura_{invoice_num.replace('/', '_')}.xml"
    workspace.write(ctx.folder, rel_path, xml_content)
    if hasattr(ctx, "written") and rel_path not in ctx.written:
        ctx.written.append(rel_path)
    return json.dumps({
        "status": "created",
        "path": rel_path,
        "net": net_amount,
        "vat": vat_amount,
        "total": gross_total,
        "customer": customer,
    }, ensure_ascii=False)


def get_tools() -> list:
    from agenti.agency.tools import Tool
    return [
        Tool("read_invoice", "Parse an electronic invoice (XML SDI or JSON) extracting supplier, amounts, VAT, and payment info.",
             {"path": "relative/path/to/invoice.xml"}, "read", _read_invoice),
        Tool("create_invoice", "Generate a valid electronic invoice (FatturaPA XML format) with calculated taxes.",
             {"customer_name": "Acme Corp", "vat_id": "IT12345678901", "total_net": 1000.0, "vat_rate": 22.0, "iban": "IT00X0000000000000000000000"}, "write", _create_invoice),
    ]
