"""One ordered installation for both the production CLI and Edge fixtures."""
from pathlib import Path


def recorder_script() -> str:
    root = Path(__file__).resolve().parent
    return '\n'.join((root / name).read_text(encoding='utf-8-sig')
                     for name in ('selectors.js', 'intelligence.js', 'capture.js'))
