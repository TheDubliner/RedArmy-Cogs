import asyncio
import csv
import random
import re
import time

from pathlib import Path
from typing import Optional

import discord

from redbot.core import (
    Config,
    commands,
    data_manager
)

from .annodominigame import (
    AnnoDominiGame,
    AnnoDominiPlayer,
    AnnoDominiCard,
    TooManyGamesException
)

UNIQUE_ID = 165778314672494


class AnnoDomini(commands.Cog):
    """Play Anno Domini with your friends!"""
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.name = "annodomini"
        self.games = []
        self.config = Config.get_conf(
            self,
            identifier=UNIQUE_ID,
            force_registration=True
        )

        self.config.register_guild(
            language="de",
            startinghand=9,
            delay=300.0,
            doMention=True
        )

        self.config.register_member(
            wins=0, games=0
        )

    @commands.guild_only()
    @commands.group(aliases=["ad"], invoke_without_command=True)
    async def annodomini(self, ctx, _):
        """
        Command group.
        """
        prefix = await ctx.bot.get_valid_prefixes()
        message = (f"Fancy a game of Anno Domini? Type "
                   f"**{prefix[0]}{self.name} newgame** or **{prefix[0]}help "
                   f"{self.name}** for more options.")
        await ctx.send(message)
    
    @annodomini.command()
    @commands.guild_only()
    async def newgame(self, ctx: commands.Context, *topics: str):
        """
        Create a new game of Anno Domini for other players to join.

        You must provide a list of topics up front.
        """
        prefix = await ctx.bot.get_valid_prefixes()
        already_in_game = self._get_user_game(ctx.author)
        if already_in_game:
            return await ctx.channel.send(  # TODO: factor out
                f"You’re already in a game (id: *{already_in_game.gid}*)\n"
                f"Type **{prefix[0]}{self.name} leave** to leave that game."
            )

        avail_topics = await self._get_topics(ctx)
        if all(topic in avail_topics for topic in topics):
            await ctx.channel.send(
                "Creating new game..."
            )
            try:
                newgame = AnnoDominiGame(self, ctx, topics)
                self.games.append(newgame)
            except TooManyGamesException:
                return await ctx.channel.send(
                    "Too many games in progress!"
                )
            player = AnnoDominiPlayer(ctx, owner=True)
            newgame.players.append(player)
            await ctx.channel.send(
                f"You created game id: *{newgame.gid}*\n"
                f"Other players can join with **{prefix[0]}{self.name} "
                f"join**.\nOnce ready, type **{prefix[0]}{self.name} start**!"
            )
        else:
            await ctx.channel.send(
                f"Topics not recognised. Type **{prefix[0]}{self.name} "
                f"topics** to display the available list."
            )
    
    @annodomini.command()
    async def topics(self, ctx: commands.Context):
        """
        Shows the available topics for the set language.
        """
        avail_topics = await self._get_topics(ctx)
        return await ctx.channel.send(
            f"Available topics: {', '.join(avail_topics)}"
        )
    
    @annodomini.command()
    async def languages(self, ctx: commands.Context):
        """
        Shows the available languages for the cog.
        """
        avail_langs = self._get_languages()
        return await ctx.channel.send(
            f"Available languages: {', '.join(avail_langs)}"
        )

    @annodomini.command()
    async def language(self, ctx: commands.Context, language: str):
        """
        Set the language.

        Defaults to de.
        This value is server specific.
        """
        if language is not None:
            await self.config.guild(ctx.guild).language.set(language)
            return await ctx.send(f"Language has been changed to {language}.")

        language = await self.config.guild(ctx.guild).language()
        await ctx.send(f"Language is currently set to {language}.")

    @annodomini.command()
    async def join(self, ctx):
        """
        Join an open game of Anno Domini.
        """
        already_in_game = self._get_user_game(ctx.author)
        if already_in_game:
            return await ctx.channel.send(
                f"{ctx.author.name}, you’re already playing a game!")
        game = self._get_running_game(ctx)
        if game:
            player = AnnoDominiPlayer(ctx)
            game.players.append(player)
            return await ctx.channel.send(
                f"{ctx.author.name} has joined game #{game.gid}.")
        await ctx.channel.send(
            f"No game found to join. Why not start your own?")

    @annodomini.command()
    async def leave(self, ctx):
        """
        Leave your current game of Anno Domini.
        """
        # TODO:
        # check if in game and leave it
        await ctx.channel.send("Command not yet implemented.")

    @annodomini.command()
    async def start(self, ctx):
        """
        Starts the game of Anno Domini with min. 2 players.
        """
        game = self._get_running_game(ctx)
        if game is None:
            return await ctx.channel.send(
                f"Set up a game first!")
        if game.players[0].member != ctx.author:
            return await ctx.channel.send(
                f"Only the game owner can start it.")
        if len(game.players) < 2:
            return await ctx.channel.send(
                f"You can’t play a game against yourself!")
        await ctx.channel.send(f"Starting game...")
        await game.setup()
        
    @annodomini.command()
    async def addbot(self, *, ctx):
        """
        Adds one/more bots to your current game.
        """
        # TODO:
        # check if in game, otherwise how to start a game
        # check if owner, otherwise warn not owner
        # check if game in progress, otherwise warn not possible
        # add * bots to current game players
        await ctx.channel.send("Command not yet implemented.")

    @annodomini.command()
    async def delbot(self, *, ctx):
        """
        Removes one/more bots from your current game.
        """
        # TODO
        await ctx.channel.send("Command not yet implemented.")

    @annodomini.command()
    async def kickplayer(self, ctx, *, name=None):
        """
        Kick a player from the game.

        Can only be performed by game owner.
        """
        # TODO
        await ctx.channel.send("Command not yet implemented.")
    
    @annodomini.command()
    async def howtoplay(self, ctx):
        """
        Instructions on how to play Anno Domini.
        """
        prefix = await ctx.bot.get_valid_prefixes()
        embed = discord.Embed(
            colour=discord.Colour(0xf5a623),
            description="In _Anno Domini_, each player receives a hand of 9 "
                        "cards featuring historical events, delivered in a "
                        "private message from the bot. A board is started in "
                        "the channel with a single card player from the deck. "
                        "On their turn, players must attempt to play a card to"
                        " the deck in the right chronological order. If they "
                        "believe there to be an error in the order, they can "
                        "challenge the player before them. If the order was "
                        "correct, the challenger receives two cards and "
                        "forfeits their turn; if however there was an error, "
                        "the challenged player receives three cards and the "
                        "challenger gets to play a card to a new board.\n\n")
        embed.set_author(name="Anno Domini – How to Play")
        embed.add_field(
            name="Setting up a Game",
            value=f"Type **{prefix[0]}annodomini newgame [topics]** to set up "
                  f"a game with the chosen topics. Players can join this "
                  f"game with **{prefix[0]}annodomini join**. The creator can "
                  f"type **{prefix[0]}annodomini start** to then launch the "
                  f"game.",
            inline=False)
        embed.add_field(
            name="Playing a Card",
            value="When it is your turn, you can do one of two things, the "
                  "first being to **play** a card to the board. To to this, "
                  "type **play** followed by the number of card you want to "
                  "play and the number of the card you want to place it "
                  "after.\n",
            inline=False)
        embed.add_field(name="Example #1", value="play 5 2", inline=True)
        embed.add_field(
            name="Explanation",
            value="Plays your card #5 after card #2 on the board.",
            inline=True)
        embed.add_field(
            name="Playing a Card to the Top",
            value="If you want to play you card to the top of the board, "
                  "you can simply type **play** and the card number.",
            inline=False)
        embed.add_field(name="Example #2", value="play 3", inline=True)
        embed.add_field(
            name="Explanation",
            value="Plays your card #3 to the beginning of the board.",
            inline=True)
        embed.add_field(
            name="Challenging the Order",
            value="If you think there is a mistake in the order of cards "
                  "laid out on the board, you can **challenge** the previous "
                  "player.",
            inline=False
        )
        embed.add_field(name="Example #3", value="challenge", inline=True)
        embed.add_field(
            name="Explanation",
            value="Challenge the order of the cards played (exc. first turn).",
            inline=True)
        embed.add_field(
            name="Winning",
            value="The winner is the first person to play their last card "
                  "**in the right order**. If a player plays their last card,"
                  " the next player automatically challenges!\n\nThis is an "
                  "entirely unofficial implementation based on the card game "
                  "by ABACUSSPIELE.",
            inline=False)

        await ctx.channel.send(embed=embed)

    @annodomini.command()
    async def about(self, ctx):
        """
        Displays information about this cog.
        """
        await ctx.send(
            "This cog is based on the Cards Against Humanity cog by aikaterna."
        )

    async def _get_topics(self, ctx) -> list:
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
        Optional[AnnoDominiGame]:
        """
        Returns a game if one is running in this channel or None.
        """
        for game in self.games:
            if game.ctx.channel == ctx.channel:
                return game
            
        return next(
            (game for game in self.games if game.ctx.channel == ctx.channel and game.live is False), None
        )

    def _get_user_game(self, user: discord.Member) -> Optional[AnnoDominiGame]:
        """
        Returns a game if player is playing in one or None.
        """
        for game in self.games:
            for player in game.players:
                if player.member.id == user.id:
                    return game
        return None
    
    def cog_unload(self):
        return [game._task.cancel() for game in self.games]


def setup(bot):
    bot.add_cog(AnnoDomini())
