"""Global singleton collector state shared through aqt.mw runtime attributes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Set


@dataclass
class GlobalCollector:
    """Keep singleton runtime state so hooks/timers are registered only once."""

    primary_source: str
    registered_sources: Set[str] = field(default_factory=set)
    startup_started: bool = False
    hook_keys: Set[str] = field(default_factory=set)
    timer_keys: Set[str] = field(default_factory=set)

    def register_source(self, source_id: str) -> None:
        """Track one participant addon in this Anki session."""
        self.registered_sources.add(source_id)

    def run_startup_once(self, callback: Optional[Callable[[], None]]) -> bool:
        """Run callback only once, returning True when callback is executed."""
        if self.startup_started:
            return False
        self.startup_started = True
        if callback:
            callback()
        return True

    def register_hook_once(self, hook_key: str) -> bool:
        """Register a hook key exactly once for the whole session."""
        if hook_key in self.hook_keys:
            return False
        self.hook_keys.add(hook_key)
        return True

    def register_timer_once(self, timer_key: str) -> bool:
        """Register a timer key exactly once for the whole session."""
        if timer_key in self.timer_keys:
            return False
        self.timer_keys.add(timer_key)
        return True
