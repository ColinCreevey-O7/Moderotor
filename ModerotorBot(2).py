import discord
from discord.ext import commands, tasks
from collections import defaultdict
import asyncio
from datetime import timedelta
from t import Token

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

yasakli_kelimeler = ["küfür1", "küfür2", "küfür3"]
kullanim_sayilari = defaultdict(lambda: defaultdict(int))
susturulanlar = {}

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    kelimeler = message.content.lower().split()
    for kelime in kelimeler:
        if kelime in yasakli_kelimeler:
            kullanim_sayilari[message.guild.id][message.author.id] += 1
            try:
                await message.author.send(f"{kelime} kelimesini kullandın. ({kullanim_sayilari[message.guild.id][message.author.id]}/5)")
            except:
                pass
            if kullanim_sayilari[message.guild.id][message.author.id] >= 5:
                member = message.guild.get_member(message.author.id)
                if member and message.guild.me.guild_permissions.moderate_members:
                    await member.timeout(duration=timedelta(minutes=15))
                    susturulanlar[member.id] = True
            break

    await bot.process_commands(message)

class ConfirmView(discord.ui.View):
    def __init__(self, user: discord.Member):
        super().__init__(timeout=None)
        self.user = user

    @discord.ui.button(label="✅ Approve", style=discord.ButtonStyle.success, custom_id="approve_button")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.ban_members:
            await interaction.response.send_message("❌ Bu işlemi yapmaya yetkin yok.", ephemeral=True)
            return
        try:
            await interaction.guild.ban(self.user, reason="Approved by button interaction")
            await interaction.response.send_message("✅ Ban başarıyla uygulandı.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ban başarısız oldu: {str(e)}", ephemeral=True)

    @discord.ui.button(label="❌ Deny", style=discord.ButtonStyle.danger, custom_id="deny_button")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.ban_members:
            await interaction.response.send_message("❌ Bu işlemi yapmaya yetkin yok.", ephemeral=True)
            return
        await interaction.response.send_message("❌ Ban reddedildi.", ephemeral=True)

@bot.command(name="ban")
async def banreq(ctx, user: discord.Member, *, reason):
    embed = discord.Embed(
        title="🚨 Ban Request",
        description="A request has been made to ban the following user.",
        color=discord.Color.from_str("#ff4d4d"),
        timestamp=discord.utils.utcnow()
    )
    embed.set_author(
        name=f"Requested by: {ctx.author}",
        icon_url=ctx.author.avatar.url if ctx.author.avatar else discord.Embed.Empty
    )
    embed.set_thumbnail(url=user.avatar.url if user.avatar else discord.Embed.Empty)
    embed.add_field(name="🎯 Target User", value=f"{user.mention} ({user.id})", inline=False)
    embed.add_field(name="📝 Reason", value=reason, inline=False)
    embed.set_footer(text="Ban request system")

    view = ConfirmView(user=user)
    await ctx.send(embed=embed, view=view)

bot.run(Token)
