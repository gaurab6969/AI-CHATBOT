from __future__ import annotations

import argparse
import sys
from pathlib import Path

from chatbot import DEFAULT_MODEL, generate_reply


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a single reply from chat history using Gemini."
    )
    parser.add_argument("--chat-file", help="Path to a text file containing chat history.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--api-key",
        help="Gemini API key. If omitted, uses GEMINI_API_KEY environment variable.",
    )
    parser.add_argument(
        "chat_history",
        nargs="?",
        help="Optional chat history text. If omitted, stdin is used.",
    )
    return parser


def read_chat_history(args: argparse.Namespace) -> str:
    if args.chat_file:
        path = Path(args.chat_file)
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="utf-16")
    if args.chat_history:
        return args.chat_history
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("Provide chat history as an argument, with --chat-file, or via stdin.")


def main() -> None:
    args = build_parser().parse_args()
    chat_history = read_chat_history(args).strip()
    if not chat_history:
        raise SystemExit("Chat history is empty.")
    try:
        print(generate_reply(chat_history, model=args.model, api_key=args.api_key))
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
