from __future__ import annotations

import argparse
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    x: int
    y: int


CHAT_APP_ICON = Point(1639, 1412)
CHAT_TEXT_SELECT_START = Point(972, 202)
CHAT_TEXT_SELECT_END = Point(2213, 1278)
CLEAR_SELECTION_CLICK = Point(1994, 281)
MESSAGE_BOX = Point(1808, 1328)


def track_mouse_position(interval: float = 0.25, show_repeated: bool = False) -> None:
    try:
        import pyautogui
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency: install `pyautogui` before tracking coordinates."
        ) from exc

    last_position = None
    while True:
        current_position = pyautogui.position()
        if show_repeated or current_position != last_position:
            print(f"x={current_position.x}, y={current_position.y}")
            last_position = current_position
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print mouse coordinates so you can capture automation points."
    )
    parser.add_argument("--interval", type=float, default=0.25)
    parser.add_argument(
        "--show-repeated",
        action="store_true",
        help="Print every sample instead of only changed positions.",
    )
    args = parser.parse_args()

    try:
        track_mouse_position(interval=args.interval, show_repeated=args.show_repeated)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    except KeyboardInterrupt:
        print("\nStopped coordinate tracking.")


if __name__ == "__main__":
    main()
