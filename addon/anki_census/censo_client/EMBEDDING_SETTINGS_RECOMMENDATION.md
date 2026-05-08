# Embedding Settings Tab Recommendation

This note describes the official, reusable way to expose Anki Census controls in host add-ons.

## Official approach

Use the built-in reusable widget from `censo_client`:

- `CensusSettingsTab`
- `CensusTabAdapter`

This is the same behavior pattern validated in Dynamic Deadline.

## Minimal integration

```python
from .censo_client import init_censo_client, CensusSettingsTab

censo = init_censo_client(
    source_addon_id="my-addon-id",
    source_addon_name="My Add-on",
    source_addon_version="1.0.0",
)

# Inside your config dialog setup:
self.tabs = QTabWidget()
self.main_tab = QWidget()
self.census_tab = CensusSettingsTab(censo_client=censo)

self.tabs.addTab(self.main_tab, "Settings")
self.tabs.addTab(self.census_tab, "Anki Census")
```

## What this tab includes

- Global participation toggle (`Pause participation globally`)
- Status line (active/paused/unavailable)
- Status preview modal (summary + payload preview)
- Developer unlock area (password `4599`)
- Developer actions:
  - View JSON
  - Copy JSON
  - Save JSON
  - Send test
  - Reset local submission state

## Why this is recommended

- Zero extra UI work for each add-on
- Consistent UX across all add-ons
- Same debug workflow as the validated Dynamic Deadline integration
- Global opt-out and global singleton behavior remain centralized in `censo_client`

## Fail-safe requirement

Keep host add-ons resilient if census initialization fails:

```python
try:
    from .censo_client import init_censo_client
    censo = init_censo_client(...)
except Exception:
    censo = None
```

If `censo is None`, keep the host add-on fully functional and show a short client-unavailable state in the tab.

## Host add-on responsibility

This module provides UI and client behavior. The host add-on remains responsible for:

- creating/opening its own config window
- adding the census widget as a dedicated tab
- handling host-specific translations if needed
