import unittest
from unittest import TestCase

import ChatAI
from ChatAI import ChatAI, extract_bot_response


class TestChatAI(TestCase):
    #    def setUp(self):
    def test_imagine(self):
        chat_bot = ChatAI("")
        chat_bot.init_model()
        print(chat_bot.imagine())


    def test_make_prompt_with_history(self):
        self.chat_bot = ChatAI("")

        # Define a conversation history with multiple entries
        conversation_history = [
            ("User1", "Bot1"),
            ("User2", "Bot2"),
            ("User3", "Bot3")
        ]

        # Generate a prompt with the conversation history
        prompt = self.chat_bot.make_prompt("User4's prompt", conversation_history)
        print(prompt)
        # Check that the generated prompt contains the conversation history
        self.assertIn("User:\nUser1\nBot:\nBot1", prompt)
        self.assertIn("User:\nUser2\nBot:\nBot2", prompt)
        self.assertIn("User:\nUser3\nBot:\nBot3", prompt)

    def test_make_prompt_truncate_history(self):
        self.chat_bot = ChatAI("")

        # Define a conversation history that would exceed the max_tokens limit
        conversation_history = [
            ("User1", "Bot1" * 200),  # This entry alone exceeds max_tokens
            ("User2", "Bot2"),
            ("User3", "Bot3")
        ]

        # Generate a prompt with the conversation history
        prompt = self.chat_bot.make_prompt("User4's prompt", conversation_history, max_tokens=700)
        print(prompt)
        # Check that the generated prompt contains only the last two entries
        self.assertNotIn("User:\nUser1\nBot:\nBot1", prompt)
        self.assertIn("User:\nUser2\nBot:\nBot2", prompt)
        self.assertIn("User:\nUser3\nBot:\nBot3", prompt)

    def test_make_prompt(self):
        chatai = ChatAI("Du är en chatbot.")
        expected_return = """<|endoftext|><s>
Du är en chatbot.
User:
Hej!
<s>
Bot:"""
        prompt_return = chatai.make_prompt("Hej!")
        print("Return:" + show_hidden_chars(prompt_return))
        print("Expect:" + show_hidden_chars(expected_return))
        self.assertEqual(expected_return, prompt_return)

    def test_extract_bot_response(self):
        llm_text = [" <|endoftext|><s> ",
                    " Du är en vänlig assistent. Här är en konversation mellan en människa och dig:",
                    " User:",
                    " Vad gör du?",
                    " <s>",
                    " Bot:",
                    " Vad har du råkat ut för?",
                    " /////////////",
                    " User/23/12 00:"]

        response = extract_bot_response(llm_text)
        self.assertEqual(response, "Vad har du råkat ut för?")

    def test_extract_bot_response2(self):
        llm_text = ("<|endoftext|><s> , Du är en vänlig assistent. Här är en konversation mellan en människa och dig:, "
                    "User: , Nej DU är en assistent!, <s>, Bot: Nej DU är en bot!, jóði:").split(",")

        response = extract_bot_response(llm_text)
        self.assertEqual(response, "Nej DU är en bot!")

    def test_extract_bot_response3(self):
        llm_text = ["<|endoftext|><s>"
                    "Du är en vänlig assistent. Här är en konversation mellan en människa och dig:"
                    "User:"
                    "Hej!"
                    "<s>"
                    "Bot:"
                    "Hej. Jag ser att du har en fråga. Fråga inte av personliga anledningar."]

        response = extract_bot_response(llm_text)
        self.assertEqual(response, "Hej. Jag ser att du har en fråga. Fråga inte av personliga anledningar.")

    if __name__ == '__main__':
        unittest.main()


def show_hidden_chars(text):
    # Replace newline characters with "\n" and space characters with "\s"
    visible_text = text.replace("\n", "\\n").replace(" ", "\\s")
    return visible_text
