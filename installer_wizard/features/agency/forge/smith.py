import json
import math

from features.agency import prompts
from features.agency.forge import sandbox
from features.agency.forge.guard import ALLOWED_IMPORTS, ForgeRejected, check, name
from features.agency.forge.registry import ForgedTool, registry
from features.agency.text import clean, estimate_tokens
from features.brain import llm

ATTEMPTS = 2
MIN_TESTS = 2
MAX_TESTS = 6
MAX_ARGS = 12


def same(actual, expected) -> bool:
    if isinstance(expected, bool) or isinstance(actual, bool):
        return actual is expected
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9)
    if isinstance(expected, list) and isinstance(actual, list):
        return len(actual) == len(expected) and all(same(a, e) for a, e in zip(actual, expected))
    if isinstance(expected, dict) and isinstance(actual, dict):
        return actual.keys() == expected.keys() and all(same(actual[k], v) for k, v in expected.items())
    return actual == expected


def need_of(args: dict) -> dict:
    return {"name": name(args.get("name")), "purpose": clean(args.get("purpose"), 600),
            "example": clean(args.get("example"), 600)}


def blueprint(spec, tool_name: str, origin: dict) -> ForgedTool:
    if not isinstance(spec, dict):
        raise ForgeRejected("the toolsmith did not return an object")
    raw_args = spec.get("args") if isinstance(spec.get("args"), dict) else {}
    tests = [t for t in spec.get("tests", []) if isinstance(t, dict) and isinstance(t.get("args"), dict) and "expect" in t]
    if not MIN_TESTS <= len(tests) <= MAX_TESTS:
        raise ForgeRejected(f"between {MIN_TESTS} and {MAX_TESTS} tests with expected results are required")
    code = spec.get("code")
    check(code)
    return ForgedTool(name=tool_name, description=clean(spec.get("description"), 300) or "forged tool",
                      args={clean(k, 40): clean(v, 200) for k, v in list(raw_args.items())[:MAX_ARGS]}, code=code,
                      tests=[{"args": t["args"], "expect": t["expect"]} for t in tests], origin=origin)


async def prove(tool: ForgedTool) -> None:
    for index, test in enumerate(tool.tests, 1):
        outcome = await sandbox.execute(tool.code, test["args"])
        if not outcome.get("ok"):
            raise ForgeRejected(f"test {index} crashed: {outcome.get('error')}")
        if not same(outcome.get("result"), test["expect"]):
            shown = json.dumps(outcome.get("result"), ensure_ascii=False, default=str)[:200]
            raise ForgeRejected(f"test {index} returned {shown}, expected {json.dumps(test['expect'], ensure_ascii=False)[:200]}")


async def forge(args: dict, origin: dict) -> tuple[ForgedTool, int]:
    need = need_of(args)
    if registry.get(need["name"]):
        raise ForgeRejected(f"tool {need['name']} already exists")
    if not sandbox.available():
        raise sandbox.SandboxUnavailable("network isolation (unshare) is not available")
    failure, tokens = "", 0
    for _ in range(ATTEMPTS):
        prompt = prompts.forge(need, sorted(ALLOWED_IMPORTS), failure)
        spec = await llm.generate(prompt, as_json=True, max_tokens=2400, temperature=0.2, kind="deep",
                                  system=prompts.FORGE, component="agency_forge")
        tokens += estimate_tokens(prompt, json.dumps(spec, ensure_ascii=False) if spec else "")
        try:
            tool = blueprint(spec, need["name"], origin)
            await prove(tool)
        except ForgeRejected as exc:
            failure = str(exc)
            continue
        return registry.add(tool), tokens
    raise ForgeRejected(failure or "the toolsmith gave up")
