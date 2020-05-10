import requests
import urllib.parse

import discord
from tabulate import tabulate

from .quakeapi import QuakeWrapper

from redbot.core import (
    Config,
    commands,
    data_manager
)

UNIQUE_ID = 539938880633039

class QuakeStats(commands.Cog):
    """Play Anno Domini with your friends!"""
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.name = "quakestats"
        self.api = QuakeWrapper(self)
        self.config = Config.get_conf(
            self,
            identifier=UNIQUE_ID,
            force_registration=True
        )
        self.config.register_member(
            uuid=None
        )

    @commands.group(aliases=["qc"], invoke_without_command=True)
    async def quakestats(self, ctx, _):
        """
        Command group.
        """
        if ctx.invoked_subcommand is None:
            pass
        # prefix = await ctx.bot.get_valid_prefixes()
        message = f"Still very much experimental!"
        await ctx.send(message)
    
    @quakestats.command()
    @commands.guild_only()
    async def setname(self, ctx, *, playername=None):
        """
        Register your player name.
        """
        if playername is None:
            return await ctx.send(
                f"You need to tell me your Quake Champions name.")
        await self.config.member(ctx.author).uuid.set(playername)
        return await ctx.send(f"You registered your name as: {playername}")

    @quakestats.command()
    @commands.guild_only()
    async def getname(self, ctx : commands.Context):
        """
        Get your player name if registered with the bot.
        """
        prefix = await self.bot.get_valid_prefixes()
        uuid = await self.config.member(ctx.author).uuid()
        if uuid:
            return await ctx.send(f"Your registered player name is: {uuid}")
        return await ctx.send(
            f"It appears you haven’t registered your player name "
            f"yet. Type **{prefix[0]}quakestats setname <name>** "
            f"to do so.")
    
    @quakestats.command()
    async def player(self, ctx : commands.Context, *, playername : str = None):
        """
        Get stats for a specific player.
        """
        if playername is None:
            uuid = await self.config.member(ctx.author).uuid()
            if uuid:
                playername = uuid
            else:
                return
        if ctx.message.mentions:
            if len(ctx.message.mentions) > 1:
                return await ctx.channel.send(
                    "Please only specific one player!")
            else:
                uuid = await self.config.member(ctx.message.mentions[0]).uuid()
                if uuid:
                    playername = uuid
                else:
                    return await ctx.channel.send(
                        "This user hasn’t registered a Quake Champion name.")
        with ctx.channel.typing():
            stats = self.api.get_player_stats(playername)
            if stats:
            duelrank = self.api.get_player_rank(
                stats["playerRatings"]["duel"]["rating"], human=True)
            duetrank = self.api.get_player_rank(
                stats["playerRatings"]["tdm"]["rating"], human=True)
                msg = f'**Duel**:\n'
                msg += f'```\n'
                msg += f'Rating: {stats["playerRatings"]["duel"]["rating"]}' \
                       f' ± {stats["playerRatings"]["duel"]["deviation"]}\n'
                msg += f'Rank: {duelrank}\n'
                msg += f'Games: {stats["playerRatings"]["duel"]["gamesCount"]}'
                msg += f'```'
                msg += f'**2v2**:\n'
                msg += f'```'
                msg += f'Rating: {stats["playerRatings"]["tdm"]["rating"]}' \
                       f' ± {stats["playerRatings"]["tdm"]["deviation"]}\n'
                msg += f'Rank: {duetrank}\n'
                msg += f'Games: {stats["playerRatings"]["tdm"]["gamesCount"]}'
                msg += f'```'
                img = self.api.get_player_image(stats)
                img_name = stats["name"].replace(" ", "_") + ".png"
                img = discord.File(fp=img, filename=img_name)
                embed = discord.Embed(
                    title='Quake Champions Stats for ' + stats["name"],
                    colour=discord.Colour(0x9b5b16),
                    url="https://stats.quake.com/profile/" + \
                        urllib.parse.quote(stats["name"]),
                    description=msg)
                embed.set_footer(text="Quake Stats",
                    icon_url="https://stats.quake.com/fav/favicon-96x96.png")
                embed.set_image(url="attachment://" + img_name)
                return await ctx.channel.send(file=img, embed=embed)
            else:
                return await ctx.channel.send('User not found!')
