from agenti.agent import registry
from agenti.tasks import queue as taskq


@registry.tool("what_i_am_doing", "mostra cosa sta facendo Nuxiva in background in questo momento", {}, agent="agent")
async def what_i_am_doing() -> str:
    from agenti.desktop.desk import desk
    data = taskq.snapshot()
    desk.show("doing_now", data, key="agent:doing_now", ttl=30)
    return f"{data['active']} cose in corso in background"
