from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CommandStateEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: Literal["USER_COMMAND_EXECUTED"]
    task_id: str = Field(min_length=1, max_length=128)
    agent: str = Field(min_length=1, max_length=128)
    status: str = Field(min_length=1, max_length=32)


def record_state_event(event: dict) -> None:
    from server.core.event_sourcing.ledger import ledger

    validated = CommandStateEvent.model_validate(event)
    ledger.append_event(validated.task_id, validated.event_type, validated.model_dump())
