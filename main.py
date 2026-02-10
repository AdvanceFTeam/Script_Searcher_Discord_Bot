# Last Updated: 2026-02-10
# Version: 2.6

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
    activity = discord.Game(name="Script Searcher | v3.0")
    await bot.change_presence(activity=activity)
    print(f"Bot is ready 🤖 | Serving in {len(bot.guilds)} servers")
    print(f"Commands: /search, /fetch, /trending, /script, /executors, /rscripts_*")

def fetch_scripts(api, query, mode, page, **filters):
    try:
        if api == "scriptblox":
            params = {"q": query, "mode": mode, "page": page}
            if filters.get("verified") is not None:
                params["verified"] = 1 if filters["verified"] else 0
            if filters.get("patched") is not None:
                params["patched"] = 1 if filters["patched"] else 0
            if filters.get("key") is not None:
                params["key"] = 1 if filters["key"] else 0
            if filters.get("universal") is not None:
                params["universal"] = 1 if filters["universal"] else 0
            if filters.get("sortBy"):
                params["sortBy"] = filters["sortBy"]
            if filters.get("order"):
                params["order"] = filters["order"]
            if filters.get("strict") is not None:
                params["strict"] = "true" if filters["strict"] else "false"
            if filters.get("owner"):
                params["owner"] = filters["owner"]
            if filters.get("placeId"):
                params["placeId"] = filters["placeId"]
            
            query_string = urllib.parse.urlencode(params)
            url = f"https://scriptblox.com/api/script/search?{query_string}"
            r = requests.get(url)
            r.raise_for_status()
            data = r.json()
            if "result" in data and "scripts" in data["result"]:
                scripts = data["result"]["scripts"]
                total_pages = data["result"].get("totalPages", None)
                return scripts, total_pages, None
            else:
                return None, None, f"Couldn't find any scripts matching '{query}'"
        elif api == "rscripts":
            not_paid = False if mode.lower() == "paid" else True
            params = {"q": query, "page": page, "notPaid": not_paid}
            if filters.get("noKeySystem") is not None:
                params["noKeySystem"] = filters["noKeySystem"]
            if filters.get("mobileOnly") is not None:
                params["mobileOnly"] = filters["mobileOnly"]
            if filters.get("verifiedOnly") is not None:
                params["verifiedOnly"] = filters["verifiedOnly"]
            if filters.get("unpatched") is not None:
                params["unpatched"] = filters["unpatched"]
            if filters.get("orderBy"):
                params["orderBy"] = filters["orderBy"]
            if filters.get("sort"):
                params["sort"] = filters["sort"]
            
            query_string = urllib.parse.urlencode(params)
            url = f"https://rscripts.net/api/v2/scripts?{query_string}"
            r = requests.get(url)
            r.raise_for_status()
            data = r.json()
            if "scripts" in data:
                scripts = data["scripts"]
                return scripts, None, None
            else:
                return None, None, f"Couldn't find any scripts matching '{query}'"
    except requests.RequestException as e:
        return None, None, f"Something went wrong: {e}"
    except KeyError as ke:
        return None, None, f"Unexpected response format: {ke}"

def fetch_scripts_from_api(api, endpoint, page=1, **params):
    try:
        if api == "scriptblox":
            if page and page > 1:
                params["page"] = page
            query_string = urllib.parse.urlencode(params) if params else ""
            url = f"https://scriptblox.com/api/script/{endpoint}"
            if query_string:
                url += f"?{query_string}"
        elif api == "rscripts":
            if page and page > 1:
                params["page"] = page
            query_string = urllib.parse.urlencode(params) if params else ""
            url = f"https://rscripts.net/api/v2/{endpoint}"
            if query_string:
                url += f"?{query_string}"
        
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        return data, None
    except requests.RequestException as e:
        return None, f"Something went wrong: {e}"
    except Exception as e:
        return None, f"Unexpected response format: {e}"
