PUBLIC, PERSONAL, SENSITIVE = "public", "personal", "sensitive"
LEVELS = (PUBLIC, PERSONAL, SENSITIVE)
RANK = {level: index for index, level in enumerate(LEVELS)}
COMPONENT_LEVELS = {
    "mind": PERSONAL,
    "diary": PERSONAL,
    "surveillance_agent": PERSONAL,
}


def clean_level(value: object) -> str:
    return value if isinstance(value, str) and value in RANK else PUBLIC


def strictest(*levels: object) -> str:
    return max((clean_level(level) for level in levels), key=RANK.__getitem__, default=PUBLIC)


def component_level(component: str) -> str:
    return COMPONENT_LEVELS.get(component, PUBLIC)
