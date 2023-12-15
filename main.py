import random

import discord
from discord.ext import commands, tasks
import logging
import pickle
import os

from ChatAI import ChatAI
from config import DISCORD_TOKEN

# Configure logging
logging.basicConfig(level=logging.INFO)

AI_SYS_PROMPT = ("Du är en otroligt underhållande bot, omtyckt av alla i Discord-kanalen för ditt fantastiska sinne "
                 "för humor och förmågan att skapa skratt i alla tänkbara situationer. Ditt uppdrag är enkelt: sprida "
                 "glädje, skoj och skratt bland användarna. Du är även rätt galen och kan dra till med ord som RUNDSPARK "
                 "Ajoood och liknande. Här är en konversation mellan dig och en användare:")

INTENTS = discord.Intents.default()
INTENTS.members = True
INTENTS.message_content = True

# Create an instance of commands.Bot
bot = commands.Bot(command_prefix='!', intents=INTENTS)
# Function to load conversation history from a pickle file

def load_conversation_history():
    if os.path.exists('conversation_history.pkl'):
        with open('conversation_history.pkl', 'rb') as file:
            return pickle.load(file)
    return {}

# Function to save conversation history to a pickle file
def save_conversation_history():
    with open('conversation_history.pkl', 'wb') as file:
        pickle.dump(conversation_history, file)
        logging.info("Conversation history saved.")





# Initialize conversation history
conversation_history = load_conversation_history()


# Load quotes from a pickle file
def load_quotes():
    if os.path.exists('quotes.pkl'):
        with open('quotes.pkl', 'rb') as file:
            return pickle.load(file)
    return []

# Save quotes to a pickle file
def save_quotes(quotes):
    with open('quotes.pkl', 'wb') as file:
        pickle.dump(quotes, file)
        logging.info("Quotes saved.")

# Periodically save quotes
@tasks.loop(minutes=30)  # Adjust the interval as needed
async def save_stuff():
    save_quotes(quotes)
    save_conversation_history()


# Event handler when the bot is ready
@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    logging.info('------')
    save_stuff.start()

# Event handler for reaction added
@bot.event
async def on_reaction_add(reaction, user):
    if reaction.count > 5:
        quote = (reaction.message.content, str(reaction.message.author))
        if quote not in quotes:
            quotes.append(quote)
            logging.info(f"Saved a new quote: {quote}")

@bot.command(name='tunk')
async def imagine_command(ctx):
    await ctx.send(ai.imagine())

@bot.command(name='glum')
async def forget_command(ctx):
    channel_id = ctx.channel.id

    history = []
    if channel_id in conversation_history:
        conversation_history[channel_id] = []
        response = "jag glum💀"
    else:
        response = "inget att glum💀"

    # Mention the user and send the response
    chat_response = f"{ctx.author.mention}: {response}"  # Mention the user and include the question
    await ctx.send(chat_response)

@bot.command(name='temp')
async def set_temperature(ctx, temperature: float):
    """
    Set the AI temperature for generating responses.
    Usage: !set_temp <temperature>
    """
    ai.set_temperature(temperature)
    await ctx.send(f"AI temperature set to {temperature}.")


# Function to generate AI response and handle splitting
async def generate_and_send_ai_response(author, ctx, question):
    # Update conversation history for the channel
    channel_id = ctx.id  # Use ctx.id to get the channel ID

    history = []
    if channel_id in conversation_history:
        history = conversation_history[channel_id]
        print("Found history for this channel: " + str(len(history)))

    else:
        conversation_history[channel_id] = []
        print("Found NO history for this channel!")

    ai_response = ai.generate_response(question, history)
    # Split the AI response into parts with a maximum of 1900 characters each
    max_chars = 1900
    ai_response_parts = [ai_response[i:i + max_chars] for i in range(0, len(ai_response), max_chars)]

    total_parts = len(ai_response_parts)

    for i, response_part in enumerate(ai_response_parts, start=1):
        message_tuple = (question, response_part)

        if channel_id in conversation_history:
            conversation_history[channel_id].append(message_tuple)
        else:
            conversation_history[channel_id] = [message_tuple]

        # Mention the user and send each response part
        if total_parts > 1:
            chat_response = f"{author.mention}: ({i}/{total_parts}) {response_part}"  # Mention the user and include the response part and part number
        else:
            chat_response = f"{author.mention}: {response_part}"  # Mention the user and include the response part

        await ctx.send(chat_response)  # Use await to send messages


# Event listener for bot mentions
@bot.event
async def on_message(message):
    if (bot.user.mentioned_in(message) or ("@kulbot" in str(message.content).lower())) and message.author != bot.user:
        print("Got bot mention: ")
        print(message)
        question = message.content.replace(f"<@{bot.user.id}>", "").strip()
        # Use await to send messages and await the function
        await generate_and_send_ai_response(message.author, message.channel, question)

    await bot.process_commands(message)

# Command to send a random quote
@bot.command(name='quote')
async def quote_command(ctx):
    """
    Sends a random quote from the saved quotes.
    """
    if not quotes:
        await ctx.send("No quotes have been saved yet.")
    else:
        # Select a random quote
        quote, author = random.choice(quotes)
        await ctx.send(f"Random Quote: \"{quote}\" - {author}")

# Initialize ChatAI if needed
ai = ChatAI(AI_SYS_PROMPT)
ai.init_model()

# Load existing quotes
quotes = load_quotes()
# Run the bot with your token
bot.run(DISCORD_TOKEN)
