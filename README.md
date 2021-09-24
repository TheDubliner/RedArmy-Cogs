# Red Army Cogs

[![discord.py](https://img.shields.io/badge/discord-py-blue.svg)](https://github.com/Rapptz/discord.py) [![Red DiscordBot](https://img.shields.io/badge/Discord-Red%20Bot-red.svg)](https://github.com/Cog-Creators/Red-DiscordBot)

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
[Chuck Norris](../master/README.md#chuck) | Spam your channel with Chuck Norris quotes.
[Cobblers](../master/README.md#cobblers) | Play the word game Cobblers in your channel.
[Quake Stats](../master/README.md#quake-stats) | Display Quake Champion stats.
[The Stig](../master/README.md#the-stig) | Bring on the Stig.

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

## Chuck Norris

This cog pulls up random quotes from the ChuckNorris.io API and pastes them in your channel.

### Usage

**`[p]chucknorris categories`**

Returns a list of avaialble categories.

**`[p]chucknorris random`**

Spams a random Chuck Norris quote to the channel.

**`[p]chucknorris random [category1,category2]`**

Searches for a random Chuck Norris quote from the listed categories. Categories should be separated by commas, without spaces.

**`[p]chucknorris random @user`**

Returns the quote replacing Chuck Norris with _@user_’s name.

**`[p]chucknorris search [term]`**

Searches the Chuck Norris database for your search term.

## Cobblers

This cog allows you to play a classic parlour game based roughly on the board game _Balderdash_.

### Usage

**`[p]cobblers start`**

Create a new game which automatically starts after a certain amount of time. Players can join by giving a 👍.

**`[p]cobblers stop`**

Stop the currently running game in this channel without scoring.

**`[p]cobblers join`**

Join an ongoing game of _Cobblers_ after it has started.

**`[p]cobblers leave`**

Leave an ongoing game of _Cobblers_.

**`[p]cobblers leaderboard`**

Show the top ten players for the guild.

**`[p]cobblerssettings`**

Display/change the game settings (e.g. length of time for setting up, writing answers, voting etc.)

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

**`[p]quakestats lastmatch [player name]`**

Display stats from the player’s most recent match.

## The Stig

Add some random The Stig quotes to your channel.

### Usage

**`[p]stig [player name] [f]`**

Adds a random Stig quote from the Top Gear show. Optionally mention a user to have their name inserted. Adding 'f' at the end changes the pronouns.

**`[p]stig addquote [quote]`**

Add your own quote to the list. The sentence should include the word *Stig* somewhere.
# Help

Use these cogs at your own risk!

# Credit

Thanks to the [creators of Redbot](https://github.com/Cog-Creators/Red-DiscordBot/graphs/contributors) for creating the base these cogs run on. Kudos to [aikaterna-cogs](https://github.com/aikaterna/aikaterna-cogs) and [Flame-Cogs](https://github.com/Flame442/FlameCogs) for providing the inspiration.