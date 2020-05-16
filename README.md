# Red Army Cogs

[![discord.py](https://img.shields.io/badge/discord-py-blue.svg)](https://github.com/Rapptz/discord.py)

Cogs for the [Red Discord Bot](https://github.com/Cog-Creators/Red-DiscordBot)

# Installation

>These are cogs for the [Red-DiscordBot V3](https://github.com/Cog-Creators/Red-DiscordBot/tree/V3/develop). You need to have a working V3 Redbot in order to install these cogs.

*[p] is your prefix.*

Make sure downloader is loaded:
`[p]load downloader`

Add the repo to your bot:
`[p]repo add redarmycogs https://github.com/TheDubliner/RedArmy-Cogs`

Install the cogs you want:
`[p]cog install redarmycogs <cog name>`

Load installed cogs:
`[p]load <cog name>`

# Cogs

Name | Description
--- | ---
[Anno Domini](../master/README.md#anno-domini) | Play Anno Domini in your channel.
[Cobblers](../master/README.md#cobblers) | Play the word game Cobblers in your channel.
[Quake Stats](../master/README.md#quake-stats) | Display Quake Champion stats.

## Anno Domini

This cog will let you set up and play a game of _Anno Domini_ in your server.

### Usage

**`[p]annodomini newgame [topics]`**

Begin a game of _Anno Domini_ for other players to join using the chosen topics.

**`[p]annodomini join`**

Join a game of _Anno Domini_ in the channel.

**`[p]annodomini start`**

Start the game of _Anno Domini_ once you have enough players.

**`[p]annodomini topics`**

Get a list of available topics to play.

**`[p]annodomini languages`**

Display a list of supported languages.

**`[p]annodomini language [language]`**

Change the language for the game.

**`[p]annodomini howtoplay`**

Shows the basic game rules.

## Cobblers

This cog allows you to play a classic parlour game based roughly on the board game _Balderdash_.

### Usage

**`[p]cobblers newgame`**

Create a new game which automatically starts after a certain amount of time. Players can join by giving a 👍.

**`[p]cobblers join`**

Join an ongoing game of _Cobblers_ after it has started.

**`[p]cobblers leave`**

Leave an ongoing game of _Cobblers_.

**`[p]cobblerssettings`**

Display/change the game settings (e.g. length of time for answers, voting etc.)

**`[p]cobblers howtoplay`**

Show the basic game rules.

## Quake Stats

This cog allows you to grab player stats for Quake Champions.

### Usage

**`[p]quakestats player [player name]`**

Display basic duel/TDM stats for the `player name` entered. You can also the
player’s Discord name, or no name for yourself, if your Quake names are
registered with the bot (see below).

**`[p]quakestats setname [player name]`**

Register your Quake player name with the bot.

**`[p]quakestats getname`**

Display the Quake player name registered with the bot.

**`[p]quakestats match [player name]`**

Display stats from the player’s most recent match.

# Help

Use these cogs at your own risk!

# Credit

Thanks to the [creators of Redbot](https://github.com/Cog-Creators/Red-DiscordBot/graphs/contributors) for creating the base these cogs run on. Kudos to [aikaterna-cogs](https://github.com/aikaterna/aikaterna-cogs) and [Flame-Cogs](https://github.com/Flame442/FlameCogs) for providing the inspiration.