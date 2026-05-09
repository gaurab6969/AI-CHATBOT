import unittest

from chatbot import get_last_message, is_last_message_from_sender, parse_chat_messages


class ChatbotParsingTests(unittest.TestCase):
    def test_parse_bracketed_whatsapp_messages(self) -> None:
        chat_log = (
            "[21:00, 12/6/2024] Gaurav: Hello there\n"
            "[21:01, 12/6/2024] Satyam: Hi, what's up?"
        )
        messages = parse_chat_messages(chat_log)

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].sender, "Gaurav")
        self.assertEqual(messages[1].text, "Hi, what's up?")

    def test_parse_multiline_message(self) -> None:
        chat_log = (
            "[21:00, 12/6/2024] Gaurav: First line\n"
            "Second line\n"
            "[21:01, 12/6/2024] Satyam: Reply"
        )
        messages = parse_chat_messages(chat_log)

        self.assertEqual(messages[0].text, "First line\nSecond line")

    def test_parse_export_format_messages(self) -> None:
        chat_log = (
            "12/6/2024, 21:00 - Gaurav: Hello there\n"
            "12/6/2024, 21:01 - Satyam: Hi"
        )
        last_message = get_last_message(chat_log)

        self.assertIsNotNone(last_message)
        self.assertEqual(last_message.sender, "Satyam")
        self.assertEqual(last_message.text, "Hi")

    def test_is_last_message_from_sender(self) -> None:
        chat_log = (
            "[21:00, 12/6/2024] Satyam: Ping\n"
            "[21:01, 12/6/2024] Gaurav: Pong"
        )
        self.assertTrue(is_last_message_from_sender(chat_log, "Gaurav"))
        self.assertFalse(is_last_message_from_sender(chat_log, "Satyam"))


if __name__ == "__main__":
    unittest.main()