# ugly code right here yes 
def fetch_trending(api):
    try:
        if api == "scriptblox":
            url = "https://scriptblox.com/api/script/trending"
            r = requests.get(url)
            r.raise_for_status()
            data = r.json()
            if "result" in data and "scripts" in data["result"]:
                trending_scripts = data["result"]["scripts"]
                full_scripts = []
                for script_meta in trending_scripts:
                    slug = script_meta.get("slug")
                    if slug:
                        try:
                            script_url = f"https://scriptblox.com/api/script/{slug}"
                            script_r = requests.get(script_url)
                            script_r.raise_for_status()
                            script_data = script_r.json()
                            if "script" in script_data:
                                full_scripts.append(script_data["script"])
                        except:
                            continue
                return full_scripts, None
            return None, "Nothing trending right now"
        elif api == "rscripts":
            url = "https://rscripts.net/api/v2/trending"
            r = requests.get(url)
            r.raise_for_status()
            data = r.json()
            if "success" in data:
                scripts = []
                for item in data["success"]:
                    script_data = item.get("script", {})
                    if script_data:
                        script_data["views"] = item.get("views", 0)
                        user_data = item.get("user", {})
                        if user_data:
                            script_data["user"] = user_data
                        scripts.append(script_data)
                return scripts, None
            return None, "Nothing is trending right now"
    except requests.RequestException as e:
        return None, f"bad: something went wrong: {e}"
    except Exception as e:
        return None, f"bad response = format broke or something: {e}"

def fetch_script_by_id(api, script_id):
    try:
        if api == "scriptblox":
            url = f"https://scriptblox.com/api/script/{script_id}"
            r = requests.get(url)
            r.raise_for_status()
            data = r.json()
            if "script" in data:
                return data["script"], None
            return None, f"Couldn't find script '{script_id}'"
        elif api == "rscripts":
            url = f"https://rscripts.net/api/v2/script?id={script_id}"
            r = requests.get(url)
            r.raise_for_status()
            data = r.json()
            if "script" in data and len(data["script"]) > 0:
                return data["script"][0], None
            return None, f"Couldn't find script '{script_id}'"
    except requests.RequestException as e:
        return None, f"Something went wrong: {e}"
    except Exception as e:
        return None, f"Unexpected response format: {e}"

def fetch_executors():
    try:
        url = "https://scriptblox.com/api/executor/list"
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        return data, None
    except requests.RequestException as e:
        return None, f"bad = went wrong: {e}"
    except Exception as e:
        return None, f"something went wrong: response format: {e}"
    

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
        if game_id:
            game_link = f"https://www.roblox.com/games/{game_id}"
        else:
            game_link = "https://www.roblox.com"        
        script_image = script.get("image", FALLBACK_IMAGE)
        views = script.get("views", 0)
        script_type = "Free" if script.get("scriptType", "free").lower() == "free" else "Paid"
        verified_status = "✅ Verified" if script.get("verified", False) else "❌ Not Verified"
        key_status = f"[Key Link]({script.get('keyLink', '')})" if script.get("key", False) else "✅ No Key"
        patched_status = "❌ Patched" if script.get("isPatched", False) else "✅ Not Patched"
        universal_status = "🌐 Universal" if script.get("isUniversal", False) else "Not Universal"
        truncated_script = script.get("script", "No Script")
        if len(truncated_script) > 400:
            truncated_script = truncated_script[:397] + "..."
        embed.add_field(name="Game", value=f"[{game_name}]({game_link})", inline=True)
        embed.add_field(name="Verified", value=verified_status, inline=True)
        embed.add_field(name="Type", value=script_type, inline=True)
        embed.add_field(name="Universal", value=universal_status, inline=True)
        embed.add_field(name="Views", value=f"👁️ {views}", inline=True)
        embed.add_field(name="Key", value=key_status, inline=True)
        embed.add_field(name="Patched", value=patched_status, inline=True)
        embed.add_field(name="Links", value=f"[Raw Script](https://rawscripts.net/raw/{script.get('slug','')}) - [Script Page](https://scriptblox.com/script/{script.get('slug','')})", inline=False)
        embed.add_field(name="Script", value=f"```lua\n{truncated_script}\n```", inline=False)
        embed.add_field(name="Timestamps", value=format_timestamps(script), inline=False)
        if validators.url(script_image):
            embed.set_image(url=script_image)
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
    embed.set_footer(text=f"Made by AdvanceFalling Team | Powered by {'ScriptBlox' if api=='scriptblox' else 'RScripts'} | Page {page}/{total_items}")
    return embed

