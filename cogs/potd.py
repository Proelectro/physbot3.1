from discord.ext import tasks
from random import choice
import discord
from discord.ext import commands
from discord import app_commands
from helper import worksheet, on_interaction
from datetime import datetime,time
import config
import os
Cog = commands.Cog

sheet = worksheet('POTD')
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
WEEKDAY = ['Monday', 'Tuesday', 'Wednesday',
           'Thursday', 'Friday', 'Saturday', 'Sunday']
class Menu(discord.ui.View):
    def __init__(self, to_append:list):
        super().__init__(timeout=None)
        self.to_append = to_append
    @discord.ui.button(label="Yes",style=discord.ButtonStyle.green)
    async def yes(self,interaction: discord.Interaction, button: discord.ui.Button):
        data = sheet.get()
        num = self.to_append[0] = len(data)
        sheet.append_row(self.to_append)
        await interaction.response.edit_message(content = f"Uploaded as PoTD {num}. Accepted by {interaction.user}",view=None)
        self.stop()
    @discord.ui.button(label="No",style=discord.ButtonStyle.red)
    async def no(self, interaction: discord.Interaction,button: discord.ui.Button):
        await interaction.response.edit_message(content = f"Cancelled uploading...",view=None)
        self.stop()

class Potd(Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.post.start()
    
    @tasks.loop(time=time(0,0))
    async def post(self):
        msg = await self.bot.get_channel(config.potd_planning).fetch_message(config.potd_toggle)
        if "101" in msg.content:
            return
        data = sheet.get()
        now = datetime.now()
        for num in range(len(data)-1,1,-1):
            if data[num][10] == 'pending' and data[num-1][10] != 'pending':
                data[num-1][10] = 'done'
                data[num][10] = 'live'
                data[num][1] = f'{now.day} {MONTHS[now.month-1]} {now.year}'
                data[num][2] = WEEKDAY[now.weekday()]
                post = f'**POTD {data[num][0]}**\n**{data[num][1]}**\n{data[num][6]}'
                post2 = f'POTD Creator: **{data[num][3]}**\n' if data[num][3] else ""
                post3 = f'Difficulty: {data[num][8]}\n' if data[num][8] else ""
                post4 = f'Points: {data[num][5]}\n' if data[num][5] else ""
                post6 = f'{self.bot.get_guild(config.phods).get_role(config.potd_role).mention} to submit your solution use /potd submit command in my({self.bot.user.mention}) DM.'
                msg1 = await self.bot.get_channel(config.problem_of_the_day).send(post)
                msg2 = await self.bot.get_channel(config.problem_of_the_day).send(post2+post4+post3)
                msg3 = await self.bot.get_channel(config.problem_of_the_day).send(post6)
                await msg1.publish()
                await msg2.publish()
                await msg3.publish()
                sheet.update(data)
                break
        else:
            await self.bot.get_channel(config.problem_of_the_day).send("Sorry we dont have any POTD today.")
   
    
    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or isinstance(message.author, discord.Member):
            return
        if "potd" in message.content:
            await message.channel.send("To submit your solution of a potd type /potd submit and click on the command. As shown below.",file=discord.File(os.getcwd()+r"/images/submit.png"))
            await message.channel.send("Then type number to which you are submiting and attach your solution as a single pdf. As shown below",file=discord.File(os.getcwd()+r"/images/potd.png"))
   
    group = app_commands.Group(name="potd", description="...")
    @group.command(name="fetch", description="To fetch potd by its num")
    @on_interaction
    async def fetch(self, interaction: discord.Interaction, num: int):
        data = sheet.get()
        if interaction.channel_id == config.problem_of_the_day:
            await interaction.response.send_message("Depreciated",ephemeral=True)
            return True
        else:
            if data[num][6] and (data[num][10] == 'done' or interaction.channel_id in (config.potd_planning,config.potd_botspam)):
                try:
                    data[num][3] = (await self.bot.fetch_user(data[num][11].__int__())).name
                except:
                    pass
                post = f'**POTD {data[num][0]}**\n**{data[num][1]}**\n{data[num][6]}'
                post2 = f'POTD Creator: **{data[num][3]}**\n' if data[num][3] else ""
                post3 = f'Source: ||{data[num][4]}||\n' if data[num][4] else ""
                post4 = f'Points: {data[num][5]}\n' if data[num][5] else ""
                post6 = f'Difficulty: {data[num][8]}\n' if data[num][8] else ""
                post5 = f'Category: {data[num][7]}\n' if data[num][7] else ""
                await interaction.channel.send(post)
                await interaction.channel.send(post2+post3+post4+post6+post5)
                await interaction.response.send_message(
                    "Posted succefully", ephemeral=True)
                sheet.update(data)
                return False
            else:
                await interaction.response.send_message("No such potd exist")
                return True

    @group.command(name="solution", description="To get solution of a particular potd")
    @on_interaction
    async def solution(self, interaction: discord.Interaction, num: int, link: str = ""):
        data = sheet.get()
        if link and (interaction.user.get_role(config.admin) or interaction.user.get_role(config.potd_creator)):
            data[num][9] = link
            await interaction.response.send_message("Successfully updated the solution to the sheet.")
            sheet.update(data)
            return
        else:
            if data[num][10] == 'done':
                if data[num][9]:
                    try:
                        data[num][3] = (await self.bot.fetch_user(data[num][11].__int__())).name
                    except:
                        pass
                    post = f"**POTD {num} Solution**\nPOTD Creator: **{data[num][3]}**\nSource: {data[num][4]}\n{data[num][9]}"
                    await interaction.response.send_message("Solution found",ephemeral=True)
                    await interaction.channel.send(post)
                else:
                    await interaction.response.send_message(f"No solution currently available for PoTD {num}\nAsk the POTD creator ({data[num][3]}) or message in <#604504641144619019> for more details.\n(Also try looking in <#719928959256625232> or type `in:#potd-solution potd <num>` or `in:#potd-solution potd-<num>` in discord search bar.)")
                return False
            else:
                await interaction.response.send_message("Solution not yet released.")
                return True
    @group.command(name="submit", description="Only works on DM.")
    @on_interaction
    async def submit(self, interaction: discord.Interaction, num: int, solution: discord.Attachment):
        data = sheet.get()
        error = ""
        if isinstance(interaction.user, discord.Member):
            error = "This command only works in DM"
        elif data[num][10] == "pending":
            error = "No such potd exists"
        if error:
            await interaction.response.send_message(error)
        else:
            try:
                mention = (await self.bot.fetch_user(int(data[num][11]))).mention
            except Exception as e:
                print(e)
                mention = "@"+data[num][3] 
            await self.bot.get_channel(config.potd_botspam).send(f'{mention}\nSubmission for POTD {num} by {interaction.user}\n{solution.url}')
            await interaction.response.send_message("Sucessfully submited the potd.")
            return False
    @group.command(name="upload", description="To requests your question as potd")
    @app_commands.describe(question_links = "Image attachement links for more then one link each link should be in newline.")
    @on_interaction
    async def upload(self, interaction: discord.Interaction,question_links: str,topic:str,source:str="",points:int = None,  difficulty:int=None):
        if not all("attachments" in k for k in question_links.splitlines()):
            await interaction.response.send_message("You need an attachemnt link. mobile: link on share ; pc: open image in newtab and copy url.")
            return
        data = sheet.get()
        now = datetime.now()
        channel = self.bot.get_channel(config.potd_planning)
        if interaction.channel_id in (config.potd_planning,config.potd_botspam):
            msg = "Are you sure you want to upload this can't be reversed."
            await interaction.response.send_message("Processing your querry....")
        else:
            msg = "Do you want to approve his/her requested note this can't be reversed."
            await channel.send(f"PoTD requested by user {interaction.user}.")
            await interaction.response.send_message("Your potd has been requested for approval.")
        num = len(data)
        to_append = [len(data),f'{now.day} {MONTHS[now.month-1]} {now.year}',WEEKDAY[now.weekday()],interaction.user.name,source,points,question_links,topic,difficulty,"","pending",interaction.user.id.__str__()]
        data.append(to_append)
        post = f'**POTD {data[num][0]}**\n**{data[num][1]}**\n{data[num][6]}'
        post2 = f'POTD Creator: **{data[num][3]}**\n' 
        post3 = f'Source: ||{data[num][4]}||\n' 
        post4 = f'Points: {data[num][5]}\n' 
        post5 = f'Category: {data[num][7]}\n'  
        await channel.send(post)
        await channel.send(post2+post3+post4+post5)
        await channel.send(view=Menu(to_append),content=msg)
    async def cog_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        await self.bot.get_channel(config.log2).send((await self.bot.fetch_user(config.proelectro)).mention,embed=discord.Embed(color=config.red,title=str(interaction.user),description=str(error)))

async def setup(bot):
    await bot.add_cog(Potd(bot))
