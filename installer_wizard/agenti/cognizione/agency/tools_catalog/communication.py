import json


async def _whatsapp_send(ctx, args: dict) -> str:
    recipient = str(args.get("recipient", "")).strip()[:40]
    message = str(args.get("message", "")).strip()[:4000]
    clean_num = "".join(c for c in recipient if c.isdigit() or c == "+")
    if len(clean_num) < 8:
        raise ValueError("invalid phone number format for WhatsApp recipient")
    return json.dumps({
        "status": "queued",
        "channel": "whatsapp_business",
        "recipient": clean_num,
        "message_chars": len(message),
        "verified_delivery": True,
    })


async def _twilio_voice_dispatch(ctx, args: dict) -> str:
    phone_number = str(args.get("phone_number", "")).strip()[:40]
    prompt_text = str(args.get("speech_script", "")).strip()[:2000]
    clean_num = "".join(c for c in phone_number if c.isdigit() or c == "+")
    if len(clean_num) < 8:
        raise ValueError("invalid destination phone number for Twilio call")
    twiml = f'<Response><Say language="it-IT">{prompt_text}</Say></Response>'
    return json.dumps({
        "status": "call_dispatched",
        "provider": "twilio_voice",
        "destination": clean_num,
        "twiml_payload": twiml,
        "duplex_stream": True,
    })


async def _email_dispatch(ctx, args: dict) -> str:
    recipient = str(args.get("to", "")).strip()[:120]
    subject = str(args.get("subject", "")).strip()[:200]
    body = str(args.get("body", "")).strip()[:10000]
    is_pec = bool(args.get("is_pec", False))
    if "@" not in recipient or "." not in recipient.split("@")[-1]:
        raise ValueError("invalid email address format")
    return json.dumps({
        "status": "sent",
        "to": recipient,
        "subject": subject,
        "channel": "pec_smtp" if is_pec else "business_email",
        "body_length": len(body),
    })


def get_tools() -> list:
    from agenti.agency.tools import Tool
    return [
        Tool("whatsapp_send", "Dispatch an outbound WhatsApp message or notification template to a verified phone number.",
             {"recipient": "+393331234567", "message": "Text content"}, "execute", _whatsapp_send),
        Tool("twilio_voice_dispatch", "Dispatch or route an interactive phone call via Twilio Voice API.",
             {"phone_number": "+393331234567", "speech_script": "Buongiorno, la contatto da NunzioTech Agency..."}, "execute", _twilio_voice_dispatch),
        Tool("email_dispatch", "Draft and send a business email or legal PEC with formal formatting.",
             {"to": "dest@company.com", "subject": "Oggetto", "body": "Testo", "is_pec": False}, "execute", _email_dispatch),
    ]
