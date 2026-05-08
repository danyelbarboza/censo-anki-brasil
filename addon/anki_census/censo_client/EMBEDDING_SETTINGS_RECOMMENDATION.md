# Embedding Settings Tab Recommendation

This note describes the recommended way to expose Anki Census controls in any host add-on.

## Goal

Keep integration zero-config while giving users clear control over global participation.

## Recommended UI

Create a dedicated **Anki Census** tab in your existing settings/config window.

Inside that tab, keep the UI minimal:

1. One short description line
2. One checkbox: "Pause participation globally"
3. One button: "View census status"

Do not build a heavy standalone UI unless your add-on specifically needs it.

## Suggested behavior

- Read current state using `is_participation_paused()` when opening settings.
- Persist user choice with `set_participation_paused(paused)` when saving settings.
- In "View census status", show:
  - pause state
  - `get_privacy_summary()`
  - `get_current_payload_preview()`

## Fail-safe requirement

Initialization and UI actions must never break the host add-on:

```python
try:
    from .censo_client import init_censo_client
    censo = init_censo_client(...)
except Exception:
    censo = None
```

If `censo is None`, disable census controls and show a short "client unavailable" message.

## UX constraints

- Keep copy short.
- Do not require manual setup from end users.
- Respect global opt-out across all integrated add-ons.
- Avoid duplicate hooks/timers/submissions; rely on `init_censo_client()` singleton behavior.