async def display_scripts_dynamic(interaction, message, query, mode, api, **filters):
    current_page = 1
    while True:
        scripts, total_pages, error = fetch_scripts(api, query, mode, current_page, **filters)
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
    
    scripts_per_page = 5
    page = 0
    total_pages = (len(scripts) - 1) // scripts_per_page + 1
    
    def create_multi_script_embed(page_num):
        embed = discord.Embed(
            title=f"{'📊 ScriptBlox' if api == 'scriptblox' else '📜 RScripts'} Scripts",
            description=f"Showing {len(scripts)} script{'s' if len(scripts) != 1 else ''}",
            color=0x206694
        )
        
        start = page_num * scripts_per_page
        end = min(start + scripts_per_page, len(scripts))
        
        for idx, script in enumerate(scripts[start:end], start=start+1):
            if api == "scriptblox":
                title = script.get("title", "No Title")
                game = script.get("game", {}).get("name", "Unknown Game")
                verified = "✅" if script.get("verified", False) else "❌"
                patched = "❌" if script.get("isPatched", False) else "✅"
                views = script.get("views", 0)
                slug = script.get("slug", "")
                
                value = f"**Game:** {game}\n"
                value += f"**Verified:** {verified} | **Patched:** {patched}\n"
                value += f"**Views:** 👁️ {views}\n"
                value += f"[View](https://scriptblox.com/script/{slug}) | [Raw](https://rawscripts.net/raw/{slug})"
                
                embed.add_field(name=f"{idx}. {title}", value=value, inline=False)
            else:
                title = script.get("title", "No Title")
                views = script.get("views", 0)
                likes = script.get("likes", 0)
                verified = "✅" if script.get("user", {}).get("verified", False) else "❌"
                slug = script.get("slug", "")
                
                value = f"**Views:** 👁️ {views} | **Likes:** 👍 {likes}\n"
                value += f"**Verified:** {verified}\n"
                value += f"[View](https://rscripts.net/script/{slug})"
                
                embed.add_field(name=f"{idx}. {title}", value=value, inline=False)
        
        embed.set_footer(text=f"Made by AdvanceFalling Team | Page {page_num + 1}/{total_pages}")
        return embed
    
    while True:
        embed = create_multi_script_embed(page)
        view = discord.ui.View(timeout=60)
        
        if total_pages > 1:
            if page > 0:
                view.add_item(discord.ui.Button(label="⏪", style=discord.ButtonStyle.primary, custom_id="first", row=0))
                view.add_item(discord.ui.Button(label="◀️", style=discord.ButtonStyle.primary, custom_id="previous", row=0))
            view.add_item(discord.ui.Button(label=f"Page {page + 1}/{total_pages}", style=discord.ButtonStyle.secondary, disabled=True, row=0))
            if page < total_pages - 1:
                view.add_item(discord.ui.Button(label="▶️", style=discord.ButtonStyle.primary, custom_id="next", row=0))
                view.add_item(discord.ui.Button(label="⏩", style=discord.ButtonStyle.primary, custom_id="last", row=0))
        
        await message.edit(embed=embed, view=view)
        
        def check(i):
            return i.user == interaction.user and i.message.id == message.id
        
        try:
            i = await bot.wait_for("interaction", check=check, timeout=30.0)
            cid = i.data.get("custom_id")
            
            if cid == "previous" and page > 0:
                page -= 1
            elif cid == "next" and page < total_pages - 1:
                page += 1
            elif cid == "last":
                page = total_pages - 1
            elif cid == "first":
                page = 0
            
            await i.response.defer()
        except asyncio.TimeoutError:
            await message.edit(content="Interaction timed out.", view=None)
            break

