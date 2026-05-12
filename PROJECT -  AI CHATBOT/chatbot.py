from __future__ import annotations

import argparse
import os
import re
import time
from dataclasses import dataclass
from typing import Optional, Protocol, Tuple

from coordinates import (
    CHAT_APP_ICON,
    CHAT_TEXT_SELECT_END,
    CHAT_TEXT_SELECT_START,
    CLEAR_SELECTION_CLICK,
    MESSAGE_BOX,
    Point,
)

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
DEFAULT_SENDER_NAME = os.getenv("CHATBOT_SENDER_NAME", "Gaurav")

SYSTEM_PROMPT = (
    "You are a witty but respectful multilingual assistant from India. "
    "Reply naturally in Hindi, English, or Assamese depending on the chat context. "
    "Read the chat history and produce only the next text message. "
    "Keep the reply short, human, and ready to paste. "
    "Do not include timestamps, speaker names, labels, or extra explanation."
)

MESSAGE_PATTERNS = (
    re.compile(r"^\[(?P<timestamp>[^\]]+)\]\s(?P<sender>[^:]+):\s?(?P<text>.*)$"),
    re.compile(
        r"^(?P<timestamp>\d{1,2}/\d{1,2}/\d{2,4},\s\d{1,2}:\d{2}(?:\s?[APMapm]{2})?)\s-\s"
        r"(?P<sender>[^:]+):\s?(?P<text>.*)$"
    ),
)


@dataclass(frozen=True)
class ChatMessage:
    sender: str
    text: str
    timestamp: str = ""

    @property
    def normalized_text(self) -> str:
        return " ".join(self.text.split())


@dataclass(frozen=True)
class ScreenConfig:
    chat_app_icon: Optional[Point] = CHAT_APP_ICON
    select_start: Point = CHAT_TEXT_SELECT_START
    select_end: Point = CHAT_TEXT_SELECT_END
    clear_selection_click: Optional[Point] = CLEAR_SELECTION_CLICK
    message_box: Point = MESSAGE_BOX
    drag_duration: float = 1.5
    clipboard_delay: float = 1.0


class PyAutoGUIProtocol(Protocol):
    FAILSAFE: object
    PAUSE: float

    def click(self, x: int, y: int) -> None: ...

    def moveTo(self, x: int, y: int) -> None: ...

    def dragTo(self, x: int, y: int, duration: float, button: str = "left") -> None: ...

    def hotkey(self, *keys: str) -> None: ...

    def press(self, key: str) -> None: ...

    def position(self) -> object: ...


class PyperclipProtocol(Protocol):
    def copy(self, text: str) -> None: ...

    def paste(self) -> str: ...


def log(message: str) -> None:
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")


def parse_chat_messages(chat_log: str) -> list[ChatMessage]:
    messages: list[ChatMessage] = []
    current_message: Optional[ChatMessage] = None

    for raw_line in chat_log.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue

        match = None
        for pattern in MESSAGE_PATTERNS:
            match = pattern.match(line)
            if match:
                break

        if match:
            if current_message is not None:
                messages.append(current_message)
            current_message = ChatMessage(
                sender=match.group("sender").strip(),
                text=match.group("text").strip(),
                timestamp=match.group("timestamp").strip(),
            )
            continue

        if current_message is not None:
            current_message = ChatMessage(
                sender=current_message.sender,
                text=f"{current_message.text}\n{line.strip()}",
                timestamp=current_message.timestamp,
            )

    if current_message is not None:
        messages.append(current_message)

    return messages


def get_last_message(chat_log: str) -> Optional[ChatMessage]:
    messages = parse_chat_messages(chat_log)
    if not messages:
        return None
    return messages[-1]


def is_last_message_from_sender(chat_log: str, sender_name: str = DEFAULT_SENDER_NAME) -> bool:
    last_message = get_last_message(chat_log)
    if last_message is None:
        return False
    return last_message.sender.casefold() == sender_name.casefold()


def create_genai_client(api_key: Optional[str] = None):
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Error: Gemini API key is missing. Please set the GEMINI_API_KEY environment variable or provide it via the --api-key argument."
        )

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "Error: The 'google-genai' package is not installed. Please install it using 'pip install google-genai'."
        ) from exc

    return genai.Client(api_key=api_key), types


