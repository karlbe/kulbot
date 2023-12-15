import datetime
import re
import time

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch


class ChatAI:
    ALWAYS_PROMPT = ""

    # MODEL_PATH = "../gpt-sw3-1.3b"
    MODEL_PATH = "../gpt-sw3-356m"
    tokenizer = None
    model = None
    stop_token_id = None

    def __init__(self, always_prompt):
        self.TEMPERATURE = 0.6
        self.MAX_TOKENS = 500
        self.ALWAYS_PROMPT = always_prompt
        print("Started ChatAI!")

    def init_model(self):
        start_time = time.time()

        device = "cuda:0" if torch.cuda.is_available() else "cpu"

        # Initialize Tokenizer & Model
        self.tokenizer = AutoTokenizer.from_pretrained(self.MODEL_PATH)
        self.model = AutoModelForCausalLM.from_pretrained(self.MODEL_PATH)
        self.model.eval()
        self.model.to(device)

        # Assuming 'Människan:' is the stop token
        stop_token = 'User:'
        stop_token_ids = self.tokenizer.encode(stop_token, return_tensors="pt")

        # Extract the item from the tensor
        self.stop_token_id = stop_token_ids[0, -1].item()
        elapsed_time = time.time() - start_time
        elapsed_time_str = str(datetime.timedelta(seconds=elapsed_time))

        print(f'Init took {elapsed_time_str}')

    def imagine(self):
        bot_responses = self.simple_query("Tänk på vanliga företeelser i livet, som kanske en del aldrig tänkt på, och fortsätt den här meningen. Har ni tänkt på att", 0.99)
        imagined = bot_responses[0][103:]
        return filter_output(imagined)

    def simple_query(self, prompt, temp):
        if self.model is None:
            print("Model not initialized!")
            exit(0)

        input_ids = self.tokenizer(prompt, return_tensors="pt").input_ids.to(
            "cuda")

        outputs = self.model.generate(
            inputs=input_ids,
            max_new_tokens=200,
            num_beams=1,
            temperature=temp,
            do_sample=True
        )

        # Decode and print the model's response
        bot_response = self.tokenizer.decode(outputs[0])

        return bot_response.split("\n")

    def make_prompt(self, prompt, conversation_history=None, max_tokens=200):
        START_TOKENS = "<|endoftext|><s>"
        END_USER_TEXT_TOKEN = "<s>"

        system_prompt = ""
        convo_history = ""

        if conversation_history is None:
            conversation_history = []

        if len(self.ALWAYS_PROMPT) > 0:
            system_prompt = self.ALWAYS_PROMPT

        # Calculate the size of system_prompt, tokens, and other elements
        conversation_history_string = ""

        # Initialize the size of system_prompt, tokens, and other elements
        system_prompt_size = len(system_prompt)
        start_tokens_size = len(START_TOKENS)

        # Create a list to hold conversation history tuples in reverse order
        reverse_history = conversation_history[::-1]

        # Iterate through the conversation history tuples in reverse chronological order
        for user_question, bot_response in reverse_history:
            user_message = f"User:\n{user_question}\n"
            bot_message = f"Bot:\n{bot_response}\n"
            message_size = len(user_message) + len(bot_message)

            # Calculate the size of return_prompt after adding the conversation history message
            return_prompt_size = (
                    start_tokens_size +
                    system_prompt_size +
                    len(conversation_history_string) + message_size +
                    len("User:\n") + len(prompt) + len(END_USER_TEXT_TOKEN + "\nBot:")
            )

            # Check if adding the message would exceed max_tokens
            if return_prompt_size <= max_tokens:
                conversation_history_string = user_message + bot_message + conversation_history_string
            else:
                # print("Bot message too large to fit within max_tokens, excluding it:")
                # print(bot_message)
                break

        if len(system_prompt) > 0:
            system_prompt = system_prompt.strip() + "\n"

        if len(conversation_history_string) > 0:
            convo_history = conversation_history_string.strip() + "\n"

        return_prompt = (
                START_TOKENS + "\n" +
                system_prompt +
                convo_history +
                "User:\n" + prompt + "\n" +
                END_USER_TEXT_TOKEN + "\n" +
                "Bot:"
        )

        return return_prompt.strip()

    def generate_response(self, prompt, conversation_history=None):
        if conversation_history is None:
            conversation_history = []
        if self.model is None:
            print("Model not initialized!")
            exit(0)

        input_ids = self.tokenizer(self.make_prompt(prompt, conversation_history, self.MAX_TOKENS), return_tensors="pt").input_ids.to(
            "cuda")

        outputs = self.model.generate(
            inputs=input_ids,
            max_new_tokens=self.MAX_TOKENS,
            num_beams=1,
            temperature=self.TEMPERATURE,
            eos_token_id=self.stop_token_id,
            do_sample=True
        )

        # Decode and print the model's response
        bot_response = self.tokenizer.decode(outputs[0])

        bot_responses = bot_response.split("\n")
        print(repr(bot_responses[2:]))

        found_response: str = extract_bot_response(bot_responses)
        if "<|endoftext|>" in found_response:
            found_response = found_response[:found_response.find("<|endoftext|>")]

        found_response = check_and_fix_repetition(found_response)

        return filter_output(found_response)

    def set_temperature(self, temperature):
        if 0 < temperature < 1:
            self.TEMPERATURE = temperature
            return True
        else:
            return False


def check_and_fix_repetition(message, max_repeats=3):
    # Split the message into words
    words = message.split()

    # Create a regular expression pattern to find repeated sequences of words
    pattern = r'(\b\w+\b)(?:.*\1){' + str(max_repeats) + r',}'

    # Find all repeated sequences of words in the message
    repeated_sequences = re.findall(pattern, message)

    # If repeated sequences found, replace them in the message
    if repeated_sequences:
        for repeated_sequence in repeated_sequences:
            fixed_sequence = repeated_sequence.split()[0]  # Keep only the first occurrence
            message = message.replace(repeated_sequence, fixed_sequence, 1)

    return message


def extract_bot_response(llm_output):
    # Iterate through the list elements
    tags_found = 0
    for current_row, line in enumerate(llm_output):
        if "<s>" in line:
            tags_found += 1
        # Check if the current line contains " Bot:"
        if "Bot:" in line and tags_found > 1:
            # Split the line based on " Bot:"
            parts = line.split("Bot:")
            # Check if there are parts after " Bot:"
            if len(parts) > 1 and len(parts[1].strip()) > 0:
                return parts[1].strip()  # Use the part after " Bot:"
            else:
                # If there's nothing after " Bot:", look for the next line
                next_line_index = current_row + 1
                if next_line_index < len(llm_output):
                    return llm_output[next_line_index].strip()
                else:
                    return None  # No response found if there is no subsequent line

    return None  # No response found if " Bot:" is not present in any line

def filter_output(text):
    # Remove single quotes, double quotes, and parentheses
    text = re.sub(r"[\"\'\(\)]", "", text)

    # Additional filtering if needed
    # Add more patterns and replacements as necessary

    return text