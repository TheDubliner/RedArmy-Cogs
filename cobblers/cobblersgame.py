import asyncio
import csv
import logging
import random
import re
import time
import traceback

from collections import Counter
from pathlib import Path

import discord
from discord.abc import PrivateChannel

from redbot.core.utils.chat_formatting import pagify, humanize_list
from redbot.core.utils.menus import start_adding_reactions
from redbot.core import (
    data_manager
)

CATEGORIES = ["Films", "Words", "Dates", "Laws", "Film Synopses"]
EXPLANATIONS = {
    "Films": "Send me your synopsis of this film per private message!",
    "Words": "Send me your definition of this word per private message!",
    "Film Synopses": "Send me your title for this film per private message (include the year in brackets)!",
    "Dates": "Send me what happened on this day per private message!",
    "Laws": "Send me the end of this law per private message!"
}

class TooManyGamesException(Exception):
    """Error thrown when there are too many games in progress."""
    pass


class CobblersGame:
    """
    Class to run a game of Cobblers.

    Attributes
    ----------
    ctx : `commands.Context`
        Context object from which this session is run.
    cog : `commands.Cog`
        A reference to the parent cog.
    gid : `int`
        A unique game id to enable multiple concurrent games.
    starttime : `int`
        When game was started (currently unused)
    players : `list` of `AnnoDominiPlayer`
        Players in the game.
    questions : `list` of `dict`
        Questions with topic, name and solution.
    question : `dict`
        The current question
    answers : `list` of `tuple`
        Answers submitted for the current round.
    board_embed : `discord.Message`
        Reference the message where the current board is embed.
    round_no : `int`
        The current round of the game.
    scores : `Counter`
        A tally of the players’ scores.
    log : `logging.Logger`
        Logging link.
    msg : `str`
        Current message ready to be sent. (unused)
    live : `bool`
        Probably unnecessary game state.
    """
    def __init__(self, parent, ctx):
        self.cog = parent
        self.ctx = ctx
        self.gid = self._generate_id()
        self.starttime = int(time.time())
        self.players = []
        self.questions = []
        self.question = None  # current question
        self.answers = []
        self.board_embed = None
        self.round_no = 0
        self.scores = Counter()
        self.log = logging.getLogger('red.redarmycogs.cobblers')
        self.msg = ''
        self._last_play = int(time.time())  # TODO: integrate this?
        self._task = None

    def _generate_id(self):
        """
        Generates an id for the game for concurrent games.
        """
        if len(self.cog.games) >= 9000:
            raise TooManyGamesException("Games full!")
        games = [game.gid for game in self.cog.games]
        while True:
            gid = random.randint(1000, 9999)
            if gid not in games:
                return gid

    async def send_error(self):
        """
        Sends a message to the channel after an error.
        """
        await self.ctx.send(
            'A fatal error has occurred, shutting down.'
        )

    async def send_timeout(self):
        """
        Cleanup code when a user times out.
        """
        # TODO remove the player from the game
        await self.ctx.send(
            'You did not respond in time. Shutting down.'
        )

    def error_callback(self, fut):
        """
        Checks for errors.
        """
        try:
            fut.result()
        except asyncio.CancelledError:
            pass
        except asyncio.TimeoutError:
            asyncio.create_task(self.send_timeout())
        except Exception as exc:
            asyncio.create_task(self.send_error())
            msg = 'Error in Cobblers.'
            self.log.exception(msg)
            stack = ''.join(traceback.TracebackException.from_exception(exc).format())
            self.log.exception(stack)
        try:
            self.cog.games.remove(self)
        except ValueError:
            pass

    async def get_players(self):
        countdown = await self.cog.config.guild(self.ctx.guild).setuptime()
        message = await self.ctx.message.channel.send(
            f"Join the game now by giving your 👍\n"
            f"The game will start in {int(countdown)} seconds!")
        await message.add_reaction("👍")
        await asyncio.sleep(countdown)
        message = await self.ctx.channel.fetch_message(message.id)
        for reaction in message.reactions:
            if str(reaction) == "👍":
                async for user in reaction.users():
                    if user not in self.players and user != self.cog.bot.user \
                        and len(self.players) < self.cog.maxplayers:
                        self.players.append(user)

        if await self.cog.config.guild(self.ctx.guild).mentions():
            player_names = [player.mention for player in self.players]
        else:
            player_names = [player.display_name for player in self.players]
        await self.ctx.channel.send(
            f"Starting game with {humanize_list(player_names)}"
        )

    async def setup(self):
        """
        Initialises the game.
        """
        self._task = asyncio.create_task(self.get_players())
        await self._task
        if not self.enough_players():
            self.ctx.send("Not enough players to start. Quitting!")
            self.cog.games.remove(self)
            return
        await self.get_questions()
        self.live = True
        self._task = asyncio.create_task(self.run())
        self._task.add_done_callback(self.error_callback)

    async def check_winner(self):
        """
        Checks if someone has won.
        """
        win_score = await self.cog.config.guild(self.ctx.guild).winningscore()
        if any(score >= win_score for score in self.scores.values()):
            return True
        return False

    async def new_round(self):
        """
        Sets up a new round.
        """
        self.round_no += 1
        self.answers = []
        self.board_embed = None

    async def run(self):
        """
        Runs the main game loop.
        """
        while self.live:
            if not self.enough_players():
                await self.ctx.send(
                    "Not enough players to continue. Quitting!")
                self.cog.games.remove(self)
                return
            ans_delay = \
                await self.cog.config.guild(self.ctx.guild).answersdelay()
            vote_delay = \
                await self.cog.config.guild(self.ctx.guild).votingdelay()
            if await self.check_winner():
                break
            await self.new_round()
            try:
                self.question = self.questions.pop()
            except IndexError:
                # add another 20 questions if 100 somehow weren’t enough
                self.questions = self.get_questions(20)
                self.question = self.questions.pop()

            embed = discord.Embed(
                colour=discord.Colour.dark_blue(),
                description=f"{self.question['topic']}: "
                            f"{self.question['name']}\n"
                            f"{EXPLANATIONS[self.question['topic']]}")
            embed.set_author(
                name=f"Cobblers: Round #{self.round_no}")
            self.board_embed = await self.ctx.send(
                embed=embed)
            for player in self.players:
                await player.send(
                    f"{self.question['topic']}: {self.question['name']}\n"
                    f"Type your answer to me below:"
                    )
            # identify the author of the correct answer as `False`
            self.answers.append((False, self.question['solution']))

            # wait for player answers, shuffle them and update the board
            await self.wait_for_answers(ans_delay)
            random.shuffle(self.answers)
            embed = await self._build_board_embed(reveal=False)
            await self.updateboard(embed)

            # wait for players to vote, then display scores
            votes = await self.wait_for_votes(vote_delay)
            embed = await self._build_board_embed(reveal=True)
            await self.updateboard(embed)
            if votes:
                self.scores += votes
            if self.scores:
                msg = "**Scores after that round:**\n"
                for score in self.scores.most_common():
                    msg += (f"{score[0].name}: {score[1]} "
                            f"{'(+'+f'{votes[score[0]]}'})\n")
            else:
                msg = "Nobody scored anything that round!"
            await self.ctx.channel.send(msg)

        winners = self.get_winners()
        if len(winners) == 1:
            msg = (f"**{winners[0].name} is the winner!**\n")
        else:
            msg = (f"**{humanize_list([winner.name for winner in winners])} "
                   "are the winners!**\n")
        msg += "__Final scores:__\n"
        for score in votes.most_common():
            msg += f"{score[0].name}: {score[1]}\n"
        await self.ctx.channel.send(msg)

        await self.update_scores()
    
    def get_winners(self):
        """
        Return the player(s) with the top score.

        Returns
        -------
        `list`
            List of players with the top score.
        """
        topscore = 0
        topscorers = []
        for name, score in self.scores.most_common():
            if score == topscore:
                topscorers.append(name)
            if score > topscore:
                topscorers.append(name)
                topscore = score
            if score < topscore:
                break
        return topscorers

    async def wait_for_votes(self, delay: float):
        """
        Wait for votes from players.

        Parameters
        ----------
        delay : `float`
            How long users have to respond (in seconds).

        Returns
        -------
        votes : `Counter`
            A dictionary of the points scored this round.
        """
        symbols = [
            "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"
        ]

        # add reactions to the board for players to click
        for idx in range(len(self.answers)):
            await self.board_embed.add_reaction(symbols[idx])
        await asyncio.sleep(delay)

        votes = Counter()
        voted = []  # only allow players to vote once

        # refresh the message to get reactions after the voting has ended
        message = await self.ctx.channel.fetch_message(self.board_embed.id)
        for reaction in message.reactions:
            if str(reaction.emoji) in symbols:
                async for voter in reaction.users():
                    if voter not in self.players or voter == self.ctx.bot \
                        or voter in voted:
                        continue  # TODO: potentially allow foreign votes?
                    votee = self.answers[symbols.index(str(reaction))][0]
                    if votee is False:
                        votes[voter] += 2  # 2 pts for correct answer
                        voted.append(voter)
                        continue
                    if voter != votee:
                        votes[votee] += 1  # 1 pt for being voted for
                        voted.append(voter)
        return votes

    async def _answer_helper(self, player: discord.User, delay: float):
        """
        Helper method to return player answers
        """
        try:
            answer = await self.ctx.bot.wait_for(
                "message", check=lambda m: (
                    isinstance(m.channel, PrivateChannel) and
                    m.author.id == player.id
                ), timeout=delay
            )
            return answer
        except asyncio.TimeoutError:
            raise asyncio.TimeoutError

    async def wait_for_answers(self, delay: float):
        """Wait for answers from players.

        Parameters
        ----------
        delay : float
            How long users have to respond (in seconds).

        Returns
        -------
        bool
            `True` if the session wasn’t interrupted.
        """
        answers = await asyncio.gather(
            *[self._answer_helper(player, delay) for player in self.players],
            return_exceptions=True
        )
        for answer in answers:
            if type(answer) is asyncio.TimeoutError:
                continue
            self.answers.append((
                answer.author,
                answer.content[:1000]
                if len(answer.content) > 1000
                else answer.content
                ))
        return True

    async def send(self):
        """Safely send messages."""
        for page in pagify(self.msg):
            await self.ctx.send(page)
        self.msg = ''

    def enough_players(self) -> bool:
        """
        Check if there are enough players to continue.
        """
        if len(self.players) >= self.cog.minplayers:
            return True
        return False

    async def get_questions(self, questions: int = 100) -> list:
        """
        Fills the list with questions for the game.

        Notes
        -----
        Questions consist of a `topic`, `name` and `solution`.

        Films can be added forwards and backwards (i.e. from the title,
        write a synopsis; from the synopsis, write a film title)
        """
        language = await self.cog.config.guild(self.ctx.guild).language()
        sourcefile = Path.joinpath(data_manager.bundled_data_path(self),
                                   f"data-{language}.csv")
        with open(sourcefile, "r", encoding="utf8") as source:  # TODO: detect encoding
            reader = csv.DictReader(source, delimiter=",")
            buckets = {category: [] for category in CATEGORIES}
            for row in reader:
                # randomly add half films backwards
                if row['topic'] == 'Films' and random.choice([True, False]):
                    buckets['Film Synopses'].append(
                        {
                            'topic': 'Film Synopses',
                            'name': row['solution'],
                            'solution': row['name']
                        }
                    )
                    continue
                buckets[row['topic']].append(row)
        no_of_qs_per_cat = round(questions / len(buckets))
        for bucket in buckets.values():
            random.shuffle(bucket)
            self.questions.extend(bucket[:no_of_qs_per_cat])
        del buckets
        random.shuffle(self.questions)

    async def update_scores(self):
        """
        Update the scores at the end of the game.
        """
        winners = self.get_winners()
        for player, score in self.scores.items():
            stats = await self.cog.config.member(player).all()
            stats["games"] += 1
            stats["points"] += score
            if player in winners:
                stats["wins"] += 1
            await self.cog.config.member(player).set(stats)

    async def updateboard(self, board_embed):
        await self.board_embed.edit(embed=board_embed)
        return

    async def _build_board_embed(self, reveal: bool = False):
        colour = discord.Colour.dark_blue()
        if reveal:
            colour = discord.Colour.green()
        board_embed = discord.Embed(
            color=colour,
            description=f"{self.question['topic']}: {self.question['name']}")
        board_embed.set_author(
            name=f"Cobblers: Round #{self.round_no}")
        if not reveal:
            for idx, answer in enumerate(self.answers, 1):
                board_embed.add_field(
                    name=f"Answer #{idx}", value=f"{answer[1]}", inline=False
                )
            board_embed.set_footer(
                text=f"Vote on which answer you think is the right one!"
            )
        else:
            for idx, answer in enumerate(self.answers, 1):
                if answer[0] is False:
                    board_embed.add_field(
                        name=f"Answer #{idx}", value=f"**{answer[1]}** ✅",
                        inline=False
                    )
                else:
                    board_embed.add_field(
                        name=f"Answer #{idx}", value=f"{answer[1]} ❌\n" \
                        f"Posted by: {answer[0].name}", inline=False
                    )

            board_embed.set_footer(
                text="Here’s what really happened!"
            )
        return board_embed
