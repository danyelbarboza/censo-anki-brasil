# Embedding the Anki Census Client

`censo_client/` is a reusable module that can be copied into any Anki add-on.

## Public naming and legacy folder naming

Public project name: **Anki Census**.

For compatibility during migration, the reusable folder can still be named `censo_client`.

## Copy and initialize

Copy this folder into your add-on package:

```text
censo_client/
  __init__.py
  bootstrap.py
  collector.py
  config.py
  identity.py
  payload.py
  privacy.py
  transport.py
  version.py
```

Initialize once in your add-on startup:

```python
from .censo_client import init_censo_client

censo = init_censo_client(
    source_addon_id="anki-dynamic-deadline",
    source_addon_name="Dynamic Deadline",
    source_addon_version="1.0.0",
)
```

## Global singleton behavior

The module uses `aqt.mw` runtime attributes so different add-on namespaces still share one collector instance:

- `_anki_census_global_collector`
- `_anki_census_global_state`
- legacy aliases:
  - `_anki_census_global_collector`
  - `_anki_census_global_state`

`init_censo_client()` is idempotent and does not register duplicate startup actions.

## Shared config behavior

The shared config is profile-scoped and stored in:

- new path: `<profile>/addon_data/anki_census/config.json`
- legacy fallback: `<profile>/addon_data/anki_census/config.json`

If only the legacy file exists, it is migrated to the new path.

Shared keys include:

- `anonymous_user_id`
- `participation_paused`
- `notice_seen`
- `first_notice_at`
- `first_send_allowed_after`
- `registered_sources`
- `last_submission`

Writes are atomic to reduce corruption risk.

## Global opt-out API

The client exposes:

- `is_participation_paused() -> bool`
- `set_participation_paused(paused: bool) -> None`
- `get_privacy_summary() -> dict`
- `get_current_payload_preview() -> dict`

If one add-on pauses participation, all others read the same flag.

## Source registration

Every `init_censo_client()` call upserts this source in `registered_sources` with:

- `name`
- `version`
- `first_seen_at`
- `last_seen_at`

This does not create extra timers/hooks/submissions.

## Duplicate prevention

Use `last_submission[survey_id]` and runtime singleton guards to avoid:

- one submission per add-on
- duplicate timers
- duplicate hook registration

Expected policy: at most one submission per survey window per profile.

## What is not sent

Anki Census does not send:

- card or note content
- deck/tag/field/note-type names
- media file names or binary media
- email, real name, or AnkiWeb login
- local filesystem collection paths

## Quick validation checklist

1. Start Anki with one add-on embedding `censo_client`; ensure one collector exists.
2. Load a second add-on embedding `censo_client`; ensure same collector is reused.
3. Confirm second add-on is added under `registered_sources`.
4. Set paused=true in one add-on; verify all others read paused=true.
5. Corrupt shared JSON manually; confirm fallback loads defaults without crashing Anki.
6. Call `init_censo_client()` repeatedly; verify no duplicate startup behavior.
