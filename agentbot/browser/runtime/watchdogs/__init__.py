from .dom_watchdog import DOMWatchdog
from .dialogs_watchdog import DialogsWatchdog
from .default_action_watchdog import DefaultActionWatchdog
from .downloads_watchdog import DownloadsWatchdog
from .lifecycle_watchdog import LifecycleWatchdog
from .navigation_watchdog import NavigationWatchdog
from .popups_watchdog import PopupsWatchdog

__all__ = [
    "DOMWatchdog",
    "DefaultActionWatchdog",
    "DialogsWatchdog",
    "DownloadsWatchdog",
    "LifecycleWatchdog",
    "NavigationWatchdog",
    "PopupsWatchdog",
]
