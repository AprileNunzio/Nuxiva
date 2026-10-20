import asyncio
import logging
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent
_WIZARD = _BACKEND.parent
_ROOT = _WIZARD.parent

for _p in (str(_ROOT), str(_WIZARD), str(_BACKEND)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import safe_mode


def main() -> None:
    try:
        import nuxiva_supervisor
    except BaseException as exc:
        if isinstance(exc, KeyboardInterrupt):
            raise
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
        logging.getLogger("nuxiva.launch").exception("Avvio non riuscito: modalità sicura")
        safe_mode.run(exc)
        return
    safe_mode.clear()
    asyncio.run(nuxiva_supervisor.main())


if __name__ == "__main__":
    main()
