from pathlib import Path
from typing import Optional

import asyncio
import discord
import random
import re
import yaml

from redbot.core import (
    Config,
    commands,
    data_manager
)

UNIQUE_ID = 5140937153389558


class Stig(commands.Cog):

    DATAFILENAME = "stigquotes.yaml"
    IMGFILENAME = "stig.jpeg"

    """Spam random The Stig quotes."""
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.name = "stig"
        self.config = Config.get_conf(
            self,
            identifier=UNIQUE_ID,
            force_registration=True
        )

    async def red_delete_data_for_user(self, **kwargs):
        """No data to delete."""
        return

    @commands.guild_only()
    @commands.group(invoke_without_command=True)
    async def stig(self, ctx: commands.Context, name: str):
        """
        Add The Stig to your channel.

        Post a random Stig quote to the channel. You can also mention another
        user, optionally with their gender.
        """
        async with ctx.channel.typing():
            await asyncio.sleep(1)
            quote = self.get_random_stig_quote()
            if ctx.message.mentions:
                name = ctx.message.mentions[0].display_name
                quote = self.replace_name(quote, name)
            if quote:
                embed = self.build_embed(quote)
                return await ctx.channel.send(embed=embed)

    async def get_random_stig_quote(self):
        """
        Fills the stack with cards for the game.
        """
        sourcefile = Path.joinpath(data_manager.bundled_data_path(self),
                                   f"{self.DATAFILENAME}")
        with open(sourcefile, "r", encoding="utf8") as source:
            quotes = yaml.safe_load(source)
        return random.choice(quotes)

    @staticmethod
    def replace_pronouns(sentence, name):
        sentence = re.sub(r"\b([Hh])is\b", r"\1er", sentence)
        sentence = re.sub(r"\bhe\b", "she", sentence)
        sentence = re.sub(r"\bHe\b", "She", sentence)
        sentence = re.sub(r"\b([Hh])im\b", r"\1er", sentence)
        return sentence
    
    @staticmethod
    def replace_name(sentence, name):
        sentence = re.sub(r"\bStig\b", name, sentence)
        return sentence

    def build_embed(self, quote):
        """
        Builds an embed message based on the provided quote.
        """
        embed = discord.Embed(
            title='The Stig',
            colour=discord.Colour.from_rgb(241, 90, 36),
            url=quote.get('url', None),
            description=quote.get('value'))
        embed.set_thumbnail(url="https://github.com/TheDubliner/RedArmy-Cogs/"
                                "blob/master/stig/data/stig.jpeg?raw=true")
        return embed

    @staticmethod
    def filter_mentions(message: str) -> Optional[str]:
        """
        Filters out mentions and emotes.

        Returns `None` if string is ''.
        """
        filtered_message = re.sub(r"<((@!?\d+)|(:.+?:\d+))>", r"", message)
        if not filtered_message:
            filtered_message = None
        return filtered_message