async def send_help(destination):
    embed = discord.Embed(
        title="🔍 Script Searcher Bot",
        description="Search and browse scripts from ScriptBlox and RScripts",
        color=0x3498db
    )
    
    search_commands = (
        "**`/search <query>`** - Search scripts across both APIs\n"
        "├ `mode` - Free or paid scripts\n"
        "├ `verified` - Only verified scripts\n"
        "├ `patched` - Filter by patch status\n"
        "├ `key_system` - Filter key requirements\n"
        "├ `universal` - Universal scripts only\n"
        "├ `mobile_only` - Mobile compatible\n"
        "├ `sort_by` - Sort by views, likes, date\n"
        "└ `sort_order` - Ascending or descending\n\n"
        "**`/fetch`** - Browse ScriptBlox scripts\n"
        "├ All search filters plus:\n"
        "├ `owner` - Filter by creator\n"
        "├ `place_id` - Specific game ID\n"
        "└ `max_results` - Limit results (1-20)\n"
    )
    embed.add_field(name="Search & Browse", value=search_commands, inline=False)
    
    rscripts_commands = (
        "**`/rscripts_fetch`** - Browse RScripts library\n"
        "├ `verified_only` - Verified scripts\n"
        "├ `no_key_system` - No keys required\n"
        "├ `mobile_only` - Mobile ready\n"
        "├ `unpatched` - Unpatched scripts\n"
        "└ `order_by` - Sort options\n\n"
        "**`/rscripts_by_user <username>`** - Creator's scripts\n"
    )
    embed.add_field(name="RScripts Commands", value=rscripts_commands, inline=False)
    
    other_commands = (
        "**`/trending`** - Hot scripts right now\n"
        "**`/script <id>`** - Get specific script\n"
        "**`/executors`** - List all executors\n"
        "**`!search <query>`** - Legacy search\n"
    )
    embed.add_field(name="Other Commands", value=other_commands, inline=False)
    
    examples = (
        "• `/search arsenal verified:True`\n"
        "• `/rscripts_fetch no_key_system:True`\n"
        "• `/rscripts_by_user pcallskeleton`\n"
        "• `/trending api:scriptblox`\n"
    )
    embed.add_field(name="💡 Examples", value=examples, inline=False)
    
    embed.set_thumbnail(url="https://media1.tenor.com/m/j9Jhn5M1Xw0AAAAd/neuro-sama-ai.gif")
    embed.set_footer(text="Made by AdvanceFalling Team | v2.6")
    
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
    def __init__(self, query, mode, filters=None):
        self.query = query
        self.mode = mode
        self.filters = filters or {}
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
            await display_scripts_dynamic(interaction, temp_msg, self.query, self.mode, api="scriptblox", **self.filters)
        elif self.values[0] == "rscripts":
            await interaction.followup.send("Searching RScripts API...")
            temp_msg = await interaction.followup.send("Fetching data...", ephemeral=True)
            scripts, _, error = fetch_scripts("rscripts", self.query, self.mode, 1, **self.filters)
            if error:
                await interaction.followup.send(error)
                return
            await display_scripts_local(interaction, temp_msg, scripts, api="rscripts")

class APISearchView(discord.ui.View):
    def __init__(self, query, mode, filters=None):
        super().__init__(timeout=60)
        self.add_item(APISelect(query, mode, filters))

async def send_api_selection(destination, query, mode):
    if isinstance(destination, discord.Interaction):
        await destination.response.send_message("Select the API to search scripts from:", view=APISearchView(query, mode))
    else:
        await destination.send("Select the API to search scripts from:", view=APISearchView(query, mode))

