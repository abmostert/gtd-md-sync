

def prompt(text: str, default: str | None = None) -> str:
    """
    Simple input() wrapper with optional default.
    Empty input returns default (if provided).
    """
    if default is None:
        return input(text).strip()
    s = input(f"{text} [{default}] ").strip()
    return s if s else default


def prompt_optional_date(text: str) -> str | None:
    """Accept YYYY-MM-DD or empty for None. (No strict validation in v1.)"""
    s = input(f"{text} (YYYY-MM-DD, or blank): ").strip()
    return s or None
