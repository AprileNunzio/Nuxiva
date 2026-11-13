import argparse
import ipaddress
import json
import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path

LOCAL_NAMES = {"localhost", "localhost.localdomain", "ip6-localhost", ""}
RERUNS = 2
PROXY_KEYS = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY")


class Ledger:
    current = "<import>"
    network: dict[str, set[str]] = {}
    mode = "off"


def is_local(host) -> bool:
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    name = str(host).strip().strip("[]").split("%", 1)[0].lower()
    if name in LOCAL_NAMES:
        return True
    try:
        address = ipaddress.ip_address(name)
    except ValueError:
        return False
    return address.is_loopback or address.is_unspecified


def note(target: str) -> None:
    Ledger.network.setdefault(Ledger.current, set()).add(target[:120])
    if Ledger.mode == "enforce":
        raise OSError(101, f"rete esterna vietata nei test / external network forbidden in tests: {target}")


def literal(host) -> bool:
    try:
        ipaddress.ip_address(str(host).strip("[]").split("%", 1)[0])
    except ValueError:
        return False
    return True


def guard_network(mode: str) -> None:
    Ledger.mode = mode
    if mode == "off":
        return
    for key in PROXY_KEYS:
        os.environ.pop(key, None)
        os.environ.pop(key.lower(), None)
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_getaddrinfo = socket.getaddrinfo

    def check(sock, address):
        if sock.type & socket.SOCK_DGRAM and isinstance(address, tuple) and address[1] != 53:
            return
        if sock.family in (socket.AF_INET, socket.AF_INET6) and isinstance(address, tuple) and not is_local(address[0]):
            note(f"{address[0]}:{address[1]}")

    def connect(self, address):
        check(self, address)
        return original_connect(self, address)

    def connect_ex(self, address):
        check(self, address)
        return original_connect_ex(self, address)

    def getaddrinfo(host, *args, **kwargs):
        if not is_local(host) and not literal(host):
            note(f"dns:{host}")
        return original_getaddrinfo(host, *args, **kwargs)

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex
    socket.getaddrinfo = getaddrinfo


class TrackingResult(unittest.TextTestResult):
    def startTest(self, test):
        Ledger.current = test.id()
        super().startTest(test)


def base_id(test) -> str:
    inner = getattr(test, "test_case", None)
    if inner is not None:
        return inner.id()
    return test.id()


def failed_ids(result: unittest.TestResult) -> list[str]:
    seen: dict[str, None] = {}
    for test, _ in [*result.failures, *result.errors]:
        name = base_id(test)
        if "." in name and not name.startswith("unittest.loader"):
            seen.setdefault(name, None)
        else:
            seen.setdefault(f"<caricamento> {name}", None)
    for test in result.unexpectedSuccesses:
        seen.setdefault(base_id(test), None)
    return list(seen)


def isolated(test_id: str, top: Path) -> bool:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    run = subprocess.run([sys.executable, "-m", "unittest", test_id], cwd=top, env=env, capture_output=True, text=True, timeout=900)
    return run.returncode == 0


def classify(ids: list[str], top: Path) -> dict[str, str]:
    verdict: dict[str, str] = {}
    for test_id in ids:
        if test_id.startswith("<caricamento>"):
            verdict[test_id] = "vero"
            continue
        passes = sum(1 for _ in range(RERUNS) if isolated(test_id, top))
        if passes == RERUNS:
            verdict[test_id] = "ordine"
        elif passes:
            verdict[test_id] = "instabile"
        else:
            verdict[test_id] = "vero"
    return verdict


LABELS = {
    "vero": ("fallisce sempre, anche da solo", "fails every time, also alone"),
    "ordine": ("passa da solo: dipende da ordine o stato condiviso", "passes alone: depends on order or shared state"),
    "instabile": ("a volte passa e a volte no: instabile", "passes only sometimes: flaky"),
}


def report(title: str, verdict: dict[str, str], network: dict[str, set[str]], elapsed: float, total: int) -> str:
    lines = [f"### {title}", "", f"{total} test, {elapsed:.0f}s", ""]
    if verdict:
        lines += ["| Test | Esito / Verdict |", "|---|---|"]
        for test_id, kind in verdict.items():
            it, en = LABELS[kind]
            lines.append(f"| `{test_id}` | **{kind}**: {it} / {en} |")
        lines.append("")
    if network:
        lines += ["Test che usano la rete esterna / Tests using the external network:", ""]
        for test_id in sorted(network):
            lines.append(f"- `{test_id}`: {', '.join(sorted(network[test_id])[:4])}")
        lines.append("")
    if not verdict and not network:
        lines.append("Tutto verde / All green")
    return "\n".join(lines) + "\n"


def annotate(verdict: dict[str, str], network: dict[str, set[str]], mode: str) -> None:
    for test_id, kind in verdict.items():
        it, en = LABELS[kind]
        print(f"::error title=test {kind}::{test_id}: {it} / {en}")
    level = "error" if mode == "enforce" else "warning"
    for test_id in sorted(network):
        print(f"::{level} title=rete nei test / network in tests::{test_id} -> {', '.join(sorted(network[test_id])[:4])}")


def write_summary(text: str, path: str | None) -> None:
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    for destination in filter(None, (target, path)):
        with open(destination, "a", encoding="utf-8") as handle:
            handle.write(text)


def load(names: list[str], start: str, top: Path) -> unittest.TestSuite:
    loader = unittest.TestLoader()
    if names:
        return loader.loadTestsFromNames(names)
    return loader.discover(start, top_level_dir=str(top))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", required=True)
    parser.add_argument("--start", default="tests")
    parser.add_argument("--title", default="Test")
    parser.add_argument("--network", choices=("off", "report", "enforce"), default="report")
    parser.add_argument("--no-classify", action="store_true")
    parser.add_argument("--summary")
    parser.add_argument("--json")
    parser.add_argument("names", nargs="*")
    args = parser.parse_args(argv)
    top = Path(args.top).resolve()
    os.chdir(top)
    sys.path.insert(0, str(top))
    guard_network(args.network)
    began = time.monotonic()
    suite = load(args.names, args.start, top)
    runner = unittest.TextTestRunner(verbosity=2, resultclass=TrackingResult, stream=sys.stdout)
    result = runner.run(suite)
    elapsed = time.monotonic() - began
    ids = failed_ids(result)
    verdict = {test_id: "vero" for test_id in ids} if args.no_classify else classify(ids, top)
    network = {key: value for key, value in Ledger.network.items()}
    text = report(args.title, verdict, network, elapsed, result.testsRun)
    print(text)
    annotate(verdict, network, args.network)
    write_summary(text, args.summary)
    if args.json:
        Path(args.json).write_text(json.dumps({"failed": verdict, "network": {k: sorted(v) for k, v in network.items()}}, indent=1), encoding="utf-8")
    if result.testsRun == 0 and not ids:
        print("::error::nessun test trovato / no tests found")
        return 1
    return 1 if ids or (args.network == "enforce" and network) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
