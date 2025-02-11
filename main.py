# Last Updated: 2025-02-11
# Version: 2.4

import discord
from discord.ext import commands
from discord import app_commands
import requests
import os
import asyncio
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
import validators
import urllib.parse

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
FALLBACK_IMAGE = "https://c.tenor.com/jnINmQlMNbsAAAAC/tenor.gif"
intents = discord.Intents.default()
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_searches = {}
    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    activity = discord.Game(name="Script Searcher | /search or !search")
    await bot.change_presence(activity=activity)
    print(f"Bot is ready 🤖 | Serving in {len(bot.guilds)} servers")

def fetch_scripts(api, query, mode, page):
    try:
        if api == "scriptblox":
            params = {"q": query, "script name": query, "mode": mode, "page": page}
            query_string = urllib.parse.urlencode(params, safe=' ')
            url = f"https://scriptblox.com/api/script/search?{query_string}"
            # just use my proxy api if the scriptblox api doesnt work
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
            }
            r = requests.get(url, headers=headers)
            # r = requests.get(url)
            r.raise_for_status()
            data = r.json()
            if "result" in data and "scripts" in data["result"]:
                scripts = data["result"]["scripts"]
                total_pages = data["result"].get("totalPages", None)
                return scripts, total_pages, None
            else:
                return None, None, f"No scripts found for query `{query}`."
        elif api == "rscripts":
            not_paid = False if mode.lower() == "paid" else True
            params = {"q": query, "page": page, "notPaid": not_paid}
            query_string = urllib.parse.urlencode(params)
            url = f"https://rscripts.net/api/v2/scripts?{query_string}"
            r = requests.get(url)
            r.raise_for_status()
            data = r.json()
            if "scripts" in data:
                scripts = data["scripts"]
                return scripts, None, None
            else:
                return None, None, f"No scripts found for query `{query}`."
    except requests.RequestException as e:
        return None, None, f"Error occurred: {e}"
    except KeyError as ke:
        return None, None, f"Error processing data: {ke}"

def format_datetime(dt_str):
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            return "Unknown"
    now = datetime.now(timezone.utc)
    delta = relativedelta(now, dt)
    if delta.years > 0:
        ago = f"{delta.years} years ago"
    elif delta.months > 0:
        ago = f"{delta.months} months ago"
    elif delta.days > 0:
        ago = f"{delta.days} days ago"
    elif delta.hours > 0:
        ago = f"{delta.hours} hours ago"
    elif delta.minutes > 0:
        ago = f"{delta.minutes} minutes ago"
    else:
        ago = "just now"
    formatted = dt.strftime("%m/%d/%Y | %I:%M:%S %p")
    return f"{ago} | {formatted}"

def format_timestamps(script):
    created = format_datetime(script.get("createdAt", ""))
    updated = format_datetime(script.get("updatedAt", ""))
    return f"**Created At:** {created}\n**Updated At:** {updated}"

