from pathlib import Path

import asyncio
import discord
import logging
import random
import re

import yaml

from redbot.core import (
    checks,
    Config,
    commands,
    data_manager,
)
from redbot.core.utils.chat_formatting import (
    box,
    humanize_list,
    pagify,
)


UNIQUE_ID = 6326647334524038
log = logging.getLogger("redarmycogs.fastshow")


class FastShow(commands.Cog):
    """Spam random Fast Show quotes."""

    __version__ = "0.1.0"

    DATAFILENAME = "fastshowquotes.yaml"

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.name = "fastshow"
        self.config = Config.get_conf(
            self,
            identifier=UNIQUE_ID,
            force_registration=True
        )

        guild_defaults = {
            "channels": [],
            "toggled": False,
        }

        self.config.register_guild(**guild_defaults)

    async def red_delete_data_for_user(self, **kwargs):
        """No data to delete."""
        return

    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    @commands.group()
    async def fastshow(self, ctx):
        """Add some Fast Show to your channel."""
        if ctx.invoked_subcommand is None:
            guild_data = await self.config.guild(ctx.guild).all()
            if not guild_data["channels"]:
                channel_names = ["No channels set."]
            else:
                channel_names = []
                for channel_id in guild_data["channels"]:
                    channel_obj = self.bot.get_channel(channel_id)
                    channel_names.append(channel_obj.name)

            toggle = "Active" if guild_data["toggled"] else "Inactive"

            msg = f"[Channels]:       {humanize_list(channel_names)}\n"
            msg += f"[Toggle]:         {toggle}\n"

            for page in pagify(msg, delims=["\n"]):
                await ctx.send(box(page, lang="ini"))

    @fastshow.command()
    async def toggle(self, ctx):
        """Toggle the Fast Show on the server."""
        toggled = await self.config.guild(ctx.guild).toggled()
        await self.config.guild(ctx.guild).toggled.set(not toggled)
        await ctx.send(f"The Fast Show is now {'' if not toggled else 'in'}active.")

    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    @fastshow.group(invoke_without_command=True)
    async def channel(self, ctx):
        """Manage channels for Fast Show."""
        await ctx.send_help()
        channel_list = await self.config.guild(ctx.guild).channels()
        channel_msg = "[Active Channels]:\n"
        if not channel_list:
            channel_msg += "None."
        for chan in channel_list:
            channel_obj = self.bot.get_channel(chan)
            channel_msg += f"{channel_obj.name}\n"
        await ctx.send(box(channel_msg, lang="ini"))

    @channel.command()
    async def add(self, ctx, channel: discord.TextChannel):
        """Add a text channel for the Fast Show to listen on."""
        channel_list = await self.config.guild(ctx.guild).channels()
        if channel.id not in channel_list:
            channel_list.append(channel.id)
            await self.config.guild(ctx.guild).channels.set(channel_list)
            await ctx.send(f"The Fast Show will now work in {channel.mention}.")
        else:
            await ctx.send(f"The Fast Show is already active in {channel.mention}.")

    @channel.command()
    async def addall(self, ctx):
        """Add all valid channels for the guild that the bot can speak in."""
        bot_text_channels = [
            c for c in ctx.guild.text_channels if c.permissions_for(ctx.guild.me).send_messages is True
        ]
        channel_list = await self.config.guild(ctx.guild).channels()
        channels_appended = []
        channels_in_list = []

        for text_channel in bot_text_channels:
            if text_channel.id not in channel_list:
                channel_list.append(text_channel.id)
                channels_appended.append(text_channel.mention)
            else:
                channels_in_list.append(text_channel.mention)
                pass

        first_msg = ""
        second_msg = ""
        await self.config.guild(ctx.guild).channels.set(channel_list)
        if len(channels_appended) > 0:
            first_msg = f"{humanize_list(channels_appended)}: added to the Fast Show channels.\n"
        if len(channels_in_list) > 0:
            second_msg = f"{humanize_list(channels_in_list)}: already in the list of Fast Show channels."
        await ctx.send(f"{first_msg}{second_msg}")

    @channel.command()
    async def remove(self, ctx, channel: discord.TextChannel):
        """Remove a text channel from the Fast Show."""
        channel_list = await self.config.guild(ctx.guild).channels()
        if channel.id in channel_list:
            channel_list.remove(channel.id)
        else:
            return await ctx.send(f"{channel.mention} not in the active channel list.")
        await self.config.guild(ctx.guild).channels.set(channel_list)
        await ctx.send(f"{channel.mention} removed from the list of channels.")

    @channel.command()
    async def removeall(self, ctx):
        """Remove all channels from the list."""
        await self.config.guild(ctx.guild).channels.set([])
        await ctx.send("All channels have been removed from the list of channels.")

    @commands.Cog.listener()
    async def on_message(self, message):
        """
        Listens out for certain key words being dropped in active channels.
        """
        try:
            if isinstance(message.channel, discord.abc.PrivateChannel):
                return
            if message.author.bot:
                return
            guild_data = await self.config.guild(message.guild).all()
            if not guild_data["toggled"]:
                return
            if not guild_data["channels"]:
                return
            if re.search(r"(?i)\bblack\b", message.content):
                quote = await self.get_random_quote("black")
                async with message.channel.typing():
                    for line in quote:
                        await asyncio.sleep(3)
                        await message.channel.send(line)
        except Exception:
            log.error("Error in Fast Show loop.", exc_info=True)
    
    @fastshow.command()
    async def about(self, ctx: commands.Context):
        """
        About this cog.
        """
        await ctx.reply(
            "This cog fires random quotes into the void. Inspired by the 90s "
            "sketch show _The Fast Show_. Thanks to http://magneton.hut.fi/Q/"
            "horse for the show transcripts and aikaterna for the inspiration."
        )

    @fastshow.command()
    async def version(self, ctx: commands.Context):
        """
        Displays the current cog version.
        """
        await ctx.reply(
            f"This cog is on version {self.__version__}.",
            mention_author=False
        )

    async def get_random_quote(self, quote_type: str):
        """
        Returns a random quote for the given type.
        """
        bundledquotes = Path.joinpath(data_manager.bundled_data_path(self),
                                      self.DATAFILENAME)
        with open(bundledquotes, "r", encoding="utf8") as source:
            quotes = yaml.safe_load(source)
        return random.choice(quotes[quote_type])
