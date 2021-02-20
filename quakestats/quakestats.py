import asyncio
import requests
import urllib.parse

from typing import Literal

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
    """Display Quake Champions stats in the channel."""
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

    async def red_delete_data_for_user(self, *,
        requester: Literal["discord", "owner", "user", "user_strict"],
        user_id: int,
        ):
        """
        Delete user data.
        """
        await self.config.user_from_id(user_id).clear()
        return

    @commands.group(aliases=["qc"], invoke_without_command=True)
    async def quakestats(self, ctx, _):
        """
        Share Quake Champions stats in your channel.
        """
        if ctx.invoked_subcommand is None:
            prefix = ctx.prefix
            message = (
                f"Didn’t recognise your command. "
                f"Type **{prefix}quakestats player _playername_** or "
                f"**{prefix}help quakestats** for more options.")
            await ctx.send(message)

    @quakestats.command()
    @commands.guild_only()
    async def setname(self, ctx, *, playername=None):
        """
        Register your player name with the bot.
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
        prefix = await self.bot.get_valid_prefixes()[0]
        uuid = await self.config.member(ctx.author).uuid()
        if uuid:
            return await ctx.send(f"Your registered player name is: {uuid}")
        return await ctx.send(
            f"It appears you haven’t registered your player name "
            f"yet. Type **{prefix}{self.name} setname _<name>_** "
            f"to do so.")

    @quakestats.command()
    async def player(self, ctx : commands.Context, *, playername : str = None):
        """
        Get stats for a specific player.
        """
        # try to get player name for caller
        if playername is None:
            uuid = await self.config.member(ctx.author).uuid()
            if uuid:
                playername = uuid
            else:
                return await ctx.channel.send(
                    "Please register your Quake Champion name first, provide "
                    "a player name or mention someone.")

        # try to get player name for mentioned person
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

        # try to get stats for playername
        async with ctx.channel.typing():
            await asyncio.sleep(1)
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

    @quakestats.command()
    async def match(self, ctx : commands.Context, *, player : str = None):
        """
        Get stats for your most recent match.
        """
        if player is None:
            uuid = await self.config.member(ctx.author).uuid()
            if uuid:
                player = uuid
            else:
                return await ctx.send_help()
        elif ctx.message.mentions:
            if len(ctx.message.mentions) > 1:
                return await ctx.channel.send(
                    "Please only specific one player!")
            else:
                uuid = await self.config.member(ctx.message.mentions[0]).uuid()
                if uuid:
                    player = uuid
                else:
                    return await ctx.channel.send(
                        "This user hasn’t registered a Quake Champion name.")

        async with ctx.channel.typing():
            await asyncio.sleep(1)
            pstats = self.api.get_player_stats(player)
            match = pstats["matches"].pop()
            mstats = self.api.get_match_stats(
                uid=match["id"], name=player
            )
            stats = "```\n" + self._get_table(mstats) + "\n```"
            return await ctx.channel.send(stats)

    @staticmethod
    def _get_table(stats):
        """
        Small helper method to return a pretty table for
        the statistics.
        """
        headers = [
            "Name",
            "Score",
            "Kills",
            "Deaths",
            "K:D",
            "Damage",
            "Mega",
            "Armour",
            "Pwr Up"
            ]
        cols = (
            "left",
            "center",
            "center",
            "center",
            "center",
            "center",
            "center",
            "center",
            "center"
            )

        if stats["teamScores"]:
            team0, team1 = [], []
            for p in stats["battleReportPersonalStatistics"]:
                table = "team" + str(p["teamIndex"])
                locals()[table].append([
                    p["nickname"],
                    p["score"],
                    p["kills"],
                    p["deaths"],
                    round(p["kills"]/p["deaths"], 1),
                    p["totalDamage"],
                    p["megaHealthPickups"],
                    p["heavyArmorPickups"],
                    p["powerPickups"]
                ])
            team0.sort(key=lambda x: x[1], reverse=True)
            team1.sort(key=lambda x: x[1], reverse=True)
            return "\n\n".join(
                [tabulate(team0,
                    headers=headers, tablefmt="fancy_grid", colalign=cols),
                tabulate(team1,
                    headers=headers, tablefmt="fancy_grid", colalign=cols)])

        table = []
        for p in stats["battleReportPersonalStatistics"]:
            table.append([
                p["nickname"],
                p["score"],
                p["kills"],
                p["deaths"],
                round(p["kills"]/p["deaths"], 1),
                p["totalDamage"],
                p["megaHealthPickups"],
                p["heavyArmorPickups"],
                p["powerPickups"]
            ])
        table.sort(key=lambda x: x[1], reverse=True)

        return tabulate(table, headers=headers,
            tablefmt="fancy_grid", colalign=cols)
