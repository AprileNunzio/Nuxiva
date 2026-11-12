import argparse
import json
import os
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.append(str(_BACKEND))

from agenti import _manifest, _scaffold
from agenti._layout import ScaffoldError
from agenti._registry import registry

LANG_DIR = Path(__file__).resolve().parent / "_language"
SUPPORTED = ("it", "en", "fr", "es")


def _locale(choice: str | None) -> str:
    raw = (choice or os.environ.get("NUXIVA_LANG") or os.environ.get("LANG") or "it")[:2].lower()
    return raw if raw in SUPPORTED else "it"


def _messages(lang: str) -> dict:
    return json.loads((LANG_DIR / f"{lang}.json").read_text(encoding="utf-8"))


class Output:
    def __init__(self, lang: str) -> None:
        self.text = _messages(lang)

    def __call__(self, key: str, **values) -> str:
        return self.text.get(key, key).format(**values)

    def issues(self, issues: list[dict]) -> list[str]:
        return [self("issue", field=i.get("field", ""), reason=self.text.get(f"code.{i.get('code', '')}", i.get("code", "")))
                for i in issues]


def _clean(values: list[str] | None) -> list[str]:
    return [v.strip() for v in values or [] if v.strip()]


def _new(args, say: Output) -> int:
    spec = {
        "id": args.id.strip(), "category": args.categoria.strip(), "name": args.nome.strip(),
        "description": args.descrizione.strip(), "capabilities": _clean(args.capacita),
        "nouns": _clean(args.parole), "phrases": _clean(args.frasi), "icon": "",
    }
    if not args.comunque:
        close = _scaffold.similar(spec, registry)
        if close:
            print(say("similar", agents=", ".join(f"{ident} ({score})" for ident, score in close)), file=sys.stderr)
            return 3
    try:
        target = _scaffold.create(spec)
    except ScaffoldError as exc:
        print(say("invalid"), file=sys.stderr)
        for line in say.issues(exc.issues):
            print(line, file=sys.stderr)
        return 2
    print(say("created", id=spec["id"], path=target))
    return 0


def _check_one(agent, say: Output) -> bool:
    report = _scaffold.inspect(agent.dir)
    print(say("score", id=agent.id, category=agent.category, score=report["score"]))
    for part in report["missing"]:
        print(say("missing", part=part))
    for part in report["optional_missing"]:
        print(say("optional", part=part))
    return report["complete"]


def _check(args, say: Output) -> int:
    registry.refresh()
    if args.id:
        agent = registry.get(args.id) if _manifest.valid_id(args.id) else None
        if agent is None:
            print(say("unknown", id=args.id), file=sys.stderr)
            return 2
        return 0 if _check_one(agent, say) else 1
    agents = registry.agents()
    complete = sum(_check_one(agent, say) for agent in agents)
    rejected = registry.rejected()
    for item in rejected:
        print(say("rejected", path=item["path"]), file=sys.stderr)
        for line in say.issues(item["issues"]):
            print(line, file=sys.stderr)
    print(say("summary", complete=complete, total=len(agents), rejected=len(rejected)))
    return 1 if rejected else 0


def build_parser(say: Output) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m agenti", description=say("cli"))
    parser.add_argument("--lingua", choices=SUPPORTED)
    sub = parser.add_subparsers(dest="command", required=True)
    new = sub.add_parser("nuovo", help=say("cmd.new"))
    new.add_argument("--id", required=True, help=say("arg.id"))
    new.add_argument("--categoria", required=True, choices=_manifest.CATEGORIES, help=say("arg.category"))
    new.add_argument("--nome", required=True, help=say("arg.name"))
    new.add_argument("--descrizione", required=True, help=say("arg.description"))
    new.add_argument("--capacita", action="append", help=say("arg.capability"))
    new.add_argument("--parole", action="append", help=say("arg.noun"))
    new.add_argument("--frasi", action="append", help=say("arg.phrase"))
    new.add_argument("--comunque", action="store_true", help=say("arg.anyway"))
    check = sub.add_parser("verifica", help=say("cmd.check"))
    check.add_argument("id", nargs="?", help=say("arg.check_id"))
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    lang = _locale(argv[argv.index("--lingua") + 1] if "--lingua" in argv[:-1] else None)
    say = Output(lang)
    args = build_parser(say).parse_args(argv)
    return _new(args, say) if args.command == "nuovo" else _check(args, say)


if __name__ == "__main__":
    sys.exit(main())
