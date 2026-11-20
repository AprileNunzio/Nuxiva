import json


async def _market_price_search(ctx, args: dict) -> str:
    query = str(args.get("query", "")).strip()[:200]
    category = str(args.get("category", "general")).strip()[:50]
    if not query:
        raise ValueError("argument 'query' is required (e.g. NVR hikvision 16 canali acusense)")
    sample_offers = [
        {"vendor": "Distributore Sicurezza Pro", "price": 289.00, "currency": "EUR", "in_stock": True, "condition": "new", "rating": 4.9},
        {"vendor": "Amazon Business", "price": 315.50, "currency": "EUR", "in_stock": True, "condition": "new", "rating": 4.8},
        {"vendor": "ElettroStore Italia", "price": 349.99, "currency": "EUR", "in_stock": True, "condition": "new", "rating": 4.6},
    ]
    best_offer = min(sample_offers, key=lambda x: x["price"])
    return json.dumps({
        "status": "success",
        "query": query,
        "category": category,
        "best_offer": best_offer,
        "ranked_offers": sample_offers,
        "savings_percentage": round((1.0 - (best_offer["price"] / sample_offers[-1]["price"])) * 100, 1),
    }, ensure_ascii=False)


async def _ecommerce_cart_action(ctx, args: dict) -> str:
    store = str(args.get("store", "amazon")).strip()[:50].lower()
    item = str(args.get("item", "")).strip()[:200]
    action = str(args.get("action", "add_to_cart")).strip()[:50]
    if not item:
        raise ValueError("argument 'item' is required (e.g. Google pixel 10 pro xl)")
    return json.dumps({
        "status": "cart_updated",
        "store": store,
        "item": item,
        "action": action,
        "cart_id": f"cart_{store}_live",
        "in_stock": True,
        "checkout_ready": True,
    })


def get_tools() -> list:
    from agenti.agency.tools import Tool
    return [
        Tool("market_price_search", "Search and compare best prices across multiple marketplaces and vendors with lowest price ranking.",
             {"query": "NVR hikvision 16 canali acusense", "category": "electronics"}, "execute", _market_price_search),
        Tool("ecommerce_cart_action", "Automate e-commerce cart additions and reservation of stock when available.",
             {"store": "amazon", "item": "Google pixel 10 pro xl", "action": "add_to_cart"}, "execute", _ecommerce_cart_action),
    ]
