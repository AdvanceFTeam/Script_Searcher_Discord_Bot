import discord
from discord.ext import commands
from discord import app_commands
import requests
import os
import asyncio
import random
from dotenv import load_dotenv
import validators

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.message_content = True

class MyBot(commands.Bot):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_searches = {}

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot(command_prefix='!', intents=intents)

max_content_length = 200

@bot.event
async def on_ready():
    activity = discord.Game(name="Script Searcher | !search and /search")
    await bot.change_presence(activity=activity)
    print("Bot is ready 🤖")

@bot.command()
async def search(ctx, query=None, mode='free'):
    await execute_search(ctx, query, mode, prefix=True)

@bot.tree.command(name="search", description="Search for scripts")
@app_commands.describe(query="The search query",
                       mode="Search mode ('free' or 'paid')")
async def slash_search(interaction: discord.Interaction,
                       query: str = None,
                       mode: str = 'free'):
    ctx = await bot.get_context(interaction)
    await execute_search(ctx, query, mode, prefix=False)

async def execute_search(ctx, query, mode, prefix):
    user_id = ctx.author.id
    try:
        if user_id in bot.active_searches:
            message = await ctx.send("You already have an active search running. Please wait for the first command to complete.")
            await asyncio.sleep(random.randint(5, 10))
            await message.delete()
            return

        bot.active_searches[user_id] = True

        if query is None:
            help_message = (
                "Use `!search <query>` to find scripts.\n\n"
                "You can specify the search mode (default is `free`).\n"
                "**Modes**: `free`, `paid`\n"
                "**Example**: `!search arsenal paid`\n\n"
                "Please provide a query to get started."
            )
            initial_embed = discord.Embed(
                title="🔍 Script Search Help",
                description=help_message,
                color=0x3498db
            )
            initial_embed.set_thumbnail(url="https://media1.tenor.com/m/j9Jhn5M1Xw0AAAAd/neuro-sama-ai.gif")
            await ctx.send(embed=initial_embed)
            del bot.active_searches[user_id]
            return

        page = 1
        api_url = f"https://scriptblox.com/api/script/search?q={query}&mode={mode}&page={page}"

        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()

        if "result" in data and "scripts" in data["result"]:
            scripts = data["result"]["scripts"]

            if not scripts:
                await ctx.send("No scripts found!")
                del bot.active_searches[user_id]
                return

            message = await ctx.send("Fetching data...")

            await display_scripts(ctx, message, scripts, page, data["result"]["totalPages"], prefix)
        else:
            await ctx.send("No scripts found!")
    except requests.RequestException as e:
        await ctx.send(f"An error occurred: {e}")
    except KeyError as ke:
        await ctx.send(f"An error occurred while processing your request. Please try again later. Error: {ke}")
    finally:
        if user_id in bot.active_searches:
            del bot.active_searches[user_id]


async def display_scripts(ctx, message, scripts, page, total_pages, prefix):
    while True:
        embed = create_embed(scripts[page - 1], page, total_pages)
        await message.edit(embed=embed, content=None)

        await message.clear_reactions()

        if total_pages > 1:
            if page > 1:
                await message.add_reaction("⬅️")
            if page < total_pages:
                await message.add_reaction("➡️")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"]

        try:
            reaction, _ = await bot.wait_for("reaction_add", check=check, timeout=30.0)

            if str(reaction.emoji) == "⬅️" and page > 1:
                page -= 1
            elif str(reaction.emoji) == "➡️" and page < total_pages:
                page += 1

        except asyncio.TimeoutError:
            if prefix:
                timeout_message = await ctx.send("You took too long to interact.")
                await asyncio.sleep(5)
                await timeout_message.delete()
            else:
                await ctx.send("You took too long to interact.", ephemeral=True)
            break

def create_embed(script, page, total_pages):
    game_name = script["game"]["name"]
    game_id = script["game"]["gameId"]
    title = script["title"]
    script_type = script["scriptType"]
    script_content = script["script"]
    views = script["views"]
    verified = script["verified"]
    has_key = script.get("key", False)
    key_link = script.get("keyLink", "")
    is_patched = script.get("isPatched", False)
    is_universal = script.get("isUniversal", False)
    created_at = script["createdAt"]
    updated_at = script["updatedAt"]
    game_image_url = "https://scriptblox.com" + script["game"].get("imageUrl", "")

    paid_or_free = "Free" if script_type == "free" else "💲 Paid"
    verified_status = "✅ Verified" if verified else "❌ Not Verified"
    key_status = f"[Key Link]({key_link})" if has_key and key_link else ("🔑 Has Key" if has_key else "✅ No Key")
    patched_status = "❌ Patched" if is_patched else "✅ Not Patched"
    universal_status = "🌐 Universal" if is_universal else "Not Universal"
    truncated_script_content = (script_content[:max_content_length - 3] + "..." if len(script_content) > max_content_length else script_content)

    embed = discord.Embed(title=title, color=0x206694)

    embed.add_field(name="Game", value=f"[{game_name}](https://www.roblox.com/games/{game_id})", inline=True)
    embed.add_field(name="Verified", value=verified_status, inline=True)
    embed.add_field(name="Script Type", value=paid_or_free, inline=True)
    embed.add_field(name="Universal", value=universal_status, inline=True)
    embed.add_field(name="Views", value=f"👁️ {views}", inline=True)
    embed.add_field(name="Key", value=key_status, inline=True)
    embed.add_field(name="Patched", value=patched_status, inline=True)
    embed.add_field(name="Script Content", value=f"```lua\n{truncated_script_content}\n```", inline=False)
    embed.add_field(name="", value=f"**Created At:** {created_at}\n**Updated At:** {updated_at}", inline=False)

    set_image_or_thumbnail(embed, game_image_url)

    embed.set_footer(text=f"Made by AdvanceFalling Team | Page {page}/{total_pages}", 
                     icon_url="https://img.getimg.ai/generated/img-u1vYyfAtK7GTe9OK1BzeH.jpeg")
    
    return embed

def set_image_or_thumbnail(embed, url):
    try:
        if url and validators.url(url):
            embed.set_image(url=url)
        else:
            embed.set_image(url="https://c.tenor.com/jnINmQlMNbsAAAAC/tenor.gif")
    except Exception as e:
        print(f"Error setting image URL: {e}")
        embed.set_image(url="https://c.tenor.com/jnINmQlMNbsAAAAC/tenor.gif")
        
        
    ''' Old Code you can use: if you want the image or thumbnail to be smaller
    try:
        if game_image_url and validators.url(game_image_url):
            embed.set_thumbnail(url=game_image_url)
        else:
            embed.set_thumbnail(url="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR8U6yuDVz_6IYqS9cM2oJpGzrM9o-hZT_k21aqQclWBA&s")
    except Exception as e:
        print(f"Error setting thumbnail URL: {e}")
        embed.set_thumbnail(url="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR8U6yuDVz_6IYqS9cM2oJpGzrM9o-hZT_k21aqQclWBA&s")
    '''

bot.run(TOKEN)
