"""Regional default language lookup, keyed by state.

Pure function — no external dependencies. Used at district-seed time and at
centre-creation time to derive a default UI language without asking anyone
to enter it manually.
"""

STATE_LANGUAGE = {
    "Maharashtra": "mr",
}


def default_language_for_state(state: str) -> str:
    return STATE_LANGUAGE.get(state, "en")
