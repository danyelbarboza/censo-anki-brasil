"""Small runtime checks for the reusable client behavior without full Anki UI."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass

from . import bootstrap, config


@dataclass
class _FakePm:
    """Minimal profile manager stub used by self-check tests."""

    profile_dir: str

    def profileFolder(self) -> str:
        """Return fake profile path."""
        return self.profile_dir


@dataclass
class _FakeMw:
    """Minimal mw stub that supports runtime attributes and profile path resolution."""

    profile_dir: str

    def __post_init__(self):
        """Attach fake profile manager."""
        self.pm = _FakePm(self.profile_dir)


def run_self_check() -> dict:
    """Run deterministic checks for singleton, idempotency, and global config behavior."""
    with tempfile.TemporaryDirectory(prefix="anki-census-selfcheck-") as tmp:
        fake_mw = _FakeMw(tmp)
        bootstrap.mw = fake_mw
        config.mw = fake_mw

        client_a = bootstrap.init_censo_client("addon-a", "Addon A", "1.0.0")
        collector_a = getattr(fake_mw, "_anki_census_global_collector", None)

        client_b = bootstrap.init_censo_client("addon-b", "Addon B", "2.0.0")
        collector_b = getattr(fake_mw, "_anki_census_global_collector", None)

        cfg = config.load_global_config()
        client_a.set_participation_paused(True)
        paused_cfg = config.load_global_config()

        config_path = config.get_shared_config_path()
        with open(config_path, "w", encoding="utf-8") as handle:
            handle.write("{invalid json")
        recovered_cfg = config.load_global_config()

        return {
            "single_collector": collector_a is collector_b and collector_a is not None,
            "source_registered": sorted((cfg.get("registered_sources") or {}).keys()),
            "opt_out_shared": bool(client_b.is_participation_paused()) and bool(paused_cfg.get("participation_paused")),
            "corrupted_json_recovery": bool(recovered_cfg.get("anonymous_user_id")),
            "legacy_alias_present": hasattr(fake_mw, "_anki_census_legacy_global_collector"),
            "config_path": os.path.normpath(config_path),
            "client_preview_has_sources": bool(client_a.get_current_payload_preview().get("source_addons_detected")),
        }


if __name__ == "__main__":
    print(json.dumps(run_self_check(), ensure_ascii=False, indent=2))
