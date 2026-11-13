import json
import os
import sys

TEXT = {
    "success": ("verde", "green"),
    "failure": ("FALLITO", "FAILED"),
    "cancelled": ("annullato, non è un errore del codice", "cancelled, not a code failure"),
    "skipped": ("saltato", "skipped"),
}


def main() -> int:
    needs = json.loads(os.environ.get("NEEDS", "{}"))
    rows = []
    worst = "success"
    for name, info in sorted(needs.items()):
        result = str(info.get("result", "failure"))
        it, en = TEXT.get(result, (result, result))
        rows.append(f"| {name} | {result} | {it} / {en} |")
        if result == "failure" or (result == "cancelled" and worst != "failure"):
            worst = result
    body = ["### Riepilogo CI / CI summary", "", "| Job | Esito | Significato / Meaning |", "|---|---|---|", *rows, ""]
    text = "\n".join(body)
    print(text)
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(text)
    if worst == "failure":
        print("::error::almeno un job è fallito davvero / at least one job really failed")
        return 1
    if worst == "cancelled":
        print("::warning::run annullato prima del termine / run cancelled before completion")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
