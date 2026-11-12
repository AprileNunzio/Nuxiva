from agenti._registry import registry

AGENT_ID = "autonomy"


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
        return {"id": AGENT_ID, "name": m.get("name", AGENT_ID), "capabilities": list(m.get("capabilities", []))}


agent = Agent()
