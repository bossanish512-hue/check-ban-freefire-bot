import discord
import os
from discord.ext import commands
from discord.ext.commands import CommandOnCooldown, BucketType
from dotenv import load_dotenv
from flask import Flask
import threading
from utils import check_ban

app = Flask(__name__)

load_dotenv()
APPLICATION_ID = os.getenv("APPLICATION_ID")
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

DEFAULT_LANG = "en"
user_languages = {}
nomBot = "None"

# 🔹 Store authorized ban channels
authorized_channels = set()

@app.route('/')
def home():
    global nomBot
    return f"Bot {nomBot} is working"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

threading.Thread(target=run_flask).start()

@bot.event
async def on_ready():
    global nomBot
    nomBot = f"{bot.user}"
    print(f"Le bot est connecté en tant que {bot.user}")

# ---------------- COMMANDS ---------------- #

@bot.command(name="guilds")
async def show_guilds(ctx):
    guild_names = [f"{i+1}. {guild.name}" for i, guild in enumerate(bot.guilds)]
    guild_list = "\n".join(guild_names)
    await ctx.send(f"Le bot est dans les guilds suivantes :\n{guild_list}")

@bot.command(name="lang")
async def change_language(ctx, lang_code: str):
    lang_code = lang_code.lower()
    if lang_code not in ["en", "fr"]:
        await ctx.send("❌ Invalid language. Available: `en`, `fr`")
        return

    user_languages[ctx.author.id] = lang_code
    message = "✅ Language set to English." if lang_code == 'en' else "✅ Langue définie sur le français."
    await ctx.send(f"{ctx.author.mention} {message}")

# 🔹 Set ban channel
@bot.command(name="setbanchannel")
@commands.has_permissions(administrator=True)
async def set_ban_channel(ctx, channel: discord.TextChannel):
    authorized_channels.add(channel.id)
    await ctx.send(f"✅ Ban check commands are now allowed in {channel.mention}")

# 🔹 Remove ban channel
@bot.command(name="removebanchannel")
@commands.has_permissions(administrator=True)
async def remove_ban_channel(ctx, channel: discord.TextChannel):
    if channel.id in authorized_channels:
        authorized_channels.remove(channel.id)
        await ctx.send(f"❌ Ban check disabled in {channel.mention}")
    else:
        await ctx.send(f"{channel.mention} was not set as ban channel.")

# 🔹 Check ban command
@bot.command(name="check")
@commands.cooldown(1, 30, BucketType.user)   # 1 use per 30s per user
async def check_ban_command(ctx, uid: str = None):
    lang = user_languages.get(ctx.author.id, "en")

    # Channel restriction
    if ctx.channel.id not in authorized_channels:
        msg = {
            "en": "This command is not available in this channel. Please use it in an authorized channel.",
            "fr": "Cette commande n'est pas disponible dans ce salon. Veuillez l'utiliser dans un salon autorisé."
        }
        await ctx.send(msg[lang])
        return

    # UID validation
    if not uid or not uid.isdigit():
        msg = {
            "en": f"{ctx.author.mention} ❌ **Invalid UID!**\n➡️ Please use: `!check 123456789`",
            "fr": f"{ctx.author.mention} ❌ **UID invalide !**\n➡️ Veuillez fournir un UID valide sous la forme : `!check 123456789`"
        }
        await ctx.send(msg[lang])
        return

    print(f"Commande fait par {ctx.author} (lang={lang})")

    async with ctx.typing():
        try:
            ban_status = await check_ban(uid)
        except Exception as e:
            await ctx.send(f"{ctx.author.mention} ⚠️ Error:\n```{str(e)}```")
            return

        if ban_status is None:
            msg = {
                "en": f"{ctx.author.mention} ❌ **Could not get information. Please try again later.**",
                "fr": f"{ctx.author.mention} ❌ **Impossible d'obtenir les informations.**\nVeuillez réessayer plus tard."
            }
            await ctx.send(msg[lang])
            return

        is_banned = int(ban_status.get("is_banned", 0))
        period = ban_status.get("period", "N/A")
        nickname = ban_status.get("nickname", "NA")
        region = ban_status.get("region", "N/A")
        id_str = f"`{uid}`"

        if isinstance(period, int):
            period_str = f"more than {period} months" if lang == "en" else f"plus de {period} mois"
        else:
            period_str = "unavailable" if lang == "en" else "indisponible"

        embed = discord.Embed(
            color=0xFF0000 if is_banned else 0x00FF00,
            timestamp=ctx.message.created_at
        )

        if is_banned:
            embed.title = "**▌ Banned Account 🛑 **" if lang == "en" else "**▌ Compte banni 🛑 **"
            embed.description = (
                f"**• {'Reason' if lang == 'en' else 'Raison'} :** "
                f"{'This account was confirmed for using cheats.' if lang == 'en' else 'Ce compte a été confirmé comme utilisant des hacks.'}\n"
                f"**• {'Suspension duration' if lang == 'en' else 'Durée de la suspension'} :** {period_str}\n"
                f"**• {'Nickname' if lang == 'en' else 'Pseudo'} :** `{nickname}`\n"
                f"**• {'Player ID' if lang == 'en' else 'ID du joueur'} :** {id_str}\n"
                f"**• {'Region' if lang == 'en' else 'Région'} :** `{region}`"
            )
            file = discord.File("assets/banned.gif", filename="banned.gif")
            embed.set_image(url="attachment://banned.gif")
        else:
            embed.title = "**▌ Clean Account ✅ **" if lang == "en" else "**▌ Compte non banni ✅ **"
            embed.description = (
                f"**• {'Status' if lang == 'en' else 'Statut'} :** "
                f"{'No sufficient evidence of cheat usage on this account.' if lang == 'en' else 'Aucune preuve suffisante pour confirmer l’utilisation de hacks sur ce compte.'}\n"
                f"**• {'Nickname' if lang == 'en' else 'Pseudo'} :** `{nickname}`\n"
                f"**• {'Player ID' if lang == 'en' else 'ID du joueur'} :** {id_str}\n"
                f"**• {'Region' if lang == 'en' else 'Région'} :** `{region}`"
            )
            file = discord.File("assets/notbanned.gif", filename="notbanned.gif")
            embed.set_image(url="attachment://notbanned.gif")

        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed.set_footer(text="DEVELOPED BY M8N•")
        await ctx.send(f"{ctx.author.mention}", embed=embed, file=file)

# 🔹 Cooldown error handler
@check_ban_command.error
async def check_ban_error(ctx, error):
    lang = user_languages.get(ctx.author.id, "en")
    if isinstance(error, CommandOnCooldown):
        seconds_left = int(error.retry_after)
        msg = {
            "en": f"⏳ Please wait {seconds_left} seconds before using this command again.",
            "fr": f"⏳ Veuillez attendre {seconds_left} secondes avant de réutiliser cette commande."
        }
        await ctx.send(msg[lang])

bot.run(TOKEN)
