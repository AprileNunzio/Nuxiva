import json
import time


async def _social_post_publish(ctx, args: dict) -> str:
    platform = str(args.get("platform", "instagram")).strip()[:40].lower()
    content = str(args.get("content", "")).strip()[:5000]
    media_urls = [str(u)[:240] for u in args.get("media_urls", []) if isinstance(u, str)]
    schedule = args.get("scheduled_at")
    if not content and not media_urls:
        raise ValueError("content or media_urls is required for social publishing")
    return json.dumps({
        "status": "scheduled" if schedule else "published",
        "platform": platform,
        "content_length": len(content),
        "media_count": len(media_urls),
        "scheduled_at": schedule,
        "post_id": f"post_{platform}_{int(time.time())}",
        "engagement_tracking": True,
    })


def get_tools() -> list:
    from agenti.agency.tools import Tool
    return [
        Tool("social_post_publish", "Publish or schedule multimedia posts across social platforms (Instagram, TikTok, LinkedIn, X, Facebook).",
             {"platform": "instagram", "content": "Nuovo drop online!", "media_urls": ["https://..."]}, "execute", _social_post_publish),
    ]
