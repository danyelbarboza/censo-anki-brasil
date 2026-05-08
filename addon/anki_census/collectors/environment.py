import platform
import sys
from aqt import appVersion

def collect_environment():
    try:
        from aqt.qt import QT_VERSION_STR
        qt_major = str(QT_VERSION_STR).split('.')[0]
    except Exception:
        qt_major = "unknown"
    return {
        "anki_version": str(appVersion),
        "platform": platform.system() or "unknown",
        "platform_release": platform.release() or "unknown",
        "python_major_version": str(sys.version_info.major),
        "qt_major_version": qt_major,
        "machine": platform.machine() or "unknown",
    }
