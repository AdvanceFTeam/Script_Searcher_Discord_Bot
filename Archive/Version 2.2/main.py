# Last Updated: 2024-11-20
# Version: 2.2

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
    activity = discord.Game(name="Script Searcher | /search or !search")
    await bot.change_presence(activity=activity)
    print(f"Bot is ready 🤖 | Serving in {len(bot.guilds)} servers")

@bot.command(name='search')
async def prefix_search(ctx, query: str = None, mode: str = 'free'):
    if query:
        await send_api_selection(ctx, query, mode)
    else:
        await send_help(ctx)

@bot.command(name='bothelp')
async def prefix_help(ctx):
    await send_help(ctx)

class APISelect(discord.ui.Select):
    def __init__(self, query, mode):
        self.query = query
        self.mode = mode
        options = [
            discord.SelectOption(label="ScriptBlox", value="scriptblox", description="Search scripts from ScriptBlox API"),
            discord.SelectOption(label="Rscripts", value="rscripts", description="Search scripts from Rscripts API"),
        ]
        super().__init__(placeholder="Choose an API to search scripts...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if self.values[0] == "scriptblox":
            await interaction.followup.send("Searching ScriptBlox API...")
            await search_scriptblox(interaction, self.query, self.mode)
        elif self.values[0] == "rscripts":
            await interaction.followup.send("Searching Rscripts API...")
            await search_rscripts(interaction, self.query, self.mode)

class APISearchView(discord.ui.View):
    def __init__(self, query, mode):
        super().__init__(timeout=30)
        self.query = query
        self.mode = mode
        self.add_item(APISelect(query, mode))

@bot.tree.command(name="search", description="Search for scripts")
@app_commands.describe(query="The search query", mode="Search mode (free or paid)")
async def slash_search(interaction: discord.Interaction, query: str, mode: str = 'free'):
    await interaction.response.send_message("Select the API to search scripts from:", view=APISearchView(query, mode))

@bot.tree.command(name="bothelp", description="Display help information")
async def slash_help(interaction: discord.Interaction):
    await send_help(interaction)

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

async def send_api_selection(destination, query, mode):
    if isinstance(destination, discord.Interaction):
        await destination.response.send_message("Select the API to search scripts from:", view=APISearchView(query, mode))
    else:
        await destination.send("Select the API to search scripts from:", view=APISearchView(query, mode))

async def search_scriptblox(interaction, query, mode):
    page = 1
    scriptblox_api_url = f"https://scriptblox.com/api/script/search?q={query}&mode={mode}&page={page}"

    try:
        scriptblox_response = requests.get(scriptblox_api_url)
        scriptblox_response.raise_for_status()
        scriptblox_data = scriptblox_response.json()

        if "result" in scriptblox_data and "scripts" in scriptblox_data["result"]:
            scripts = scriptblox_data["result"]["scripts"]

            if not scripts:
                await interaction.followup.send(f"No scripts found for: `{query}` in mode `{mode}`.")
                return

            message = await interaction.followup.send("Fetching data...")
            await display_scripts(interaction, message, scripts, page, scriptblox_data["result"]["totalPages"], api="scriptblox")
        else:
            await interaction.followup.send(f"No scripts found for: `{query}` in mode `{mode}`.")

    except requests.RequestException as e:
        await interaction.followup.send(f"An error occurred: {e}")
    except KeyError as ke:
        await interaction.followup.send(f"An error occurred while processing your request. Please try again later. Error: {ke}")

async def search_rscripts(interaction, query, mode):
    page = 1
    not_paid = "false" if mode == "paid" else "true"
    rscripts_api_url = f"https://rscripts.net/api/scripts?q={query}&page={page}&notPaid={not_paid}"

    try:
        rscripts_response = requests.get(rscripts_api_url)
        rscripts_response.raise_for_status()
        rscripts_data = rscripts_response.json()

        if "scripts" in rscripts_data:
            scripts = rscripts_data["scripts"]

            if not scripts:
                await interaction.followup.send(f"No scripts found for: `{query}` in mode `{mode}`.")
                return

            message = await interaction.followup.send("Fetching data...")
            await display_scripts(interaction, message, scripts, page, rscripts_data["info"]["maxPages"], api="rscripts")
        else:
            await interaction.followup.send(f"No scripts found for: `{query}` in mode `{mode}`.")

    except requests.RequestException as e:
        await interaction.followup.send(f"An error occurred: {e}")
    except KeyError as ke:
        await interaction.followup.send(f"An error occurred while processing your request. Please try again later. Error: {ke}")

async def display_scripts(interaction, message, scripts, page, total_pages, api):
    while True:
        script = scripts[page - 1]
        embed = create_embed(script, page, total_pages, api)

        view = discord.ui.View()

        if total_pages > 1:
            if page > 1:
                view.add_item(discord.ui.Button(label="⏪", style=discord.ButtonStyle.primary, custom_id="first"))
                view.add_item(discord.ui.Button(label="◀️", style=discord.ButtonStyle.primary, custom_id="previous"))
            view.add_item(discord.ui.Button(label=f"Page {page}/{total_pages}", style=discord.ButtonStyle.secondary, disabled=True))
            if page < total_pages:
                view.add_item(discord.ui.Button(label="▶️", style=discord.ButtonStyle.primary, custom_id="next"))
                view.add_item(discord.ui.Button(label="⏩", style=discord.ButtonStyle.primary, custom_id="last"))

        if api == "scriptblox":
            download_url = f"https://scriptblox.com/download/{script['_id']}"
            post_url = f"https://scriptblox.com/script/{script['slug']}"
            view.add_item(discord.ui.Button(label="Download", url=download_url, style=discord.ButtonStyle.link))
            view.add_item(discord.ui.Button(label="View", url=post_url, style=discord.ButtonStyle.link))

            copybtn = discord.ui.Button(label="Copy Script", style=discord.ButtonStyle.primary)

            async def cbc(interaction):
                await interaction.response.send_message(
                    f"```lua\n{script['script']}\n```", 
                    ephemeral=True 
                )

            copybtn.callback = cbc 
            view.add_item(copybtn) 

        await message.edit(embed=embed, view=view)

        def check(i):
            return i.user == interaction.user and i.message.id == message.id

        try:
            i = await bot.wait_for("interaction", check=check, timeout=30.0)
            if i.data["custom_id"] == "previous" and page > 1:
                page -= 1
            elif i.data["custom_id"] == "next" and page < total_pages:
                page += 1
            elif i.data["custom_id"] == "last":
                page = total_pages
            elif i.data["custom_id"] == "first":
                page = 1

            await i.response.defer()

        except asyncio.TimeoutError:
            await message.edit(content="Interaction timed out.", view=None)
            break


def create_embed(script, page, total_pages, api):
    embed = discord.Embed(color=0x206694)
    prefix, footer_icon, powered_by = "", "", ""

    if api == "scriptblox":
        prefix = "[SB]"
        footer_icon = "https://img.getimg.ai/generated/img-u1vYyfAtK7GTe9OK1BzeH.jpeg"
        powered_by = "Scriptblox"

        game = script.get("game", {})
        game_name = game.get("name", "Unknown Game")
        game_id = game.get("gameId", "")
        game_image_url = "https://scriptblox.com" + game.get("imageUrl", "")
        title = script.get("title", "No Title")
        script_content = script.get("script", "")
        views = script.get("views", 0)
        script_type = script.get("scriptType", "unknown")
        slug = script.get("slug", "")
        
        # Status Strings
        verified_status = "✅ Verified" if script.get("verified", False) else "❌ Not Verified"
        key_status = f"[Key Link]({script.get('keyLink', '')})" if script.get("key", False) else "✅ No Key"
        patched_status = "❌ Patched" if script.get("isPatched", False) else "✅ Not Patched"
        universal_status = "🌐 Universal" if script.get("isUniversal", False) else "Not Universal"
        paid_or_free = "Free" if script_type == "free" else "💲 Paid"

        # Script
        truncated_script = the_script(script_content)

        embed.title = f"{prefix} {title}"
        embed.add_field(name="Game", value=f"[{game_name}](https://www.roblox.com/games/{game_id})", inline=True)
        embed.add_field(name="Verified", value=verified_status, inline=True)
        embed.add_field(name="Script Type", value=paid_or_free, inline=True)
        embed.add_field(name="Universal", value=universal_status, inline=True)
        embed.add_field(name="Views", value=f"👁️ {views}", inline=True)
        embed.add_field(name="Key", value=key_status, inline=True)
        embed.add_field(name="Patched", value=patched_status, inline=True)
        embed.add_field(name="Links", value=f"[Raw Script](https://rawscripts.net/raw/{slug}) - [Script Page](https://scriptblox.com/script/{slug})", inline=False)
        embed.add_field(name="The Script", value=f"```lua\n{truncated_script}\n```", inline=False)
        embed.add_field(name="Timestamps", value=timestamps(script), inline=False)

        set_img_or_thumb(embed, game_image_url)
        # embed.set_footer(text=f"Made by AdvanceFalling Team | Powered by Scriptblox", icon_url="https://img.getimg.ai/generated/img-u1vYyfAtK7GTe9OK1BzeH.jpeg") # Page {page}/{total_pages}

    elif api == "rscripts":
        prefix = "[RS]"
        footer_icon = "https://i.pinimg.com/564x/bf/d3/f6/bfd3f6c59e5af5a52187bf35064b0705.jpg"
        powered_by = "Rscripts"

        title = script.get("title", "No Title")
        slug = script.get("slug", "")
        views = script.get("views", 0)
        likes = script.get("likes", 0)
        dislikes = script.get("dislikes", 0)
        date = format_datetime(script.get("date", ""))
        mobile_ready = "📱 Mobile Ready" if script.get("mobileReady", False) else "🚫 Not Mobile Ready"
        verified_status = "✅ Verified" if script.get("verified", False) else "❌ Not Verified"
        patched_status = "❌ Patched" if script.get("patched", False) else "✅ Not Patched"
        script_content = script.get("download", "")

        # User Info
        user = script.get("user", [{}])[0]
        user_name = user.get("username", "Unknown")
        user_avatar_url = f"https://rscripts.net/assets/avatars/{user.get('image', 'default.png')}"

        # Script
        script_text = f"```lua\nloadstring(game:HttpGet(\"https://rscripts.net/raw/{script_content}\"))()\n```" if script_content else "⚠️ No script content available."

        embed.title = f"{prefix} {title}"
        embed.add_field(name="Views", value=f"👁️ {views}", inline=True)
        embed.add_field(name="Likes", value=f"👍 {likes}", inline=True)
        embed.add_field(name="Dislikes", value=f"👎 {dislikes}", inline=True)
        embed.add_field(name="Mobile", value=mobile_ready, inline=True)
        embed.add_field(name="Verified", value=verified_status, inline=True)
        embed.add_field(name="Patched", value=patched_status, inline=True)
        embed.add_field(name="The Script", value=script_text, inline=False)
        embed.add_field(name="Links", value=f"[Script Page](https://rscripts.net/script/{slug})", inline=False)
        embed.add_field(name="Date", value=date, inline=True)

        embed.set_author(name=user_name, icon_url=user_avatar_url)

    embed.set_footer(text=f"Made by AdvanceFalling Team | Powered by {powered_by}", icon_url=footer_icon)
    return embed

# dont ask
def the_script(script_content, max_length=400):
    if len(script_content) > max_length:
        return script_content[:max_length - 3] + "..."
    return script_content

# formatting...
def timestamps(script):
    created_at = format_datetime(script.get("createdAt", ""))
    updated_at = format_datetime(script.get("updatedAt", ""))
    return f"**Created At:** {created_at}\n**Updated At:** {updated_at}"


def set_img_or_thumb(embed, url):
    try:
        if url and validators.url(url):
            embed.set_image(url=url)
        else:
            embed.set_image(url="https://c.tenor.com/jnINmQlMNbsAAAAC/tenor.gif")
    except Exception as e:
        print(f"Error setting image URL: {e}")
        embed.set_image(url="https://c.tenor.com/jnINmQlMNbsAAAAC/tenor.gif")

def format_datetime(dt_str):
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    except ValueError:
        dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    delta = relativedelta(now, dt)

    if delta.years > 0:
        time_ago = f"{delta.years} years ago"
    elif delta.months > 0:
        time_ago = f"{delta.months} months ago"
    elif delta.days > 0:
        time_ago = f"{delta.days} days ago"
    elif delta.hours > 0:
        time_ago = f"{delta.hours} hours ago"
    elif delta.minutes > 0:
        time_ago = f"{delta.minutes} minutes ago"
    else:
        time_ago = "just now"

    formatted_date = dt.strftime("%m/%d/%Y | %I:%M:%S %p")
    return f"{time_ago} | {formatted_date}"

async def run_bot():
    while True:
        try:
            await bot.start(TOKEN)
        except (discord.ConnectionClosed, discord.GatewayNotFound) as e:
            print(f"Disconnected due to: {e}. Attempting to reconnect...")
            await asyncio.sleep(5)

if TOKEN:
    asyncio.run(run_bot())
else:
    print("Error: Token is None. Please set your BOT_TOKEN in your environment(.env).")
