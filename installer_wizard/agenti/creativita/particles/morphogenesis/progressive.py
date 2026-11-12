from dataclasses import dataclass

LOD_BUDGETS = {
    "shell": 2_500,
    "core": 6_000,
    "fine": 12_000,
    "full": 24_000,
}


@dataclass(frozen=True)
class ProgressiveAssembly:
    shell: dict
    core: dict
    fine: dict
    full: dict


def decompose_lod(spec: dict) -> ProgressiveAssembly:
    parts = list((spec or {}).get("parts") or [])
    total = len(parts)
    if total <= 2:
        return ProgressiveAssembly(spec, spec, spec, spec)

    shell_count = max(2, total // 3)
    core_count = min(total, shell_count + total // 3)

    return ProgressiveAssembly(
        shell={"parts": parts[:shell_count]},
        core={"parts": parts[:core_count]},
        fine=spec,
        full=spec,
    )


def point_budget_for(stage_name: str) -> int:
    return LOD_BUDGETS.get(str(stage_name).lower(), 12_000)
