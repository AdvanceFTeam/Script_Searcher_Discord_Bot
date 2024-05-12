import discord
from discord.ext import commands
import requests
import os
import asyncio
from dotenv import load_dotenv
import validators

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

max_content_length = 200

@bot.event
async def on_ready():
    activity = discord.Game(name="!search to find scripts")
    await bot.change_presence(activity=activity)
    print("Bot is ready FUCKERS🤖")

@bot.command()
async def search(ctx, query=None, mode='free'):
    if query is None:
        initial_embed = discord.Embed(
            title="🔍 Script Search",
            description="Use the `!search` command followed by your query to search for scripts. You can also specify the search mode (default is 'free').\nModes: 'free', 'paid'\nFor example: `!search {my_script} paid`\nPlease provide a query to get started",
            color=0x3498db
        )
        await ctx.send(embed=initial_embed)
        return

    page = 1

    api_url = f"https://scriptblox.com/api/script/search?q={query}&mode={mode}&page={page}"

    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()

        if "result" in data and "scripts" in data["result"]:
            scripts = data["result"]["scripts"]

            if not scripts:
                await ctx.send("No scripts found!")
                return

            message = await ctx.send("Fetching data...") 

            await display_scripts(ctx, message, scripts, page, data["result"]["totalPages"])
        else:
            await ctx.send("No scripts found!")
    except requests.RequestException as e:
        await ctx.send(f"An error occurred: {e}")

async def display_scripts(ctx, message, scripts, page, total_pages):
    if ctx.guild:  
        for script in scripts:
            embed = create_embed(script, page, total_pages)
            if not message.embeds: 
                await message.edit(embed=embed)
            else:
                await message.edit(embed=embed, content=None)  

            await message.clear_reactions()
            await message.add_reaction("⬅️")
            await message.add_reaction("➡️")

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"]

            try:
                reaction, _ = await bot.wait_for("reaction_add", check=check, timeout=30.0)

                if str(reaction.emoji) == "⬅️" and page > 1:
                    page -= 1
                elif str(reaction.emoji) == "➡️":
                    page += 1

            except asyncio.TimeoutError:
                await ctx.send("You took too long to interact.")
                break
        else:
            await ctx.send("End of search results.")
    else:
        await ctx.send("This command can only be used in a server channel.")

def create_embed(script, page, total_pages):
    game_name = script["game"]["name"]
    title = script["title"]
    script_type = script["scriptType"]
    script_content = script["script"]
    views = script["views"]
    verified = script["verified"]
    has_key = script.get("key", False)
    created_at = script["createdAt"]
    updated_at = script["updatedAt"]
    thumbnail_url = "https://scriptblox.com" + script["game"].get("imageUrl", "")

    paid_or_free = "Free 💰" if script_type == "free" else "Paid 💲"
    views_emoji = "👀"
    verified_emoji = "✅" if verified else "❌"
    key_emoji = "🔑" if has_key else "🚫"

    truncated_script_content = (
        script_content[:max_content_length - 3] + "..."
        if len(script_content) > max_content_length
        else script_content
    )

    field_value = (
        f"Game: {game_name} {views_emoji}\n"
        f"Script Type: {paid_or_free} {verified_emoji}\n"
        f"Views: {views}\n"
        f"Verified: {verified_emoji}\n"
        f"Key Required: {key_emoji}\n"
        f"Created At: {created_at}\n"
        f"Updated At: {updated_at}\n"
        f"```lua\n{truncated_script_content}\n```"
    )

    embed = discord.Embed(
        title=title,
        description=field_value,
        color=0x27ae60
    )

    try:
        if thumbnail_url and validators.url(thumbnail_url):
            embed.set_thumbnail(url=thumbnail_url)
        else:
            embed.set_thumbnail(url="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR8U6yuDVz_6IYqS9cM2oJpGzrM9o-hZT_k21aqQclWBA&s")
    except Exception as e:
        print(f"Error setting thumbnail URL: {e}")
        embed.set_thumbnail(url="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR8U6yuDVz_6IYqS9cM2oJpGzrM9o-hZT_k21aqQclWBA&s")

    embed.set_footer(text=f" Made by AdvanceFalling Team | Page {page}/{total_pages}", icon_url="https://i.pinimg.com/564x/7e/ed/10/7eed10f9bef56d535f4e610d48d1a06b.jpg")

    return embed

bot.run(TOKEN)