@bot.tree.command(name="search", description="Search for scripts with advanced filters")
@app_commands.describe(
    query="The search query",
    mode="Search mode (free or paid)",
    verified="Filter by verified status",
    patched="Filter by patched status (ScriptBlox only)",
    key_system="Filter by key system requirement",
    universal="Filter by universal scripts (ScriptBlox only)",
    mobile_only="Mobile ready scripts only (RScripts only)",
    sort_by="Sort by field (views, likes, date, etc.)",
    sort_order="Sort order (asc or desc)"
)
async def slash_search(
    interaction: discord.Interaction, 
    query: str, 
    mode: str = 'free',
    verified: bool = None,
    patched: bool = None,
    key_system: bool = None,
    universal: bool = None,
    mobile_only: bool = None,
    sort_by: str = None,
    sort_order: str = None
):
    filters = {}
    if verified is not None:
        filters["verified"] = verified
        filters["verifiedOnly"] = verified
    if patched is not None:
        filters["patched"] = patched
    if key_system is not None:
        filters["key"] = key_system
        filters["noKeySystem"] = not key_system
    if universal is not None:
        filters["universal"] = universal
    if mobile_only is not None:
        filters["mobileOnly"] = mobile_only
    if sort_by:
        filters["sortBy"] = sort_by
        filters["orderBy"] = sort_by
    if sort_order:
        filters["order"] = sort_order
        filters["sort"] = sort_order
    
    await interaction.response.send_message("Select the API to search scripts from:", view=APISearchView(query, mode, filters))

@bot.tree.command(name="fetch", description="Fetch scripts from ScriptBlox with advanced filters")
@app_commands.describe(
    mode="Script mode (free or paid)",
    verified="Filter by verified status",
    patched="Filter by patched status",
    key_system="Filter by key system",
    universal="Filter universal scripts",
    sort_by="Sort by (views, likeCount, createdAt, updatedAt, dislikeCount)",
    sort_order="Sort order (asc or desc)",
    owner="Filter by owner username",
    place_id="Filter by game place ID",
    max_results="Maximum results per page (1-20)"
)
async def slash_fetch(
    interaction: discord.Interaction,
    mode: str = 'free',
    verified: bool = None,
    patched: bool = None,
    key_system: bool = None,
    universal: bool = None,
    sort_by: str = None,
    sort_order: str = None,
    owner: str = None,
    place_id: str = None,
    max_results: int = 20
):
    await interaction.response.defer()
    params = {"mode": mode, "max": max_results}
    if verified is not None:
        params["verified"] = 1 if verified else 0
    if patched is not None:
        params["patched"] = 1 if patched else 0
    if key_system is not None:
        params["key"] = 1 if key_system else 0
    if universal is not None:
        params["universal"] = 1 if universal else 0
    if sort_by:
        params["sortBy"] = sort_by
    if sort_order:
        params["order"] = sort_order
    if owner:
        params["owner"] = owner
    if place_id:
        params["placeId"] = place_id
    
    data, error = fetch_scripts_from_api("scriptblox", "fetch", **params)
    if error:
        await interaction.followup.send(f"❌ {error}")
        return
    
    if "result" in data and "scripts" in data["result"]:
        scripts = data["result"]["scripts"]
        if not scripts:
            await interaction.followup.send("No scripts found with the specified filters.")
            return
        temp_msg = await interaction.followup.send("Fetching data...")
        await display_scripts_local(interaction, temp_msg, scripts, api="scriptblox")
    else:
        await interaction.followup.send("No scripts found.")

@bot.tree.command(name="trending", description="View trending scripts")
@app_commands.describe(api="Choose API (scriptblox or rscripts)")
async def slash_trending(interaction: discord.Interaction, api: str = "scriptblox"):
    await interaction.response.defer()
    if api.lower() not in ["scriptblox", "rscripts"]:
        await interaction.followup.send("❌ Invalid API. Choose 'scriptblox' or 'rscripts'.")
        return
    
    scripts, error = fetch_trending(api.lower())
    if error:
        await interaction.followup.send(f"❌ {error}")
        return
    
    if not scripts:
        await interaction.followup.send("No trending scripts found.")
        return
    
    temp_msg = await interaction.followup.send("Fetching trending scripts...")
    await display_scripts_local(interaction, temp_msg, scripts, api=api.lower())

