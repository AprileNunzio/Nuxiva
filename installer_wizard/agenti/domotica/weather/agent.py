from agenti._registry import registry

AGENT_ID = "weather"


class Agent:
    agent_id = AGENT_ID

    def __init__(self) -> None:
        self.running = False

    @property
    def manifest(self) -> dict:
        found = registry.get(AGENT_ID)
        return dict(found.manifest) if found else {}

    def start(self) -> None:
        self.running = True

    def stop(self) -> None:
        self.running = False

    def describe(self) -> dict:
        m = self.manifest
        out = {"id": AGENT_ID, "name": m.get("name", AGENT_ID), "capabilities": list(m.get("capabilities", []))}
        from agenti.weather import places, skill
        chosen = places.default()
        if chosen:
            try:
                out["skill"] = skill.standing(chosen)
            except ValueError:
                pass
        return out


agent = Agent()