def generate_reply(
    chat_history: str,
    *,
    model: str = DEFAULT_MODEL,
    api_key: Optional[str] = None,
    system_prompt: str = SYSTEM_PROMPT,
) -> str:
    if not chat_history.strip():
        raise ValueError("Chat history is empty.")

    client, types = create_genai_client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=chat_history,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    reply = (response.text or "").strip()
    if not reply:
        raise RuntimeError("Gemini returned an empty response.")
    return reply


def load_automation_modules() -> Tuple[PyAutoGUIProtocol, PyperclipProtocol]:
    try:
        import pyautogui  # type: ignore
        import pyperclip  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Missing desktop automation dependencies. Install `pyautogui` and `pyperclip` first."
        ) from exc

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.2
    return pyautogui, pyperclip


def click_point(pyautogui_module: PyAutoGUIProtocol, point: Optional[Point]) -> None:
    if point is None:
        return
    pyautogui_module.click(point.x, point.y)


def capture_chat_history(
    pyautogui_module: PyAutoGUIProtocol,
    pyperclip_module: PyperclipProtocol,
    screen: ScreenConfig,
) -> str:
    pyautogui_module.moveTo(screen.select_start.x, screen.select_start.y)
    pyautogui_module.dragTo(
        screen.select_end.x,
        screen.select_end.y,
        duration=screen.drag_duration,
        button="left",
    )
    pyautogui_module.hotkey("ctrl", "c")
    time.sleep(screen.clipboard_delay)
    click_point(pyautogui_module, screen.clear_selection_click)
    return pyperclip_module.paste().strip()


def send_reply(
    pyautogui_module: PyAutoGUIProtocol,
    pyperclip_module: PyperclipProtocol,
    screen: ScreenConfig,
    reply: str,
    *,
    dry_run: bool,
) -> None:
    if dry_run:
        log(f"Dry run reply: {reply}")
        return

    pyperclip_module.copy(reply)
    click_point(pyautogui_module, screen.message_box)
    time.sleep(0.5)
    pyautogui_module.hotkey("ctrl", "v")
    time.sleep(0.2)
    pyautogui_module.press("enter")
    log("Reply sent.")


def run_chatbot(
    *,
    sender_name: str,
    model: str,
    api_key: Optional[str],
    poll_interval: float,
    screen: ScreenConfig,
    dry_run: bool,
    once: bool,
) -> None:
    pyautogui_module, pyperclip_module = load_automation_modules()
    last_processed_message: Optional[tuple[str, str, str]] = None

    click_point(pyautogui_module, screen.chat_app_icon)
    time.sleep(1)
    log("Chatbot started. Move the mouse to the top-left corner to trigger PyAutoGUI failsafe.")

    while True:
        chat_history = capture_chat_history(pyautogui_module, pyperclip_module, screen)
        if not chat_history:
            log("No chat history detected in the selected area.")
        else:
            last_message = get_last_message(chat_history)
            if last_message is None:
                log("Could not parse any messages from the copied chat history.")
            else:
                signature = (
                    last_message.timestamp,
                    last_message.sender.casefold(),
                    last_message.normalized_text,
                )
                log(f"Last message detected from: {last_message.sender}")

                if last_message.sender.casefold() != sender_name.casefold():
                    log("Last message is not from the target sender. Waiting.")
                elif signature == last_processed_message:
                    log("This sender message was already handled. Skipping duplicate reply.")
                else:
                    reply = generate_reply(
                        chat_history,
                        model=model,
                        api_key=api_key,
                    )
                    send_reply(
                        pyautogui_module,
                        pyperclip_module,
                        screen,
                        reply,
                        dry_run=dry_run,
                    )
                    last_processed_message = signature

        if once:
            return
        time.sleep(poll_interval)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Monitor a copied chat region and auto-generate replies with Gemini."
    )
    parser.add_argument("--sender-name", default=DEFAULT_SENDER_NAME)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--api-key",
        help="Gemini API key. If omitted, uses GEMINI_API_KEY environment variable.",
    )
    parser.add_argument("--poll-interval", type=float, default=5.0)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate replies without pasting or sending them.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single capture cycle and exit.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        run_chatbot(
            sender_name=args.sender_name,
            model=args.model,
            api_key=args.api_key,
            poll_interval=args.poll_interval,
            screen=ScreenConfig(),
            dry_run=args.dry_run,
            once=args.once,
        )
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
