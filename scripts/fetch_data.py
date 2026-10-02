import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data_loader import CACHE_PATH, load_baseline


def main():
    load_baseline()
    print(f"Baseline data is ready at {CACHE_PATH}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(f"Data fetch failed: {exc}") from exc