import discord
from discord.ext import commands
from collections import defaultdict
from datetime import timedelta
from t import Token  # Token dosyanı kullan

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

yasakli_kelimeler = ["amk", "aq", "siktir"]
kullanim_sayilari = defaultdict(lambda: defaultdict(int))  # guild_id -> user_id -> count
uyari_sayilari = defaultdict(lambda: defaultdict(int))    # guild_id -> user_id -> warning count

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    kelimeler = message.content.lower().split()
    for kelime in kelimeler:
        if kelime in yasakli_kelimeler:
            kullanim_sayilari[message.guild.id][message.author.id] += 1
            try:
                await message.author.send(
                    f"{kelime} kelimesini kullandın. ({kullanim_sayilari[message.guild.id][message.author.id]}/5)"
                )
            except:
                pass
            if kullanim_sayilari[message.guild.id][message.author.id] >= 5:
                member = message.guild.get_member(message.author.id)
                if member and message.guild.me.guild_permissions.moderate_members:
                    try:
                        await member.timeout(timedelta(minutes=30), reason="5 defa yasaklı kelime kullanımı")
                        await message.channel.send(f"{member.mention} 5 defa yasaklı kelime kullandığı için 30 dakika susturuldu.")
                        kullanim_sayilari[message.guild.id][message.author.id] = 0
                    except Exception as e:
                        await message.channel.send(f"Susturma başarısız: {str(e)}")
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

@bot.command(name="uyar")
async def uyar(ctx, user: discord.Member, *, reason="Sebep belirtilmedi."):
    if not ctx.author.guild_permissions.kick_members:
        await ctx.send("❌ Bu komutu kullanmaya yetkin yok.")
        return
    try:
        await user.send(f"⚠️ Uyarı: {ctx.guild.name} sunucusunda uyarıldınız.\nSebep: {reason}")
        uyari_sayilari[ctx.guild.id][user.id] += 1
    except:
        await ctx.send("❌ Kullanıcıya DM gönderilemedi.")
        return
    await ctx.send(f"✅ {user.mention} başarıyla uyarıldı.")

@bot.command(name="yasaklilar")
async def yasaklilar(ctx):
    if yasakli_kelimeler:
        liste = "\n".join(f"- {kelime}" for kelime in yasakli_kelimeler)
        await ctx.send(f"🚫 Yasaklı kelimeler listesi:\n{liste}")
    else:
        await ctx.send("Şu anda tanımlı yasaklı kelime bulunmuyor.")

@bot.command(name="yasakli-ekle")
@commands.has_permissions(manage_messages=True)
async def yasakli_ekle(ctx, kelime):
    kelime = kelime.lower()
    if kelime not in yasakli_kelimeler:
        yasakli_kelimeler.append(kelime)
        await ctx.send(f"✅ `{kelime}` yasaklı kelimeler listesine eklendi.")
    else:
        await ctx.send(f"❌ `{kelime}` zaten yasaklı kelimeler listesinde.")

@bot.command(name="yasakli-sil")
@commands.has_permissions(manage_messages=True)
async def yasakli_sil(ctx, kelime):
    kelime = kelime.lower()
    if kelime in yasakli_kelimeler:
        yasakli_kelimeler.remove(kelime)
        await ctx.send(f"✅ `{kelime}` yasaklı kelimeler listesinden çıkarıldı.")
    else:
        await ctx.send(f"❌ `{kelime}` yasaklı kelimeler listesinde bulunamadı.")

@bot.command(name="rapor")
@commands.has_permissions(kick_members=True)
async def rapor(ctx, user: discord.Member):
    guild_id = ctx.guild.id
    user_id = user.id
    uyari = uyari_sayilari[guild_id][user_id]
    yasakli_kullanimi = kullanim_sayilari[guild_id][user_id]

    # Susturma kontrolü kaldırıldı çünkü eski sürümde yok
    embed = discord.Embed(
        title=f"📋 {user} Kullanıcı Raporu",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Uyarı Sayısı", value=str(uyari), inline=False)
    embed.add_field(name="Yasaklı Kelime Kullanımı", value=str(yasakli_kullanimi), inline=False)
    embed.add_field(name="Susturuldu mu?", value="Bilinmiyor (discord.py sürümü desteklemiyor)", inline=False)
    embed.set_thumbnail(url=user.avatar.url if user.avatar else discord.Embed.Empty)
    embed.set_footer(text="Moderasyon Rapor Sistemi")

    await ctx.send(embed=embed)

bot.run(Token)
