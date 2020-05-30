import asyncio
import csv
import random
import re
import time

from pathlib import Path
from typing import Optional

import discord

from redbot.core import (
    checks,
    Config,
    commands,
    data_manager
)
from redbot.core.utils.chat_formatting import (
    humanize_list,
    pagify,
    box
)

from .cobblersgame import (
    CobblersGame,
    TooManyGamesException
)

UNIQUE_ID = 262597293959968


class Cobblers(commands.Cog):
    """Play Cobblers with your friends!"""
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.name = "cobblers"
        self.games = []
        self.maxplayers = 10
        self.config = Config.get_conf(
            self,
            identifier=UNIQUE_ID,
            force_registration=True
        )

        self.config.register_guild(
            language="en",
            winningscore=26,
            setuptime=120.0,
            answersdelay=300.0,
            votingdelay=120.0,
            doMention=True
        )

        self.config.register_member(
            wins=0, games=0, points=0
        )

    @commands.guild_only()
    @commands.group(aliases=["cob"], invoke_without_command=True)
    async def cobblers(self, ctx: commands.Context, _):
        """
        Command group.
        """
        if ctx.invoked_subcommand is None:
            prefix = await ctx.bot.get_valid_prefixes()
            message = (
                f"Fancy a game of Cobblers? Type **{prefix[0]}{self.name} "
                f"newgame** or **{prefix[0]}help {self.name}** for more "
                f"options.")
            await ctx.send(message)

    @commands.guild_only()
    @checks.guildowner()
    @commands.group(aliases=["cobset"])
    async def cobblerssettings(self, ctx: commands.Context):
        """Config options for Cobblers."""
        if ctx.invoked_subcommand is None:
            cfg = await self.config.guild(ctx.guild).all()
            msg = (
                'Language: {language}\n'
                'Winning score: {winningscore}\n'
                'Setup time: {setuptime}\n'
                'Time to answer: {answersdelay}\n'
                'Time to vote: {votingdelay}\n'
                'Mention players: {doMention}'
            ).format_map(cfg)
            await ctx.send(f'```py\n{msg}```')

    @cobblerssettings.command()
    async def language(self, ctx: commands.Context, value: str=None):
        """
        Set the language for the game.
        
        Defaults to en.
        This value is server specific.
        """
        if value is None:
            lang = await self.config.guild(ctx.guild).language()
            await ctx.send(f'The language is currently set to {lang}.')
        else:
            langs = self._get_languages()
            if value in langs:
                await self.config.guild(ctx.guild).language.set(value)
                await ctx.send(f'You have now changed the language to '
                               f'{value}.')
            else:
                await ctx.send(f'Language not recognised. Please choose '
                               f'from: {humanize_list(langs)}')

    @cobblerssettings.command()
    async def winscore(self, ctx: commands.Context, value: int=None):
        """
        Set the winning score for the game.
        
        Defaults to 26.
        This value is server specific.
        """
        if value is None:
            score = await self.config.guild(ctx.guild).winningscore()
            await ctx.send(f'The current score required to win is {score}.')
        else:
            await self.config.guild(ctx.guild).winningscore.set(value)
            await ctx.send(f'You have now changed the score required '
                           f'to win to {value}.')

    @cobblerssettings.command()
    async def setuptime(self, ctx: commands.Context, value: float=None):
        """
        Set the time between setting up and starting a game.
        
        Defaults to 2 minutes.
        This value is server specific.
        """
        if value is None:
            time = await self.config.guild(ctx.guild).setuptime()
            await ctx.send(f'The current setup time is {time} seconds.')
        else:
            await self.config.guild(ctx.guild).setuptime.set(value)
            await ctx.send(f'You have now changed the setup time to {value} '
                           f'seconds.')

    @cobblerssettings.command()
    async def answertime(self, ctx: commands.Context, value: float=None):
        """
        Set the time allowed for players to submit answers.
        
        Defaults to 5 minutes.
        This value is server specific.
        """
        if value is None:
            time = await self.config.guild(ctx.guild).answersdelay()
            await ctx.send(f'The current time allowed to submit answers is '
                           f'{time} seconds.')
        else:
            await self.config.guild(ctx.guild).answersdelay.set(value)
            await ctx.send(f'You have now changed the time allowed for '
                           f'submitting answers to {value} seconds.')

    @cobblerssettings.command()
    async def votetime(self, ctx: commands.Context, value: float=None):
        """
        Set the time allowed for players to vote on the answers.
        
        Defaults to 2 minutes.
        This value is server specific.
        """
        if value is None:
            time = await self.config.guild(ctx.guild).votingdelay()
            await ctx.send(f'The current time allowed for players to vote '
                           f'is {time} seconds.')
        else:
            await self.config.guild(ctx.guild).votingdelay.set(value)
            await ctx.send(f'You have now changed the voting time to '
                           f'{value} seconds.')

    @cobblerssettings.command()
    async def mentions(self, ctx: commands.Context, value: bool=None):
        """
        Set whether players should be mentioned.

        Defaults to True.
        This value is server specific.
        """
        if value is None:
            v = await self.config.guild(ctx.guild).doMention()
            if v:
                await ctx.send('Players will be mentioned by the game.')
            else:
                await ctx.send('Players will not be mentioned by the game.')
        else:
            await self.config.guild(ctx.guild).doMention.set(value)
            if value:
                await ctx.send('Players will now be mentioned by the game.')
            else:
                await ctx.send('Players will no longer be mentioned by the '
                               'game.')

    @cobblers.command()
    @commands.guild_only()
    async def newgame(self, ctx: commands.Context, *topics: str):
        """
        Create a new game of Cobblers.
        """
        prefix = await ctx.bot.get_valid_prefixes()
        already_in_game = self._get_user_game(ctx.author)
        if already_in_game:
            return await ctx.channel.send(  # TODO: factor out
                f"You’re already in a game (id: *{already_in_game.gid}*)\n"
                f"Type **{prefix[0]}{self.name} leave** to leave that game."
            )

        countdown = await self.config.guild(ctx.guild).setuptime()
        await ctx.channel.send(
            f"{ctx.author.mention} is starting a new game of Cobblers!"
            )
        try:
            newgame = CobblersGame(self, ctx)
            newgame.players.append(ctx.author)
            self.games.append(newgame)
        except TooManyGamesException:
            return await ctx.channel.send(
                "Too many games in progress!"
            )

        message = await ctx.message.channel.send(
            f"Join the game now by giving your 👍\n"
            f"The game will start in {int(countdown)} seconds!")
        await message.add_reaction("👍")
        await asyncio.sleep(countdown)
        message = await ctx.channel.fetch_message(message.id)
        for reaction in message.reactions:
            if str(reaction) == "👍":
                async for user in reaction.users():
                    if user not in newgame.players and user != self.bot.user \
                        and len(newgame.players) < self.maxplayers:
                        newgame.players.append(user)

        player_names = [player.display_name for player in newgame.players]
        await ctx.channel.send(
            f"Starting game with {humanize_list(player_names)}"
        )
        await newgame.setup()

    @commands.guild_only()
    @checks.guildowner()
    @cobblers.command()
    async def stop(self, ctx: commands.Context):
        """
        Stop the game of Cobblers in this channel.
        """
        wasGame = False
        for game in [g for g in self.games if g.ctx.channel == ctx.channel]:
            game._task.cancel()
            wasGame = True
        if wasGame:  # prevents multiple messages if more than one game exists
            await ctx.send('The game was stopped successfully.')
        else:
            await ctx.send('There is currently no game in this channel.')

    @cobblers.command()
    @commands.guild_only()
    async def join(self, ctx: commands.Context):
        """
        Join a running game of Cobblers.
        """
        # first check if user is already in a game
        already_in_game = self._get_user_game(ctx.author)
        if already_in_game:
            await ctx.channel.send(
                f"{ctx.author.name}, you’re already playing a game!")
            return

        # next check if there’s a game to join and space to play
        game = self._get_running_game(ctx)
        if game:
            if len(game.players) < self.maxplayers:
                game.players.append(ctx.author)
                return await ctx.channel.send(
                    f"{ctx.author.name} has joined game #{game.gid}.")
            else:
                return await ctx.channel.send(
                    f"This game is full. Wait for the next one!"
                )

        # finally suggest they create their own
        await ctx.channel.send(f"No game found to join. Why not start your own?")

    @cobblers.command()
    async def leave(self, ctx: commands.Context):
        """
        Leave your current game of Cobblers.
        """
        playing_in_game = self._get_user_game(ctx.author)
        if playing_in_game:
            try:
                playing_in_game.players.remove(ctx.author)
                return f"{ctx.author.name} has been removed from the game."
            except ValueError:
                return f"Oops! Couldn’t remove {ctx.author.name} from the game."
        return await ctx.channel.send("You don’t seem to be in a game!")
    
    @cobblers.command(autohelp=False)
    async def leaderboard(self, ctx: commands.Context):
        """Leaderboard for _Cobblers_.
        Defaults to the top 10 of this server, sorted by total wins.
        """
        guild = ctx.guild
        data = await self.config.all_members(guild)
        data = {guild.get_member(u): d for u, d in data.items()}
        data.pop(None, None)  # remove members who aren’t in the guild
        await self.send_leaderboard(ctx, data, "wins", 10)

    async def send_leaderboard(self,
        ctx: commands.Context, data: dict, key: str, top: int):
        """
        Send the leaderboard from the given data.

        Parameters
        ----------
        ctx : `commands.Context`
            Context to send the leaderboard to.
        data : `dict`
            Data for the leaderboard. Must map `discord.Member` ->
            `dict`.
        key : `str`
            Field to sort the data by.
        top : `int`
            Number of members to display on the leaderboard.

        Returns
        -------
        `list` of `discord.Message`
            Sent leaderboard messages.
        """
        if not data:
            await ctx.send("There are no scores on record!")
            return
        leaderboard = self._get_leaderboard(data, key, top)
        ret = []
        for page in pagify(leaderboard, shorten_by=10):
            ret.append(await ctx.send(box(page, lang="py")))
        return ret

    @staticmethod
    def _get_leaderboard(data: dict, key: str, top: int):
        # Mix in average score
        for member, stats in data.items():
            if stats["games"] != 0:
                stats["average_score"] = stats["points"] / stats["games"]
            else:
                stats["average_score"] = 0.0
        # Sort by reverse order of priority
        priority = ["average_score", "points", "wins", "games"]
        try:
            priority.remove(key)
        except ValueError:
            raise ValueError(f"{key} is not a valid key.")
        # Put key last in reverse priority
        priority.append(key)
        items = data.items()
        for key in priority:
            items = sorted(items, key=lambda t: t[1][key], reverse=True)
        max_name_len = max(map(lambda m: len(str(m)), data.keys()))
        # Headers
        headers = (
            "Rank",
            "Member" + " " * (max_name_len - 6),
            "Wins",
            "Games Played",
            "Total Score",
            "Average Score",
        )
        lines = [" | ".join(headers), " | ".join(("-" * len(h) for h in headers))]
        # Header underlines
        for rank, tup in enumerate(items, 1):
            member, m_data = tup
            # Align fields to header width
            fields = tuple(
                map(
                    str,
                    (
                        rank,
                        member,
                        m_data["wins"],
                        m_data["games"],
                        m_data["points"],
                        round(m_data["average_score"], 2),
                    ),
                )
            )
            padding = [" " * (len(h) - len(f)) for h, f in zip(headers, fields)]
            fields = tuple(f + padding[i] for i, f in enumerate(fields))
            lines.append(" | ".join(fields).format(member=member, **m_data))
            if rank == top:
                break
        return "\n".join(lines)
    
    @cobblers.command()
    async def howtoplay(self, ctx: commands.Context):
        """
        Instructions on how to play the game.
        """
        prefix = await ctx.bot.get_valid_prefixes()
        embed = discord.Embed(
            colour=discord.Colour(0xf5a623),
            description="In _Cobblers_, players must try to use their skills "
                        "of persuasion to outwit their opponents. Each round "
                        "they are presented with a question to which they "
                        "must all provide answers – and then see if they can "
                        "identify the truth from the fakes! Earn points for "
                        "avoiding the phoneys… and bonus points for tricking "
                        "your friends!\n\nCategories include: rare words "
                        "(write the definition), film titles (write the plot)"
                        ", film synopses (make up the title), laws (complete "
                        "the law) and dates (make up an event).")
        embed.set_author(name="Anno Domini – How to Play")
        embed.add_field(
            name="Setting up a Game",
            value=f"Type **{prefix[0]}cobblers newgame** to set up a game."
                  f"Players can join the game before it starts be clicking "
                  f"the thumbs up. The game will that start automatically "
                  f"after a certain time.",
            inline=False)
        embed.add_field(
            name="Answering",
            value="Each round, players will be given the task of inventing "
                  "an answer to certain question. These should be sent to "
                  "the bot via private message. Once all answers are in, "
                  "or the timer runs out, the submitted answers are put to "
                  "the vote.",
            inline=False)
        embed.add_field(
            name="Voting",
            value="The bot will update the board with the list of answers "
                  "from all the players, plus the real answer. Players have "
                  "a certain length of time to cast their votes by clicking "
                  "on the reactions. Votes for their own answers do not count"
                  " and only one vote is counted.",
            inline=False)
        embed.add_field(
            name="Scoring",
            value="Players earn **2 points** for identifying the correct "
                  "answer and **1 point** for every person who votes "
                  "for theirs.",
            inline=False)
        embed.add_field(
            name="Winning",
            value="The winner is the person with the most points after "
                  "reaching the winning threshold!\n\nThis game is inspired "
                  "by the classic parlour game and the board game "
                  "_Balderdash_.",
            inline=False)

        await ctx.channel.send(embed=embed)

    @cobblers.command()
    async def about(self, ctx: commands.Context):
        """
        Displays information about this cog.
        """
        await ctx.send(
            "This cog is based on the board game Balderdash."
        )

    async def _get_topics(self, ctx: commands.Context) -> list:
        """
        Returns a list of topics available for the cog language.
        """
        language = await self.config.guild(ctx.guild).language()
        sourcefile = Path.joinpath(data_manager.bundled_data_path(self),
                                   f"data-{language}.csv")
        with open(sourcefile, "r", encoding="utf8") as source:  # TODO: detect encoding
            reader = csv.DictReader(source, delimiter=",")
            return {row["topic"] for row in reader}
    
    def _get_languages(self) -> list:
        """
        Returns a list of languages available for the cog.
        """
        folder = data_manager.bundled_data_path(self)
        return [
            re.sub(r"data-(\w+)\.csv", r"\1", p.name)
            for p in folder.iterdir()
            if p.is_file() and p.name.endswith("csv")]

    def _get_running_game(self, ctx: commands.Context) -> \
        Optional[CobblersGame]:
        """
        Returns a game if one is running in this channel or None.
        """
        for game in self.games:
            if game.ctx.channel == ctx.channel:
                return game
            
        return next(
            (game for game in self.games if game.ctx.channel == ctx.channel and game.live is False), None
        )

    def _get_user_game(self, user: discord.Member) -> Optional[CobblersGame]:
        """
        Returns a game if player is playing in one or None.
        """
        for game in self.games:
            for player in game.players:
                if player.id == user.id:
                    return game
        return None
    
    def cog_unload(self):
        return [game._task.cancel() for game in self.games]


def setup(bot):
    bot.add_cog(Cobblers())
