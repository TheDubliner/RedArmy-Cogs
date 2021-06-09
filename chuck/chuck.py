from pathlib import Path
from typing import Optional

import asyncio
import discord
import re

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

from .chucknorrisapi import (
    ChuckNorrisWrapper
)

UNIQUE_ID = 4927347237235008


class ChuckNorris(commands.Cog):
    """Spam random Chuck Norris quotes."""
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.name = "chucknorris"
        self.config = Config.get_conf(
            self,
            identifier=UNIQUE_ID,
            force_registration=True
        )
        self.api = ChuckNorrisWrapper(self)

    async def red_delete_data_for_user(self, **kwargs):
        """No data to delete."""
        return

    @commands.guild_only()
    @commands.group(aliases=["cn"], invoke_without_command=True)
    async def chucknorris(self, ctx: commands.Context, _):
        """
        Add some Chuck Norris to your channel.

        Post a random Chuck quote to the channel. You can also search by
        category, by text, and/or mention another user.
        """
        if ctx.invoked_subcommand is None:
            prefix = await ctx.bot.get_valid_prefixes()
            message = (f"Type **{prefix[0]}help {self.name}** for options.")
            await ctx.send(message)

    @chucknorris.command()
    async def random(self, ctx: commands.Context, category: str = None):
        """
        Post a random Chuck Norris quote to the channel.

        You can optionally add a category. Multiple categories can be added
        by separating them with commas (no spaces). Mention a person to have
        their name appear instead of Chuck’s.
        """
        if category:
            category = self.filter_mentions(category)
        async with ctx.channel.typing():
            await asyncio.sleep(1)
            name = None
            if ctx.message.mentions:
                name = ctx.message.mentions[0].display_name
            category = ",".join(re.split("[, ]+", category))
            quote = self.api.get_random(category=category, name=name)
            if quote:
                embed = self.build_embed(quote)
                return await ctx.channel.send(embed=embed)
            else:
                return await ctx.channel.send(embed=self.chuck_404())


    @chucknorris.command()
    async def categories(self, ctx : commands.Context):
        """
        Return a list of available categories.
        """
        async with ctx.channel.typing():
            await asyncio.sleep(0.5)
            categories = self.api.get_categories()
            return await ctx.channel.send(
                "Choose from the following categories: "
                f"{humanize_list(categories)}"
            )

    @chucknorris.command()
    async def search(self, ctx : commands.Context, *, query : str = None):
        """
        Search the Chuck Norris database for a quote.
        """
        if query:
            quote = self.api.get_random_search(query)
            if quote:
                embed = self.build_embed(quote)
                return await ctx.channel.send(embed=embed)
            else:
                return await ctx.channel.send(embed=self.chuck_404(
                    "This isn’t the Chuck Norris quote you’re looking for!"
                ))
        else:
            return await ctx.channel.send("You need to add a search term!")

    def build_embed(self, quote):
        """
        Builds an embed message based on the provided quote.
        """
        embed = discord.Embed(
            title='Chuck Norris Quotes',
            colour=discord.Colour.from_rgb(241, 90, 36),
            url=quote.get('url', None),
            description=quote.get('value'))
        embed.set_thumbnail(url=quote.get('icon_url'))
        return embed

    def chuck_404(self, message: str = "Oh noes, we didn’t find anything!"):
        """
        Builds an embed message sent when no search results are found.
        """
        return self.build_embed(
            {
                "value": message,
                "icon_url":
                "https://assets.chucknorris.host/img/avatar/chuck-norris.png",
            }
        )

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