def create_embed(script, page, total_items, api):
    embed = discord.Embed(color=0x206694)
    if api == "scriptblox":
        embed.title = f"[SB] {script.get('title', 'No Title')}"
        game = script.get("game", {})
        game_name = game.get("name", "Unknown Game")
        game_id = game.get("gameId", "")
        game_image_url = f"https://scriptblox.com{game.get('imageUrl', '')}" if game.get('imageUrl') else FALLBACK_IMAGE
        views = script.get("views", 0)
        script_type = "Free" if script.get("scriptType", "free").lower() == "free" else "Paid"
        verified_status = "✅ Verified" if script.get("verified", False) else "❌ Not Verified"
        key_status = f"[Key Link]({script.get('keyLink', '')})" if script.get("key", False) else "✅ No Key"
        patched_status = "❌ Patched" if script.get("isPatched", False) else "✅ Not Patched"
        universal_status = "🌐 Universal" if script.get("isUniversal", False) else "Not Universal"
        truncated_script = script.get("script", "No Script")
        if len(truncated_script) > 400:
            truncated_script = truncated_script[:397] + "..."
        embed.add_field(name="Game", value=f"[{game_name}](https://www.roblox.com/games/{game_id})", inline=True)
        embed.add_field(name="Verified", value=verified_status, inline=True)
        embed.add_field(name="Type", value=script_type, inline=True)
        embed.add_field(name="Universal", value=universal_status, inline=True)
        embed.add_field(name="Views", value=f"👁️ {views}", inline=True)
        embed.add_field(name="Key", value=key_status, inline=True)
        embed.add_field(name="Patched", value=patched_status, inline=True)
        embed.add_field(name="Links", value=f"[Raw Script](https://rawscripts.net/raw/{script.get('slug','')}) - [Script Page](https://scriptblox.com/script/{script.get('slug','')})", inline=False)
        embed.add_field(name="Script", value=f"```lua\n{truncated_script}\n```", inline=False)
        embed.add_field(name="Timestamps", value=format_timestamps(script), inline=False)
        if validators.url(game_image_url):
            embed.set_image(url=game_image_url)
        else:
            embed.set_image(url=FALLBACK_IMAGE)
    elif api == "rscripts":
        embed.title = f"[RS] {script.get('title', 'No Title')}"
        views = script.get("views", 0)
        likes = script.get("likes", 0)
        dislikes = script.get("dislikes", 0)
        date_str = script.get("lastUpdated") or script.get("createdAt", "")
        date = format_datetime(date_str)
        mobile_ready = "📱 Mobile Ready" if script.get("mobileReady", False) else "🚫 Not Mobile Ready"
        user = script.get("user", {})
        verified_status = "✅ Verified" if user.get("verified", False) else "❌ Not Verified"
        paid_status = "💲 Paid" if script.get("paid", False) else "🆓 Free"
        raw_script = script.get("rawScript", "")
        script_text = f"```lua\nloadstring(game:HttpGet(\"{raw_script}\"))()\n```" if raw_script else "⚠️ No script content."
        user_name = user.get("username", "Unknown")
        user_avatar_url = user.get("image", FALLBACK_IMAGE)
        embed.add_field(name="Views", value=f"👁️ {views}", inline=True)
        embed.add_field(name="Likes", value=f"👍 {likes}", inline=True)
        embed.add_field(name="Dislikes", value=f"👎 {dislikes}", inline=True)
        embed.add_field(name="Mobile", value=mobile_ready, inline=True)
        embed.add_field(name="Verified", value=verified_status, inline=True)
        embed.add_field(name="Cost", value=paid_status, inline=True)
        embed.add_field(name="Script", value=script_text, inline=False)
        embed.add_field(name="Links", value=f"[Script Page](https://rscripts.net/script/{script.get('slug','')})", inline=False)
        embed.add_field(name="Date", value=date, inline=True)
        embed.set_author(name=user_name, icon_url=user_avatar_url)
        image_url = script.get("image")
        if validators.url(image_url):
            embed.set_image(url=image_url)
        else:
            embed.set_image(url=FALLBACK_IMAGE)
    embed.set_footer(text=f"Made by AdvanceFalling Team | Powered by {'Scriptblox' if api=='scriptblox' else 'Rscripts'} | Page {page}/{total_items}")
    return embed

