
import discord
from discord import Embed
from discord.ext import tasks

bot = discord.Bot()

class QueueMain:
    NEW_USER_CONNECTED_MESSAGE = "**New User Connected**\nYou are now talking with <@{user_id}>"
    LEFT_CONNECTED_USER_MESSAGE = "Left Connected User"
    LEFT_QUEUE_MESSAGE = "Left queue"
    JOINED_QUEUE_MESSAGE = "Waiting for another user to join"

    def __init__(self):
        self.searching = {}
        self.connected = {}
        self.connected_vc = {}

    async def add_queue(self, vc, ctx):
        self.connected_vc[str(vc.channel.id)] = {"vc": vc}
        user_id = str(ctx.author.id)
        if user_id not in self.searching and user_id not in self.connected:
            self.searching[user_id] = {"user_id": user_id, "vc": vc, "ctx": ctx}
            await self.try_connect(user_id)
        else:
            pair = list(self.searching.values())[0]
            if pair["user_id"] != user_id:
                del self.searching[pair["user_id"]]
                self.connected_vc[str(pair["vc"].channel.id)]["pair"] = str(vc.channel.id)
                self.connected_vc[str(vc.channel.id)]["pair"] = str(pair["vc"].channel.id)
                self.connected[user_id] = {"user_id": user_id, "vc": pair["vc"], "pair": pair["user_id"],
                                           "ctx": pair["ctx"]}
                self.connected[pair["user_id"]] = {"user_id": pair["user_id"], "ctx": pair["ctx"], "vc": pair["vc"],
                                                   "pair": user_id}
                await self.connected[user_id]["ctx"].send(
                    self.NEW_USER_CONNECTED_MESSAGE.format(user_id=pair["user_id"])
                )
                await self.connected[pair["user_id"]]["ctx"].send(
                    self.NEW_USER_CONNECTED_MESSAGE.format(user_id=user_id)
                )

    async def remove_connected(self, user_id):
        temp = self.connected[user_id]
        del self.connected[user_id]
        del self.connected_vc[str(temp["vc"].channel.id)]["pair"]
        temp["vc"].stop_recording()
        embed = Embed(title="Left Connected User", color=0xff0000)
        await temp["ctx"].channel.send(embed=embed)
        if temp["pair"] in self.connected:
            del self.connected_vc[str(self.connected[temp["pair"]]["vc"].channel.id)]["pair"]
            temp_pair = self.connected[temp["pair"]]
            del self.connected[temp_pair["user_id"]]
            self.searching[temp_pair["user_id"]] = {"user_id": temp_pair["user_id"], "vc": temp_pair["vc"],
                                                    "ctx": temp_pair["ctx"]}
            embed = Embed(title="Connected User left", description="Searching for a new user...", color=0xff0000)
            await temp_pair["ctx"].channel.send(embed=embed)
            await self.try_connect(temp_pair["user_id"])

    async def remove_searching(self, user_id):
        temp = self.searching[user_id]
        del self.searching[user_id]
        del self.connected_vc[str(temp["vc"].channel.id)]
        temp["vc"].stop_recording()
        embed = Embed(title="Left queue", color=0xff0000)
        await temp["ctx"].channel.send(embed=embed)
    
    async def change_owner_search(self, old_user_id, new_user_id):
        temp = self.searching[old_user_id]
        del self.searching[old_user_id]
        temp["user_id"] = new_user_id
        self.searching[new_user_id] = temp
    
    async def change_owner_connect(self, old_user_id, new_user_id):
        temp = self.connected[old_user_id]
        temp["user_id"] = new_user_id
        self.connected[temp["pair"]]["pair"] = new_user_id
        self.connected[new_user_id] = temp
        del self.connected[old_user_id]
    
    async def skip(self, user_id):
        temp = self.connected[user_id]
        del self.connected_vc[str(self.connected[temp["pair"]]["vc"].channel.id)]["pair"]
        del self.connected_vc[str(self.connected[user_id]["vc"].channel.id)]["pair"]
        temp_pair = self.connected[temp["pair"]]
        del self.connected[user_id]
        self.searching[temp_pair["user_id"]] = {"user_id": temp_pair["user_id"], "vc": temp_pair["vc"], "ctx": temp_pair["ctx"]}
        embed = Embed(title="User Skipped", color=0xff0000)
        await temp_pair["ctx"].send(embed=embed)
        self.searching[temp["user_id"]] = {"user_id": temp["user_id"], "vc": temp["vc"], "ctx": temp["ctx"]}
        embed = Embed(title="Skipped User", color=0xff0000)
        await temp["ctx"].send(embed=embed)
        await self.try_connect(temp["user_id"])
        await self.try_connect(temp_pair["user_id"])
        
        
    async def try_connect(self, user_id):
        if user_id in self.searching:
            pair = list(self.searching.values())[0]
            if pair["user_id"] != user_id:
                vc = self.searching[user_id]["vc"]
                self.connected_vc[str(pair["vc"].channel.id)]["pair"] = str(vc.channel.id)
                self.connected_vc[str(vc.channel.id)]["pair"] = str(pair["vc"].channel.id)
                self.connected[user_id] = {"user_id": user_id, "vc": self.searching[user_id]["vc"], "pair": pair["user_id"],
                                           "ctx": self.searching[user_id]["ctx"]}
                del self.searching[user_id]
                del self.searching[pair["user_id"]]
                self.connected[pair["user_id"]] = {"user_id": pair["user_id"], "ctx": pair["ctx"], "vc": pair["vc"],
                                                   "pair": user_id}
                await self.connected[user_id]["ctx"].send(
                    self.NEW_USER_CONNECTED_MESSAGE.format(user_id=pair["user_id"])
                )
                await self.connected[pair["user_id"]]["ctx"].send(
                    self.NEW_USER_CONNECTED_MESSAGE.format(user_id=user_id)
                )

        
