from pathlib import Path

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
from redbot.core.utils import (
    chat_formatting
)

UNIQUE_ID = 5140937153389558


class Stig(commands.Cog):

    __version__ = "0.1.0"

    DATAFILENAME = "stigquotes.yaml"
    CUSTOMFILENAME = "custom-stig-quotes.yaml"
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

    @commands.group(invoke_without_command=True)
    async def stig(self, ctx: commands.Context,
                   name: str = None, gender: str = "m"):
        """
        Add The Stig to your channel.

        Post a random Stig quote to the channel. You can also mention another
        user, optionally adding **f** to change the gender.
        """
        async with ctx.channel.typing():
            await asyncio.sleep(1)
            quote = await self.get_random_stig_quote()
            if ctx.message.mentions:
                name = ctx.message.mentions[0].display_name
            if name:
                quote = self.replace_name(quote, name)
            if gender == "f":
                quote = self.replace_pronouns(quote)
            if quote:
                embed = self.build_embed(quote)
                return await ctx.channel.send(embed=embed)

    @stig.command(name="addquote", rest_is_raw=True)
    async def add_stig_quote(self, ctx: commands.Context, *, quote: str):
        """
        Add a Stig quote to the rotation.

        Ensure your sentence includes the name _Stig_ somewhere!
        """
        if quote is not None:
            if not re.search(r"Stig", quote):
                message = ("Your message needs more Stig!")
                return await ctx.send(message)

            quote = quote.strip()

            # remove quotes but only if symmetric
            if quote.startswith('"') and quote.endswith('"'):
                quote = quote[1:-1]

            fname = data_manager.cog_data_path(self) / self.CUSTOMFILENAME
            data = [quote]
            if fname.exists():
                with open(fname, "r") as f:
                    existing_quotes = yaml.safe_load(f)
                    data = existing_quotes + data
            with open(fname, "w") as f:
                f.write(yaml.dump(data))
            return await ctx.channel.send(
                chat_formatting.info("Added your quote!")
            )
        else:
            await self.bot.say(
                chat_formatting.warning(
                    "Cannot add a quote with no text, "
                    "attachments or embed images."
                    ))

    @stig.command()
    async def version(self, ctx: commands.Context):
        """
        Display the current cog version.
        """
        await ctx.reply(
            f"This cog is on version {self.__version__}.",
            mention_author=False
        )

    async def get_random_stig_quote(self):
        """
        Fills the stack with cards for the game.
        """
        bundledquotes = Path.joinpath(data_manager.bundled_data_path(self),
                                      self.DATAFILENAME)
        customquotes = Path.joinpath(data_manager.cog_data_path(self),
                                     self.CUSTOMFILENAME)
        with open(bundledquotes, "r", encoding="utf8") as source:
            quotes = yaml.safe_load(source)
        if customquotes.exists():
            with open(customquotes, "r", encoding="utf8") as source:
                extraquotes = yaml.safe_load(source)
                quotes = quotes + extraquotes
        return random.choice(quotes)

    @staticmethod
    def replace_pronouns(sentence):
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
            colour=discord.Colour.from_rgb(0, 0, 245),
            description=quote)
        embed.set_thumbnail(url="https://github.com/TheDubliner/RedArmy-Cogs/"
                                "blob/master/stig/data/stig.jpeg?raw=true")
        return embed