async def display_scripts_dynamic(interaction, message, query, mode, api):
    current_page = 1
    while True:
        scripts, total_pages, error = fetch_scripts(api, query, mode, current_page)
        if error:
            await interaction.followup.send(error)
            break
        if not scripts:
            await interaction.followup.send("No scripts found.")
            break
        script = scripts[0]
        display_total = total_pages if total_pages is not None else "Unknown"
        embed = create_embed(script, current_page, display_total, api)
        view = discord.ui.View(timeout=60)
        if total_pages is None:
            if current_page > 1:
                view.add_item(discord.ui.Button(label="◀️", style=discord.ButtonStyle.primary, custom_id="previous", row=0))
            view.add_item(discord.ui.Button(label=f"Page {current_page}/?", style=discord.ButtonStyle.secondary, disabled=True, row=0))
            view.add_item(discord.ui.Button(label="▶️", style=discord.ButtonStyle.primary, custom_id="next", row=0))
        else:
            if current_page > 1:
                view.add_item(discord.ui.Button(label="⏪", style=discord.ButtonStyle.primary, custom_id="first", row=0))
                view.add_item(discord.ui.Button(label="◀️", style=discord.ButtonStyle.primary, custom_id="previous", row=0))
            view.add_item(discord.ui.Button(label=f"Page {current_page}/{display_total}", style=discord.ButtonStyle.secondary, disabled=True, row=0))
            if current_page < total_pages:
                view.add_item(discord.ui.Button(label="▶️", style=discord.ButtonStyle.primary, custom_id="next", row=0))
                view.add_item(discord.ui.Button(label="⏩", style=discord.ButtonStyle.primary, custom_id="last", row=0))
        if api == "scriptblox":
            post_url = f"https://scriptblox.com/script/{script.get('slug','')}"
            raw_url = f"https://rawscripts.net/raw/{script.get('slug','')}"
            download_url = f"https://scriptblox.com/download/{script.get('_id','')}"
        else:
            post_url = f"https://rscripts.net/script/{script.get('slug','')}"
            raw_url = script.get("rawScript", "")
            download_url = raw_url
        view.add_item(discord.ui.Button(label="View", url=post_url, style=discord.ButtonStyle.link, row=1))
        view.add_item(discord.ui.Button(label="Raw", url=raw_url, style=discord.ButtonStyle.link, row=1))
        view.add_item(discord.ui.Button(label="Download", url=download_url, style=discord.ButtonStyle.link, row=1))
        copy_button = discord.ui.Button(label="Copy", style=discord.ButtonStyle.primary, row=1)
        async def copy_callback(btn_interaction):
            if api == "scriptblox":
                content = script.get("script", "")
            else:
                raw_url_local = script.get("rawScript", "")
                content = f'loadstring(game:HttpGet("{raw_url_local}"))()'
            await btn_interaction.response.send_message(f"```lua\n{content}\n```", ephemeral=True)
        copy_button.callback = copy_callback
        view.add_item(copy_button)
        await message.edit(embed=embed, view=view)
        def check(i: discord.Interaction):
            return i.user == interaction.user and i.message.id == message.id
        try:
            i: discord.Interaction = await bot.wait_for("interaction", check=check, timeout=30.0)
            cid = i.data.get("custom_id")
            if cid == "previous" and current_page > 1:
                current_page -= 1
            elif cid == "next" and (total_pages is None or current_page < total_pages):
                current_page += 1
            elif cid == "last" and total_pages is not None:
                current_page = total_pages
            elif cid == "first":
                current_page = 1
            await i.response.defer()
        except asyncio.TimeoutError:
            await message.edit(content="Interaction timed out.", view=None)
            break

async def display_scripts_local(interaction, message, scripts, api):
    if not scripts:
        await interaction.followup.send("No scripts found.")
        return
    page = 1
    total_items = len(scripts)
    while True:
        script = scripts[page - 1]
        embed = create_embed(script, page, total_items, api)
        view = discord.ui.View(timeout=60)
        if total_items > 1:
            if page > 1:
                view.add_item(discord.ui.Button(label="⏪", style=discord.ButtonStyle.primary, custom_id="first", row=0))
                view.add_item(discord.ui.Button(label="◀️", style=discord.ButtonStyle.primary, custom_id="previous", row=0))
            view.add_item(discord.ui.Button(label=f"Page {page}/{total_items}", style=discord.ButtonStyle.secondary, disabled=True, row=0))
            if page < total_items:
                view.add_item(discord.ui.Button(label="▶️", style=discord.ButtonStyle.primary, custom_id="next", row=0))
                view.add_item(discord.ui.Button(label="⏩", style=discord.ButtonStyle.primary, custom_id="last", row=0))
        if api == "scriptblox":
            post_url = f"https://scriptblox.com/script/{script.get('slug','')}"
            raw_url = f"https://rawscripts.net/raw/{script.get('slug','')}"
            download_url = f"https://scriptblox.com/download/{script.get('_id','')}"
        else:
            post_url = f"https://rscripts.net/script/{script.get('slug','')}"
            raw_url = script.get("rawScript", "")
            download_url = raw_url
        view.add_item(discord.ui.Button(label="View", url=post_url, style=discord.ButtonStyle.link, row=1))
        view.add_item(discord.ui.Button(label="Raw", url=raw_url, style=discord.ButtonStyle.link, row=1))
        view.add_item(discord.ui.Button(label="Download", url=download_url, style=discord.ButtonStyle.link, row=1))
        copy_button = discord.ui.Button(label="Copy", style=discord.ButtonStyle.primary, row=1)
        async def copy_callback(btn_interaction):
            if api == "scriptblox":
                content = script.get("script", "")
            else:
                raw_url_local = script.get("rawScript", "")
                content = f'loadstring(game:HttpGet("{raw_url_local}"))()'
            await btn_interaction.response.send_message(f"```lua\n{content}\n```", ephemeral=True)
        copy_button.callback = copy_callback
        view.add_item(copy_button)
        await message.edit(embed=embed, view=view)
        def check(i):
            return i.user == interaction.user and i.message.id == message.id
        try:
            i = await bot.wait_for("interaction", check=check, timeout=30.0)
            cid = i.data.get("custom_id")
            if cid == "previous" and page > 1:
                page -= 1
            elif cid == "next" and page < total_items:
                page += 1
            elif cid == "last":
                page = total_items
            elif cid == "first":
                page = 1
            await i.response.defer()
        except asyncio.TimeoutError:
            await message.edit(content="Interaction timed out.", view=None)
            break

