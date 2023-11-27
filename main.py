import inspect
import uuid
import random

import discord
from discord import Object
from discord.ext import commands
import os
import pickle
import asyncio
import time
import torch
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from config import DISCORD_TOKEN

# Initialize Variables
model_name = "../gpt-sw3-126m"
device = "cuda:0" if torch.cuda.is_available() else "cpu"
prompt = "Träd är fina för att"

# Initialize Tokenizer & Model
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)
model.eval()
model.to(device)

# Create an instance of the Intents class and enable the members intent
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
QUOTE_THRESHOLD = 5  # Number of reactions + number of mentions required to save quote
INITIAL_HISTORY_LIMIT = 2000


# Define the bot's command prefix
bot = commands.Bot(command_prefix='!', intents=intents)

# Define a dictionary to store the number of interactions with Clyde
clyde_count = {}
quotes = {}

last_message = {}




def main():
    global clyde_count, quotes, last_message
    # Define a dictionary to store the number of interactions with Clyde

    loop = asyncio.get_event_loop()

    # Start the bot with the specified token
    try:
        # Load saved data
        last_message = load_data('last_message.pickle', dict())

        quotes = load_data('quotes.pickle', dict())

        print(f"{len(quotes)} quotes")

        with open('quotes.pickle', 'wb') as f:
            pickle.dump(quotes, f)

        # Run the bot
        bot.run(bot_token)

    finally:
        print("shutting down")

        # Save data on shutdown
        print("Saving data...")

        save_all()

        loop.run_until_complete(bot.close())
        print("finished shutting down")


async def save_periodically(interval=300):
    while True:
        print("Scheduled data save, whoho!")
        save_all()
        await asyncio.sleep(interval)


def save_all():
    save_data(quotes, 'quotes.pickle')
    save_data(last_message, 'last_message.pickle')

def save_data(data, file):
    if data is not None:
        print("Saving to " + file)
        print(data)
        with open(file, 'wb') as f:
            pickle.dump(data, f)

def load_data(file, default):
    print("Loading " + file + ":")
    return_value = default
    if os.path.isfile(file):
        try:
            with open(file, 'rb') as f:
                loaded_data = pickle.load(f)
                if loaded_data is not None:
                    print(loaded_data)
                    return_value = loaded_data
        except Exception as e:
            print(f"Exception during pickle load of {file}: {e}")
        finally:
            if return_value is None:
                print("WHY IS NONE")
            return return_value
    return return_value



@bot.event
async def on_raw_reaction_add(payload):
    message_id = payload.message_id
    channel_id = payload.channel_id

    message = await bot.get_channel(channel_id).fetch_message(message_id)
    reactions = message.reactions

    if len(reactions) > QUOTE_THRESHOLD:
        if save_quote(message.id, message.author.display_name, message.content, len(reactions)):
            await message.channel.send("New quote added: " + message.content)


# Define an event to track all messages and count interactions with Clyde
@bot.event
async def on_message(message: discord.Message):

    await process_message(message)

    # Let the bot process commands as usual
    await bot.process_commands(message)


# Define a command to display a user's Clyde interaction count
def printInvokeMessage(ctx, method):
    print(f"{ctx.author} invoked {method}")


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')

    # Loop through all servers the bot is connected to and store discussions
    for server in bot.guilds:
        if server.id not in last_message.keys():
            last_message[server.id] = None
        print(f"Replaying discussions for {server.name} since " + str(last_message[server.id]))
        await replay_discussions(server, last_message[server.id])
    loop = asyncio.get_event_loop()
    loop.create_task(save_periodically(interval=300))


async def get_original_author(message):
    if message.reference is not None:
        if message.reference.cached_message is None:
            # Fetching the message
            channel = bot.get_channel(message.reference.channel_id)
            msg = await channel.fetch_message(message.reference.message_id)
        else:
            msg = message.reference.cached_message
        return str(msg.author)
    else:
        return None

async def process_message(message: discord.Message):
    global last_message

    if message.author == bot.user:
        return

    original_author = await get_original_author(message)

    if original_author is not None:
        original_author_str = " >> " + str(original_author)
    else:
        original_author_str = ""

    print(f"{message.created_at}: {message.author}: {message.content} ({message.channel.name}){original_author_str}")

    if message.guild.id not in last_message or last_message[message.guild.id] is None:
        last_message[message.guild.id] = 0

    if last_message[message.guild.id] < message.id:
        last_message[message.guild.id] = message.id



async def replay_discussions(guild, from_message_id):
    channel: discord.TextChannel

    for channel in guild.text_channels:
        # Check if bot has access to the channel
        bot_member = guild.get_member(bot.user.id)
        permissions = channel.permissions_for(bot_member)
        if not permissions.view_channel:
            continue
        if from_message_id is None:
            print("Replaying with limit...")
            async for message in channel.history(limit=INITIAL_HISTORY_LIMIT):
                await process_message(message)
        else:
            print("Replaying with snowflake...")
            snowflake: Object = Object(from_message_id)
            async for message in channel.history(after=snowflake, limit=INITIAL_HISTORY_LIMIT):
                await process_message(message)

        print(f"All messages replayed for: {channel.name}")
    print(f"All messages replayed for: {guild.name}")



@bot.command(name='quote')
async def quote(ctx, *, text):
    """
    Save a quote to the quote database.
    Usage: !savequote <quote>
    """
    author = None
    words = text.split()
    for word in words:
        if word.endswith(":"):
            author = word
            break

    if author is None:
        author = 'random_idiot'

    quote_str = ' '.join(words)
    save_quote(time.time_ns, author, quote_str, None)
    await ctx.send(f'Quote saved from {author}: {quote_str}')


def save_quote(msg_id, author, quote_str, reaction_count):
    global quotes
    if msg_id not in quotes.keys():
        quotes[msg_id] = {'text': quote_str, 'reactions': reaction_count, 'author': author}
        print(f"Quote saved, quote length: {len(quotes)}")
        return True
    else:
        return False


@bot.command(name='randomquote')
async def random_quote(ctx):
    """
    Retrieve a random quote from the quote database.
    Usage: !randomquote
    """
    if not quotes:
        await ctx.send('No quotes saved yet.')
        return

    selected_quote = random.choice(quotes)
    author = selected_quote['author']
    reactions = selected_quote['reactions']
    text = selected_quote['text']
    if reactions > 0:
        reaction_text = " (" + str(reactions) + " reactions)"
    else:
        reaction_text = ""

    await ctx.send(f'{author}: {text}{reaction_text}')


@bot.command(name='clyde')
async def random_quote(ctx):
    await ctx.send(f'            Till minne av Clyde\n'
                   f'                 2023-2023\n'                   
                   f'"En vänlig AI-assistent som alltid stod till tjänst."')

@bot.command()
async def start_game(ctx):
    """Starts the reaction game."""
    await ctx.send("React with :thumbsup: to win the round!")

    def check(reaction, user):
        return user != bot.user and str(reaction.emoji) == '👍'

    winner = await bot.wait_for('reaction_add', check=check)
    await ctx.send(f"{winner[1].name} has won the round!")


if __name__ == '__main__':
    main()