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

from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import start_adding_reactions
from redbot.core import (
    data_manager
)

EXPLANATIONS = {
    "Films": "Send me your synopsis of this film per private message!",
    "Words": "Send me your definition of this word per private message!",
    "Film Synopses": "Send me your title for this film per private message!",
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
        self.question = None  # correct question
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
        if len(self.cog.games) == 9000:
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

    async def setup(self):
        """
        Initialises the game.
        """
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
                self.ctx.send("No more questions!")
                break

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

        # TODO: no support for tied winners
        msg = (f"**{self.scores.most_common(1)[0].name} is the winner!**\n" 
               f"Final scores:\n")
        for score in votes.most_common():
            msg += f"{score[0].name}: {score[1]}\n"
        await self.ctx.channel.send(msg)

        await self.update_scores()

    async def wait_for_votes(self, delay: float):
        """
        Wait for votes from players.

        Parameters
        ----------
        delay : float
            How long users have to respond (in seconds).

        Returns
        -------
        votes : dict
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
                    self.log.warning(f"voter: {voter}")
                    if voter not in self.players or voter == self.ctx.bot \
                        or voter in voted:
                        self.log.warning("voter blocked")
                        continue  # TODO: potentially allow foreign votes?
                    votee = self.answers[symbols.index(str(reaction))][0]
                    self.log.warning(f"votee: {votee}")
                    if votee is False:
                        self.log.warning(f"{voter} voted for False")
                        votes[voter] += 2  # 2 pts for correct answer
                        voted.append(voter)
                        continue
                    if voter != votee:
                        self.log.warning(f"{voter} voted for {votee}")
                        votes[votee] += 1  # 1 pt for being voted for
                        voted.append(voter)
        return votes

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
            *[self.ctx.bot.wait_for(
                "message", check=lambda m: (
                    isinstance(m.channel, PrivateChannel) and
                    m.author.id == player.id
                ), timeout=delay
            ) for player in self.players],
            return_exceptions=True
        )
        for answer in answers:
            if answer is asyncio.TimeoutError:
                continue
            self.answers.append((answer.author, answer.content))
        return True

    async def send(self):
        """Safely send messages."""
        for page in pagify(self.msg):
            await self.ctx.send(page)
        self.msg = ''

    async def get_questions(self) -> list:
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
            for row in reader:
                # randomly add half films backwards
                if row['topic'] == 'Films' and random.choice([True, False]):
                    self.questions.append(
                        {
                            'topic': 'Film Synopses',
                            'name': row['solution'],
                            'solution': row['name']
                        }
                    )
                    continue
                self.questions.append(row)
        random.shuffle(self.questions)
    
    async def update_scores(self):
        """
        Update the scores at the end of the game.
        """
        for player in self.scores:
            stats = self.cog.config.member(player.member).all()
            stats["games"] += 1
            # FIXME: event of a tie
            if player == self.scores.most_common(1)[0][0]:
                stats["wins"] += 1
            self.cog.config.member(player.member).set(stats)

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
