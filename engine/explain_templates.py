"""Plain-English rejection wording for Free Money Hunter AI's own gate-hard check."""

from __future__ import annotations

from hunter_engine.explain import BASE_REJECTION_TEMPLATES

REJECTION_TEMPLATES = {
    **BASE_REJECTION_TEMPLATES,
    "official_registry_confirmed": lambda d: (
        "We couldn't confirm this against an official registry or settlement "
        "administrator ourselves — the source we have is about the program, "
        "not the official listing itself, so we won't tell you to act on it."
    ),
}
