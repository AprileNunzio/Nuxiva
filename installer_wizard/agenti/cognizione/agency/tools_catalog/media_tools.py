import json

from agenti.agency.media_production import (
    AudioProducerEngine,
    MultimediaOrchestrator,
    SMBAudioHarvester,
    VideoEditorSyncDirector,
)
from agenti.agency.tools import Context, Tool, _text


async def _smb_audio_harvest(ctx: Context, args: dict) -> str:
    path = _text(args, "smb_path", 300)
    recursive = bool(args.get("recursive", True))
    exts = args.get("extensions") if isinstance(args.get("extensions"), list) else None

    resolved = SMBAudioHarvester.resolve_smb_mount(path)
    if resolved.is_file():
        result = SMBAudioHarvester.fetch_smb_audio(resolved)
        return json.dumps({"status": "file_harvested", "audio": result}, ensure_ascii=False)

    files = SMBAudioHarvester.scan_smb_audio_shares(resolved, extensions=exts, recursive=recursive)
    return json.dumps({
        "status": "smb_scanned",
        "base_path": path,
        "resolved_mount": str(resolved),
        "count": len(files),
        "files": files[:50],
    }, ensure_ascii=False)


async def _audio_producer_synthesize(ctx: Context, args: dict) -> str:
    text = _text(args, "text", 4000)
    voice = _text(args, "voice_profile", 80, required=False) or "it-IT-DiegoNeural"
    style = _text(args, "style", 60, required=False) or "dynamic"
    pacing = int(args.get("pacing_bpm") or 120)

    result = AudioProducerEngine.generate_synthetic_audio(
        text=text,
        voice_profile=voice,
        style=style,
        pacing_bpm=pacing,
    )
    return json.dumps(result, ensure_ascii=False)


async def _video_editor_sync_and_render(ctx: Context, args: dict) -> str:
    audio_track = args.get("audio_track")
    if not isinstance(audio_track, dict):
        return json.dumps({"status": "error", "message": "audio_track object is required"})

    scenes = args.get("scenes") if isinstance(args.get("scenes"), list) else []
    aspect = _text(args, "aspect_ratio", 20, required=False) or "9:16"

    synced = VideoEditorSyncDirector.sync_audio_video_timeline(
        video_scenes=scenes,
        audio_track=audio_track,
        target_aspect=aspect,
    )
    return json.dumps(synced, ensure_ascii=False)


async def _omnichannel_reel_produce(ctx: Context, args: dict) -> str:
    title = _text(args, "title", 120)
    topic = _text(args, "topic", 200)
    platform = _text(args, "platform", 60, required=False) or "instagram_reels"
    smb_path = _text(args, "smb_path", 300, required=False) or None
    voice_text = _text(args, "voice_text", 4000, required=False) or None
    scenes = args.get("scenes") if isinstance(args.get("scenes"), list) else None
    aspect = _text(args, "aspect_ratio", 20, required=False) or "9:16"

    manifest = MultimediaOrchestrator.orchestrate_omnichannel_reel(
        title=title,
        topic=topic,
        platform=platform,
        smb_path=smb_path,
        voice_text=voice_text,
        scenes=scenes,
        aspect_ratio=aspect,
    )
    return json.dumps(manifest, ensure_ascii=False)


TOOLS = {
    "smb_audio_harvest": Tool(
        name="smb_audio_harvest",
        description="Scansiona e preleva file e tracce audio (.mp3, .wav, .m4a, .ogg, .flac) da cartelle condivise di rete SMB/CIFS locali o remote.",
        args={"smb_path": "string", "recursive": "optional boolean", "extensions": "optional list"},
        capability="read",
        run=_smb_audio_harvest,
    ),
    "audio_producer_synthesize": Tool(
        name="audio_producer_synthesize",
        description="Genera tracce vocali, soundbite e narrazioni con sintesi vocale neurale, ritmo BPM controllato e allineamento temporale delle parole.",
        args={"text": "string", "voice_profile": "optional string", "style": "optional string", "pacing_bpm": "optional integer"},
        capability="execute",
        run=_audio_producer_synthesize,
    ),
    "video_editor_sync_and_render": Tool(
        name="video_editor_sync_and_render",
        description="Sincronizza tagli video, transizioni e sottotitoli dinamici (.srt) su una traccia audio (SMB o sintetizzata) per generare il render video finale.",
        args={"audio_track": "object", "scenes": "optional list", "aspect_ratio": "optional string"},
        capability="execute",
        run=_video_editor_sync_and_render,
    ),
    "omnichannel_reel_produce": Tool(
        name="omnichannel_reel_produce",
        description="Orchestra l'intera pipeline di produzione di un Reel/TikTok/Short: alloca la scrivania di pair programming, recupera audio SMB o lo sintetizza, sincronizza il video e prepara il pacchetto multimediale.",
        args={"title": "string", "topic": "string", "platform": "optional string", "smb_path": "optional string", "voice_text": "optional string", "scenes": "optional list", "aspect_ratio": "optional string"},
        capability="execute",
        run=_omnichannel_reel_produce,
    ),
}