async def send_help(destination):
    help_message = (
        "**Script Searcher Help**\n\n"
        "Use these commands to interact with the bot:\n\n"
        "**Prefix Commands:**\n"
        "`!search <query> [mode]` - Search scripts. Example: `!search arsenal paid`.\n"
        "`!bothelp` - Show help.\n\n"
        "**Slash Commands:**\n"
        "`/search <query> [mode]` - Search scripts. Example: `/search arsenal paid`.\n"
        "`/bothelp` - Show help.\n\n"
        "Modes: `free`, `paid`\n"
        "Default mode is `free`."
    )
    embed = discord.Embed(title="🔍 Script Search Help", description=help_message, color=0x3498db)
    embed.set_thumbnail(url="https://media1.tenor.com/m/j9Jhn5M1Xw0AAAAd/neuro-sama-ai.gif")
    if isinstance(destination, discord.Interaction):
        await destination.response.send_message(embed=embed, ephemeral=True)
    else:
        await destination.send(embed=embed)

@bot.command(name='bothelp')
async def prefix_help(ctx):
    await send_help(ctx)

@bot.tree.command(name="bothelp", description="Display help information")
async def slash_help(interaction: discord.Interaction):
    await send_help(interaction)

@bot.command(name='search')
async def prefix_search(ctx, query: str = None, mode: str = 'free'):
    if query:
        await send_api_selection(ctx, query, mode)
    else:
        await send_help(ctx)

class APISelect(discord.ui.Select):
    def __init__(self, query, mode):
        self.query = query
        self.mode = mode
        options = [
            discord.SelectOption(label="ScriptBlox", value="scriptblox", description="Search scripts from ScriptBlox API"),
            discord.SelectOption(label="Rscripts", value="rscripts", description="Search scripts from RScripts API"),
        ]
        super().__init__(placeholder="Choose the API to search scripts...", min_values=1, max_values=1, options=options)
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if self.values[0] == "scriptblox":
            await interaction.followup.send("Searching ScriptBlox API...")
            temp_msg = await interaction.followup.send("Fetching data...", ephemeral=True)
            await display_scripts_dynamic(interaction, temp_msg, self.query, self.mode, api="scriptblox")
        elif self.values[0] == "rscripts":
            await interaction.followup.send("Searching RScripts API...")
            temp_msg = await interaction.followup.send("Fetching data...", ephemeral=True)
            scripts, _, error = fetch_scripts("rscripts", self.query, self.mode, 1)
            if error:
                await interaction.followup.send(error)
                return
            await display_scripts_local(interaction, temp_msg, scripts, api="rscripts")

class APISearchView(discord.ui.View):
    def __init__(self, query, mode):
        super().__init__(timeout=60)
        self.add_item(APISelect(query, mode))

async def send_api_selection(destination, query, mode):
    if isinstance(destination, discord.Interaction):
        await destination.response.send_message("Select the API to search scripts from:", view=APISearchView(query, mode))
    else:
        await destination.send("Select the API to search scripts from:", view=APISearchView(query, mode))

@bot.tree.command(name="search", description="Search for scripts")
@app_commands.describe(query="The search query", mode="Search mode (free or paid)")
async def slash_search(interaction: discord.Interaction, query: str, mode: str = 'free'):
    await interaction.response.send_message("Select the API to search scripts from:", view=APISearchView(query, mode))

async def run_bot():
    while True:
        try:
            await bot.start(TOKEN)
        except (discord.ConnectionClosed, discord.GatewayNotFound) as e:
            print(f"Disconnected due to: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

if TOKEN:
    asyncio.run(run_bot())
else:
    print("Error: BOT_TOKEN not set in environment.")
