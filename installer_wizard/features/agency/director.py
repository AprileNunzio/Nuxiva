from features.agency import prompts
from features.agency.blueprint import Blueprint, parse
from features.agency.text import estimate_tokens
from features.brain import llm

PLAN_TOKENS = 3500


async def think(goal: str, language_name: str) -> tuple[Blueprint, int]:
    prompt = prompts.plan(goal, language_name)
    raw = await llm.generate(prompt, as_json=True, max_tokens=PLAN_TOKENS, temperature=0.2,
                             system=prompts.DIRECTOR, component="agency_director")
    blueprint = parse(raw, goal)
    return blueprint, estimate_tokens(prompt, str(raw))
