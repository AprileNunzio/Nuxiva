from agenti.agent import registry
from agenti.mind import reflect


@registry.tool("what_i_learned", "mostra cosa ha imparato Nuxiva sulle abitudini e le preferenze, con la possibilità di tenerlo o dimenticarlo", {}, agent="agent")
async def what_i_learned() -> str:
    from agenti.desktop.desk import desk
    data = reflect.snapshot()
    desk.show("learned", data, key="agent:learned", ttl=60)
    return f"{len(data['items'])} cose imparate"