qq = QueueMain()

@tasks.loop(minutes=10)
async def update_status():
    game = discord.Game(name=f"Watching {len(bot.guilds)} guilds!")
    await bot.change_presence(activity=game)

@bot.event
async def on_ready():
    print("Bot ready!")
    await update_status()
    
@bot.command(name="xolmegle", description="Join the Xolmegle queue and start chatting.")
async def xolmegle(ctx):
    voice = ctx.author.voice

    if not voice:
        embed = Embed(title="Error", description="You aren't in a voice channel!", color=0xff0000)
        return await ctx.respond(embed=embed, ephemeral=True)

    if str(ctx.author.id) in qq.searching or str(ctx.author.id) in qq.connected:
        embed = Embed(title="Error", description="You are already connected!", color=0xff0000)
        return await ctx.respond(embed=embed, ephemeral=True)
    if str(voice.channel.id) in qq.connected_vc:
        embed = Embed(title="Error", description="This server already has an ongoing Xolmegle connection. Please try somewhere else or join the the same channel.", color=0xff0000)
        return await ctx.respond(embed=embed, ephemeral=True)

    vc = await voice.channel.connect()
    vc.start_recording(
        discord.sinks.WaveSink(),
        once_done,
        receive_voice,
        str(vc.channel.id),
        ctx.channel
    )
    embed = Embed(title="Joined Queue", description=qq.JOINED_QUEUE_MESSAGE, color=0x00ff00)
    await ctx.respond(embed=embed)
    await qq.add_queue(vc, ctx)

@bot.command(name="skip", description="Skip to the next user in the Xolmegle call.")
async def skip(ctx):
    if not ctx.author.voice:
        embed = Embed(title="Error", description="You aren't in a voice channel!", color=0xff0000)
        return await ctx.respond(embed=embed, ephemeral=True)
    if not str(ctx.author.voice.channel.id) in qq.connected_vc:
        embed = Embed(title="Error", description="Server does not have an ongoing Xolmegle connection", color=0xff0000)
        return await ctx.respond(embed=embed, ephemeral=True)
    if (str(ctx.author.id) not in qq.searching and str(ctx.author.id) not in qq.connected):
        embed = Embed(title="Error", description=f"You are not the current owner of the Xolmegle call.", color=0xff0000)
        return await ctx.respond(embed=embed, ephemeral=True)
    if str(ctx.author.id) in qq.searching:
        embed = Embed(title="Error", description="You are currently in a queue. You can't skip", color=0xff0000)
        return await ctx.respond(embed=embed, ephemeral=True)
    await ctx.respond("Skipping User...", ephemeral=True)
    await qq.skip(str(ctx.author.id))

@bot.command(name="leave", description="Leave the current Xolmegle call.")
async def leave(ctx):
    if not ctx.author.voice:
        embed = Embed(title="Error", description="You aren't in a voice channel!", color=0xff0000)
        return await ctx.respond(embed=embed, ephemeral=True)
    if not str(ctx.author.voice.channel.id) in qq.connected_vc:
        embed = Embed(title="Error", description="Server does not have an ongoing Xolmegle connection", color=0xff0000)
        return await ctx.respond(embed=embed, ephemeral=True)
    await ctx.respond("Leaving Call...", ephemeral=True)
    if str(ctx.author.id) in qq.searching:
        await qq.remove_searching(str(ctx.author.id))
    else:
        await qq.remove_connected(str(ctx.author.id))

@bot.command(name="help", description="Display help information.")
async def help(ctx):
    embed = Embed(title="Xolmegle Bot Commands", color=0x3498db)
    embed.add_field(name=f"/xolmegle", value="Join the Xolmegle queue and start chatting.", inline=False)
    embed.add_field(name=f"/skip", value="Skip to the next user in the Xolmegle call.", inline=False)
    embed.add_field(name=f"/leave", value="Leave the current Xolmegle call.", inline=False)
    
    await ctx.respond(embed=embed)

@bot.command(name='invite', description='Get the invite link for the bot.')
async def invite(ctx):
    invite_url = f'https://discord.com/oauth2/authorize?client_id={bot.user.id}&scope=bot&permissions=551906443264'

    embed = discord.Embed(
        title='Invite Link',
        description=f'Click [here]({invite_url}) to invite the bot to your server!',
        color=discord.Color.blue()
    )

    await ctx.respond(embed=embed)
    
@bot.event
async def on_voice_state_update(member, before, after):
    bot_voice_channel = None
    for voice_channel in bot.voice_clients:
        if voice_channel.guild == member.guild:
            bot_voice_channel = voice_channel.channel
            break
    
    if before.channel and bot_voice_channel and bot_voice_channel.id == before.channel.id:
        if not member.voice:
            member_g = None
            for memberr in bot_voice_channel.members:
                if not memberr.bot:
                    member_g = str(memberr.id)
                    break
            member = str(member.id)
            if not member_g:
                if member in qq.searching:
                    await qq.remove_searching(member)
                elif member in qq.connected:
                    await qq.remove_connected(member)
            else:
                if member in qq.searching:
                    await qq.change_owner_search(member, member_g)
                elif member in qq.connected:
                    await qq.change_owner_connect(member, member_g)    

async def once_done(sink: discord.sinks, *args):
    await sink.vc.disconnect()

def receive_voice(self, data):
    if self.user_id_rec in qq.connected_vc:
        try:
            qq.connected_vc[qq.connected_vc[self.user_id_rec]["pair"]]["vc"].send_audio_packet(data.decrypted_data, encode=False)
        except Exception as e:
            pass
        
bot.run("")