@bot.tree.command(name="script", description="Fetch a specific script by ID or slug")
@app_commands.describe(
    script_id="The script ID or slug",
    api="Choose API (scriptblox or rscripts)"
)
async def slash_script(interaction: discord.Interaction, script_id: str, api: str = "scriptblox"):
    await interaction.response.defer()
    if api.lower() not in ["scriptblox", "rscripts"]:
        await interaction.followup.send("❌ Invalid API. Choose 'scriptblox' or 'rscripts'.")
        return
    
    script, error = fetch_script_by_id(api.lower(), script_id)
    if error:
        await interaction.followup.send(f"❌ {error}")
        return
    
    if not script:
        await interaction.followup.send("Script not found.")
        return
    
    temp_msg = await interaction.followup.send("Fetching script...")
    await display_scripts_local(interaction, temp_msg, [script], api=api.lower())

@bot.tree.command(name="executors", description="View list of available executors")
async def slash_executors(interaction: discord.Interaction):
    await interaction.response.defer()
    
    executors, error = fetch_executors()
    if error:
        await interaction.followup.send(f"❌ {error}")
        return
    
    if not executors or not isinstance(executors, list):
        await interaction.followup.send("No executors found.")
        return
    
    page = 0
    per_page = 5
    total_pages = (len(executors) - 1) // per_page + 1
    
    def create_executor_embed(page_num):
        embed = discord.Embed(
            title="🎮 Available Executors",
            description=f"List of executors from ScriptBlox (Page {page_num + 1}/{total_pages})",
            color=0x206694
        )
        start = page_num * per_page
        end = min(start + per_page, len(executors))
        
        for executor in executors[start:end]:
            name = executor.get("name", "Unknown")
            platform = executor.get("platform", "Unknown")
            exe_type = executor.get("type", "Unknown")
            patched = "❌ Patched" if executor.get("patched", False) else "✅ Active"
            version = executor.get("version", "N/A")
            
            value = f"**Platform:** {platform}\n**Type:** {exe_type}\n**Status:** {patched}\n**Version:** {version}"
            
            if executor.get("website"):
                value += f"\n[Website]({executor['website']})"
            if executor.get("discord"):
                value += f" | [Discord]({executor['discord']})"
            
            embed.add_field(name=name, value=value, inline=False)
        
        embed.set_footer(text=f"Made by AdvanceFalling Team | Powered by ScriptBlox")
        return embed
    
    embed = create_executor_embed(page)
    view = discord.ui.View(timeout=60)
    
    if total_pages > 1:
        if page > 0:
            view.add_item(discord.ui.Button(label="⏪", style=discord.ButtonStyle.primary, custom_id="first"))
            view.add_item(discord.ui.Button(label="◀️", style=discord.ButtonStyle.primary, custom_id="previous"))
        view.add_item(discord.ui.Button(label=f"Page {page + 1}/{total_pages}", style=discord.ButtonStyle.secondary, disabled=True))
        if page < total_pages - 1:
            view.add_item(discord.ui.Button(label="▶️", style=discord.ButtonStyle.primary, custom_id="next"))
            view.add_item(discord.ui.Button(label="⏩", style=discord.ButtonStyle.primary, custom_id="last"))
    
    message = await interaction.followup.send(embed=embed, view=view)
    
    while True:
        def check(i):
            return i.user == interaction.user and i.message.id == message.id
        try:
            i = await bot.wait_for("interaction", check=check, timeout=30.0)
            cid = i.data.get("custom_id")
            if cid == "previous" and page > 0:
                page -= 1
            elif cid == "next" and page < total_pages - 1:
                page += 1
            elif cid == "last":
                page = total_pages - 1
            elif cid == "first":
                page = 0
            
            embed = create_executor_embed(page)
            view = discord.ui.View(timeout=60)
            
            if total_pages > 1:
                if page > 0:
                    view.add_item(discord.ui.Button(label="⏪", style=discord.ButtonStyle.primary, custom_id="first"))
                    view.add_item(discord.ui.Button(label="◀️", style=discord.ButtonStyle.primary, custom_id="previous"))
                view.add_item(discord.ui.Button(label=f"Page {page + 1}/{total_pages}", style=discord.ButtonStyle.secondary, disabled=True))
                if page < total_pages - 1:
                    view.add_item(discord.ui.Button(label="▶️", style=discord.ButtonStyle.primary, custom_id="next"))
                    view.add_item(discord.ui.Button(label="⏩", style=discord.ButtonStyle.primary, custom_id="last"))
            
            await i.response.edit_message(embed=embed, view=view)
        except asyncio.TimeoutError:
            await message.edit(content="Interaction timed out.", view=None)
            break

