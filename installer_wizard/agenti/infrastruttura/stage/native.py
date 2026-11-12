import os


def load():
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    return nuxiva_native if hasattr(nuxiva_native, "stage_plan") else None


lib = load()
ENGINE = "rust" if lib is not None else "python"
