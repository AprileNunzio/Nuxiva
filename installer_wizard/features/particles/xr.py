from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class XrSceneConfig:
    stereo_separation: float = 0.064
    inside_view_radius: float = 0.35
    hotspot_billboards: bool = True
    hand_tracking: bool = True
    lod_streaming: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


def xr_envelope(digest: str, concept: str, hotspots: list[dict] | None = None, lod_layers: dict | None = None) -> dict:
    return {
        "xr_enabled": True,
        "format": "nxpc_v1",
        "digest": digest,
        "concept": concept,
        "hotspots": list(hotspots or []),
        "lod_layers": dict(lod_layers or {}),
        "config": XrSceneConfig().to_dict(),
        "camera": {
            "initial_distance": 2.2,
            "min_distance": 0.05,
            "max_distance": 10.0,
            "allow_inside_flythrough": True,
        },
    }