def fetch_rscripts_by_username(username, page=1):
    try:
        url = f"https://rscripts.net/api/v2/scripts?page={page}&orderBy=date&sort=desc"
        headers = {"Username": username}
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()
        if "scripts" in data:
            return data["scripts"], None
        return None, f"No scripts found for '{username}'"
    except requests.RequestException as e:
        return None, f"Something went wrong: {e}"
    except Exception as e:
        return None, f"Unexpected response format: {e}"

@bot.tree.command(name="rscripts_fetch", description="Browse RScripts with advanced filters")
@app_commands.describe(
    verified_only="Show only verified scripts",
    no_key_system="Show only scripts without key systems",
    mobile_only="Show only mobile-ready scripts",
    unpatched="Show only unpatched scripts",
    order_by="Sort by field (createdAt, updatedAt, views, name)",
    sort="Sort direction (asc or desc)",
    max_results="Maximum results per page (1-20)"
)
async def slash_rscripts_fetch(
    interaction: discord.Interaction,
    verified_only: bool = None,
    no_key_system: bool = None,
    mobile_only: bool = None,
    unpatched: bool = None,
    order_by: str = None,
    sort: str = None,
    max_results: int = 20
):
    await interaction.response.defer()
    
    params = {"q": "", "page": 1, "notPaid": True}
    if verified_only is not None:
        params["verifiedOnly"] = verified_only
    if no_key_system is not None:
        params["noKeySystem"] = no_key_system
    if mobile_only is not None:
        params["mobileOnly"] = mobile_only
    if unpatched is not None:
        params["unpatched"] = unpatched
    if order_by:
        params["orderBy"] = order_by
    if sort:
        params["sort"] = sort
    
    query_string = urllib.parse.urlencode(params)
    url = f"https://rscripts.net/api/v2/scripts?{query_string}"
    
    try:
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        
        if "scripts" in data:
            scripts = data["scripts"][:max_results]
            if not scripts:
                await interaction.followup.send("No scripts found with those filters")
                return
            
            temp_msg = await interaction.followup.send("Loading scripts...")
            await display_scripts_local(interaction, temp_msg, scripts, api="rscripts")
        else:
            await interaction.followup.send("No scripts found")
    except Exception as e:
        await interaction.followup.send(f"❌ Something went wrong: {e}")

@bot.tree.command(name="rscripts_by_user", description="Find all scripts by a specific RScripts creator")
@app_commands.describe(username="The creator's username")
async def slash_rscripts_by_user(interaction: discord.Interaction, username: str):
    await interaction.response.defer()
    
    scripts, error = fetch_rscripts_by_username(username)
    if error:
        await interaction.followup.send(f"❌ {error}")
        return
    
    if not scripts:
        await interaction.followup.send(f"No scripts found for '{username}'")
        return
    
    temp_msg = await interaction.followup.send(f"Loading scripts by {username}...")
    await display_scripts_local(interaction, temp_msg, scripts, api="rscripts")

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
