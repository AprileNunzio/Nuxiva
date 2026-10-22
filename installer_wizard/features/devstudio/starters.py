import json
from textwrap import dedent

KINDS = ("static_site", "python_cli", "fastapi_service", "node_cli", "react_vite")


def _clean(text: str) -> str:
    return dedent(text).lstrip("\n")


def _static(name: str) -> dict:
    return {
        "index.html": _clean(f"""
            <!doctype html>
            <html lang="it">
            <head>
              <meta charset="utf-8">
              <meta name="viewport" content="width=device-width, initial-scale=1">
              <meta http-equiv="Content-Security-Policy" content="default-src 'self'; img-src 'self' data:">
              <title>{name}</title>
              <link rel="stylesheet" href="style.css">
            </head>
            <body>
              <main>
                <h1>{name}</h1>
                <p id="message"></p>
              </main>
              <script src="app.js" defer></script>
            </body>
            </html>
        """),
        "style.css": _clean("""
            :root { color-scheme: light dark; --accent: #2563eb; }
            * { box-sizing: border-box; }
            body { margin: 0; font-family: system-ui, sans-serif; line-height: 1.5; }
            main { max-width: 60rem; margin: 0 auto; padding: 2rem 1rem; }
            h1 { color: var(--accent); }
            @media (min-width: 48rem) { main { padding: 4rem 2rem; } }
        """),
        "app.js": _clean("""
            document.getElementById("message").textContent = "Pronto.";
        """),
    }


def _python_cli(name: str) -> dict:
    module = name.replace("-", "_")
    return {
        f"{module}/__init__.py": "",
        f"{module}/core.py": _clean("""
            def greet(who: str) -> str:
                clean = " ".join(str(who).split())[:80]
                if not clean:
                    raise ValueError("nome mancante")
                return f"Ciao, {clean}"
        """),
        "main.py": _clean(f"""
            import argparse

            from {module}.core import greet


            def main() -> int:
                parser = argparse.ArgumentParser()
                parser.add_argument("who")
                print(greet(parser.parse_args().who))
                return 0


            if __name__ == "__main__":
                raise SystemExit(main())
        """),
        "test_core.py": _clean(f"""
            import unittest

            from {module}.core import greet


            class GreetTest(unittest.TestCase):
                def test_greets(self):
                    self.assertEqual(greet("Mario"), "Ciao, Mario")

                def test_rejects_empty(self):
                    with self.assertRaises(ValueError):
                        greet("  ")


            if __name__ == "__main__":
                unittest.main()
        """),
    }


def _fastapi(name: str) -> dict:
    return {
        "requirements.txt": "fastapi>=0.110\nuvicorn>=0.29\n",
        "app/__init__.py": "",
        "app/main.py": _clean(f"""
            from fastapi import FastAPI
            from pydantic import BaseModel, Field

            app = FastAPI(title="{name}", docs_url=None, redoc_url=None)


            class Item(BaseModel):
                name: str = Field(min_length=1, max_length=80)


            @app.get("/health")
            def health() -> dict:
                return {{"status": "ok"}}


            @app.post("/items", status_code=201)
            def create(item: Item) -> dict:
                return {{"name": item.name}}
        """),
        "test_api.py": _clean("""
            import unittest

            try:
                from fastapi.testclient import TestClient
                from app.main import app
            except ImportError:
                app = None


            @unittest.skipIf(app is None, "fastapi non installato")
            class ApiTest(unittest.TestCase):
                def test_health(self):
                    self.assertEqual(TestClient(app).get("/health").json(), {"status": "ok"})

                def test_rejects_empty_name(self):
                    self.assertEqual(TestClient(app).post("/items", json={"name": ""}).status_code, 422)


            if __name__ == "__main__":
                unittest.main()
        """),
    }


def _node_cli(name: str) -> dict:
    return {
        "package.json": json.dumps({"name": name, "version": "0.1.0", "type": "module", "private": True,
                                    "scripts": {"test": "node --test"}}, indent=2) + "\n",
        "index.js": _clean("""
            export function greet(who) {
              const clean = String(who ?? "").trim().slice(0, 80);
              if (!clean) throw new RangeError("nome mancante");
              return `Ciao, ${clean}`;
            }

            if (import.meta.url === `file://${process.argv[1]}`) {
              console.log(greet(process.argv[2]));
            }
        """),
        "index.test.js": _clean("""
            import { test } from "node:test";
            import assert from "node:assert/strict";
            import { greet } from "./index.js";

            test("greets", () => assert.equal(greet("Mario"), "Ciao, Mario"));
            test("rejects empty", () => assert.throws(() => greet("  "), RangeError));
        """),
    }


def _react(name: str) -> dict:
    return {
        "package.json": json.dumps({
            "name": name, "version": "0.1.0", "private": True, "type": "module",
            "scripts": {"dev": "vite", "build": "tsc --noEmit && vite build", "preview": "vite preview"},
            "dependencies": {"react": "^18.3.1", "react-dom": "^18.3.1"},
            "devDependencies": {"@types/react": "^18.3.3", "@types/react-dom": "^18.3.0", "@vitejs/plugin-react": "^4.3.1",
                                "typescript": "^5.5.0", "vite": "^5.4.0"}}, indent=2) + "\n",
        "tsconfig.json": json.dumps({"compilerOptions": {"target": "ES2022", "module": "ESNext", "moduleResolution": "bundler",
                                                         "jsx": "react-jsx", "strict": True, "noEmit": True, "skipLibCheck": True},
                                     "include": ["src"]}, indent=2) + "\n",
        "vite.config.ts": _clean("""
            import { defineConfig } from "vite";
            import react from "@vitejs/plugin-react";

            export default defineConfig({ plugins: [react()] });
        """),
        "index.html": _clean(f"""
            <!doctype html>
            <html lang="it">
            <head>
              <meta charset="utf-8">
              <meta name="viewport" content="width=device-width, initial-scale=1">
              <title>{name}</title>
            </head>
            <body>
              <div id="root"></div>
              <script type="module" src="/src/main.tsx"></script>
            </body>
            </html>
        """),
        "src/main.tsx": _clean("""
            import { StrictMode } from "react";
            import { createRoot } from "react-dom/client";
            import { App } from "./App";

            createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
        """),
        "src/App.tsx": _clean(f"""
            import {{ useState }} from "react";

            export function App() {{
              const [count, setCount] = useState(0);
              return (
                <main style={{{{ maxWidth: "60rem", margin: "0 auto", padding: "2rem 1rem", fontFamily: "system-ui" }}}}>
                  <h1>{name}</h1>
                  <button onClick={{() => setCount((value) => value + 1)}}>Clic: {{count}}</button>
                </main>
              );
            }}
        """),
        ".gitignore": "node_modules\ndist\n",
    }


BUILDERS = {"static_site": _static, "python_cli": _python_cli, "fastapi_service": _fastapi, "node_cli": _node_cli,
            "react_vite": _react}


def scaffold(kind: str, name: str) -> dict:
    if kind not in BUILDERS:
        raise KeyError(kind)
    return BUILDERS[kind](name)
