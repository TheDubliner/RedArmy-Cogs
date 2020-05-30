import asyncio
import csv
import logging
import random
import re
import time
import traceback

from pathlib import Path

import discord

from redbot.core.utils.chat_formatting import pagify
from redbot.core import (
    data_manager
)

class TooManyGamesException(Exception):
    """Error thrown when there are too many games in progress."""
    pass

class AnnoDominiPlayer:
    """
    Simple class to embody players and their hands.

    Attributes
    ----------
    member : `discord.Member`
        Reference to the Discord member
    cards : `list` of `AnnoDominiCard`
        The player’s hand of cards
    card_embed : `discord.Message`
        Reference to the bot message containing the player’s hand
    owner : `Bool`
        Whether player created their current game
    """
    def __init__(self, ctx, owner=False):
        self.member = ctx.author
        self.cards = []
        self.card_embed = None
        self.owner = owner


class AnnoDominiCard:
    """
    Simple class to embody an Anno Domini card.

    The card holds information displayed to the players and
    then revealed when an order is challenged. The start and
    end dates are used in comparisons to check the order is
    legitimate.

    Attributes
    ----------
    cid : `str`
        Card ID number
    start : `tuple`
        Tuple in form (YYYY, MM, DD)
    end : `tuple`
        Tuple in form (YYYY, MM, DD)
    name : `str`
        The teaser information on the obverse of a card
    desc : `str`
        The revealed information on the reverse of a card
    topic : `str`
        Category of event
    """
    def __init__(self, cid: str, start: str, end: str,
                 name: str, desc: str, topic: str):
        self.cid = cid
        self.start = start
        self.end = (start, end)
        self.name = name
        self.desc = desc
        self.topic = topic

    def __lt__(self, x):
        """
        Date A is earlier than date B if it both started and
        ended before date B.
        """
        if self.start <= x.start and self.end <= x.start:
            return True
        return False

    def __le__(self, x):
        """
        Date A and date B are overlapping if:
        * date A occurred entirely during date B
        * date B occurred entirely during date A
        * date A ended after date B started but before B ended
        * date A started before date B ended and after A started
        """
        if ((self.start <= x.start and self.end >= x.end) or
            (self.start >= x.start and self.end <= x.end) or
            (self.start >= x.start and self.start <= x.end) or
            (self.end >= x.start and self.end <= x.end)):
            return True

    @property
    def start(self):
        return self._start

    @start.setter
    def start(self, value):
        self._start = self._parse_date(value)

    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, value: tuple):
        if value[1]:
            self._end = self._parse_date(value[1])
        else:
            self._end = self._parse_date(value[0], end=True)

    def _parse_date(self, date, end: bool = False) -> tuple:
        """
        Helper method to convert human input dates into simple tuples.

        If no end date is provided, we build it based on the start date.
        Unspecific dates are automatically extended to the correct range.
        """
        date = [int(x) for x in re.split("(?<!^)-|[/.]", date)]
        if not end:
            if len(date) == 1:
                date.extend([1, 1])
            if len(date) == 2:
                date.extend([1])
        else:
            if len(date) == 1:
                date.extend([12, 31])
            if len(date) == 2:
                date.extend([31])  # FIXME: not every month has 31 days
        return date


class AnnoDominiGame:
    """
    Class to run a game of Anno Domini.

    Attributes
    ----------
    ctx : `commands.Context`
        Context object from which this session is run.
    cog : `commands.Cog`
        A reference to the parent cog.
    gid : `int`
        A unique game id to enable multiple concurrent games.
    starttime : `int`
        When game was started (unused)
    players : `list` of `AnnoDominiPlayer`
        Players in the game.
    turn_order : `int`
        Index of the player whose turn it is.
    cards : `list` of `AnnoDominiCard`
        The cards in the stack.
    board : `list` of `AnnoDominiCard`
        The cards played to the game board.
    board_no : `int`
        The number of boards played.
    board_embed : `discord.Message`
        Reference to message where the current board is embedded.
    live : `Bool`
        Game status.
    log : `logging.Logger`
        Link to the logger.
    msg : `str`
        Current message ready to be sent.
    """
    def __init__(self, parent, ctx, topics: list):
        self.cog = parent
        self.ctx = ctx
        self.gid = self._generate_id()
        self.starttime = int(time.time())
        self.players = []
        self.turn_order = 0
        self.topics = topics
        self.cards = []
        self.board = []
        self.board_no = 0
        self.board_embed = None
        self.live = False
        self.log = logging.getLogger('red.redarmycogs.annodomini')
        self.msg = ''
        self._last_play = int(time.time())  # TODO: integrate this?
        self._task = None

    def _generate_id(self):
        """
        Generate a unique game id for running multiple games.
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
            'A fatal error has occurred in _Anno Domini_, shutting down.'
        )

    async def send_timeout(self):
        """
        Cleanup code when a user times out.
        """
        await self.ctx.send(
            'You did not respond in time. Shutting down.'
        )

    def error_callback(self, fut):
        """
        Checks for errors.
        """
        try:
            fut.result()
        except (asyncio.CancelledError):
            pass
        except asyncio.TimeoutError:
            asyncio.create_task(self.send_timeout())
        except Exception as exc:
            asyncio.create_task(self.send_error())
            msg = 'Error in Anno Domini.'
            self.log.exception(msg)
            stack = ''.join(traceback.TracebackException.from_exception(exc).format())
            self.log.exception(stack)
        try:
            self.cog.games.remove(self)
        except ValueError:
            pass

    async def setup(self):
        """
        Sets up and starts a game of Anno Domini.
        """
        self.live = True
        await self.get_topic_cards()
        await self.dealcards()
        await self.showhands()
        self.newround()
        self._task = asyncio.create_task(self.run())
        self._task.add_done_callback(self.error_callback)

    def validate_cmd(self, m):
        """
        Check on messages to see whether they are valid commands.

        Assumes commands must be one of:
        * play `int` `int`
        * play `int`
        * challenge
        """
        can_challenge = r"(?P<chal>challenge)|" if len(self.board) >= 2 else None
        match = re.match(rf"{can_challenge or ''}play (?P<card>\d+)( (?P<pos>\d+))?", m)
        if not match:
            return False
        if can_challenge and match.group("chal"):
            return True
        if int(match.group("card")) <= len(self.players[self.turn_order].cards) \
            and not match.group("pos"):
            return True
        if int(match.group("card")) <= len(self.players[self.turn_order].cards) \
            and int(match.group("pos")) <= len(self.board):
            return True

    async def check_winner(self):
        """
        Checks if the board is in a winning state and automatically
        challenges.
        """
        chk_idx = self._get_previous_idx()
        player = self.players[chk_idx]
        if len(player.cards) == 0:
            mention = await self.cog.config.guild(self.ctx.guild).doMention()
            name = player.member.display_name
            if mention:
                mention = player.member.mention
            win = await self.check_board()
            self.newround()
            if win:
                await self.ctx.send(f'{name} is the winner!')
                await self.update_scores()
                return True
            else:
                await self.ctx.send(
                    f"{name} played their last card "
                    f"but the order was wrong! They "
                    f"received 3 cards."
                )
                await self.dealcards(player, 3)
                await self.showhands(player)
        return False

    async def run(self):
        """
        Sets up and runs the game.
        """
        while self.live:
            self.turn_order += 1
            if self.turn_order >= len(self.players):
                self.turn_order = 0
            check_winner = await self.check_winner()
            if check_winner:
                break
            await self.showboard()
            mention = await self.cog.config.guild(self.ctx.guild).doMention()
            player = self.players[self.turn_order]
            name = player.member.display_name
            if mention:
                name = player.member.mention
            self.msg = f'It’s {name}’s turn! Play a card'
            can_challenge = len(self.board) >= 2
            if can_challenge:
                self.msg += ' or challenge the previous player!'
            else:
                self.msg += '.'
            await self.send()
            choice = await self.ctx.bot.wait_for(
                            'message',
                            timeout=await self.cog.config.guild(self.ctx.guild).delay(),
                            check=lambda m: (
                            m.author.id == self.players[self.turn_order].member.id
                            and m.channel == self.ctx.channel
                            and self.validate_cmd(m.content.lower())
                        ))
            choice = re.match(r"(?P<chal>challenge)|play (?P<card>\d+)( (?P<pos>\d+))?", choice.content.lower())
            if choice.group("chal"):
                successful_challenge = await self.challenge()
                self.newround()
                await self.showboard()
                if successful_challenge:
                    choice = await self.ctx.bot.wait_for(
                            'message',
                            timeout=await self.cog.config.guild(self.ctx.guild).delay(),
                            check=lambda m: (
                                m.author.id == self.players[self.turn_order].member.id
                                and m.channel == self.ctx.channel
                                and self.validate_cmd(m.content.lower())
                            )
                        )
                    choice = re.match(r"play (?P<card>\d+)( (?P<pos>\d+))?", choice.content.lower())
                    card = int(choice.group("card"))
                    pos = 0
                    if choice.group("pos"):
                        pos = int(choice.group("pos"))
                    self.playcard(card, pos)
                    await self.showhands(self.players[self.turn_order])
                    await self.showboard()
            elif choice.group("card"):
                card = int(choice.group("card"))
                pos = 0
                if choice.group("pos"):
                    pos = int(choice.group("pos"))
                self.playcard(card, pos)
                await self.showhands(self.players[self.turn_order])
                await self.showboard()

    async def send(self):
        """
        Safely send messages.
        """
        for page in pagify(self.msg):
            await self.ctx.send(page)
        self.msg = ''

    async def get_topic_cards(self):
        """
        Fills the stack with cards for the game.
        """
        language = await self.cog.config.guild(self.ctx.guild).language()
        sourcefile = Path.joinpath(data_manager.bundled_data_path(self),
                                   f"data-{language}.csv")
        with open(sourcefile, "r", encoding="utf8") as source:  # TODO: detect encoding
            reader = csv.DictReader(source, delimiter=",")
            for row in reader:
                if row["topic"] in self.topics:
                    self.cards.append(
                        AnnoDominiCard(**row)
                    )
        random.shuffle(self.cards)

    def playcard(self, card: int, position: int):
        """
        Play a card to the game board.

        Parameters
        ----------
        card : `int`
            Card in player’s hand (1-indexed)
        position : `int`
            Location to play that card on board (0-indexed)
        """
        player = self.players[self.turn_order]
        card = player.cards.pop(card-1)
        self.board.insert(position, card)

    async def challenge(self):
        """
        Challenge the order of cards on the board.
        """
        mention = await self.cog.config.guild(self.ctx.guild).doMention()
        chall_idx = self._get_previous_idx()
        challenger, challenged = self.players[self.turn_order], self.players[chall_idx]
        correct = await self.check_board()
        challenger_name, challenged_name = challenger.member.display_name, challenged.member.display_name
        if mention:
            challenger_name, challenged_name = challenger.member.mention, challenged.member.mention
        if correct:
            self.msg = f"The order was correct! {challenger_name} received two cards."
            await self.send()
            await self.dealcards(challenger, 2)
            await self.showhands(challenger)
            return False
        self.msg = f"The order was wrong! {challenged_name} received three cards. " \
                   f"{challenger_name} may now play a card."
        await self.send()
        await self.dealcards(challenged, 3)
        await self.showhands(challenged)
        return True

    async def check_board(self):
        """
        Check if the cards on the board are in the correct order.

        Returns
        -------
        `bool`
            True if order was correct, False if not.
        """
        if self.board == sorted(self.board):
            board_embed = await self._build_board_embed(reveal=True, correct=True)
            await self.revealboard(board_embed)
            return True
        board_embed = await self._build_board_embed(reveal=True, correct=False)
        await self.revealboard(board_embed)
        return False

    async def dealcards(self, player: AnnoDominiPlayer = None, count: int = None):
        """
        Deal cards to the player. If no player is supplied, implication is to
        deal starting hands.

        Parameters
        ----------
        player : `AnnoDominiPlayer`, optional
            Person cards should be dealt to.
        count : `int`, optional
            Number of cards to deal that person.
        """
        if not player:  # assume new game
            startinghand = await self.cog.config.guild(self.ctx.guild).startinghand()
            for player in self.players:
                for _ in range(startinghand):
                    try:
                        player.cards.append(
                            self.cards.pop())
                    except IndexError:
                        pass  # TODO: no cards left?!
        elif player:  # deal extra cards to player
            for _ in range(count):
                try:
                    player.cards.append(  # TODO: refactor to method
                        self.cards.pop())
                except IndexError:
                    pass  # TODO: no cards left!

    async def showhands(self, player=None):
        """
        Show/update the players’ hands. If player is provided, only
        show/update that player’s hand

        Parameters
        ----------
        player : `AnnoDominiPlayer`, optional
            The player whose hand to update.
        """
        if player:
            players = [player]
        else:
            players = self.players
        for player in players:
            hand_embed = await self._build_hand_embed(player)
            if player.card_embed is None:
                player.card_embed = await player.member.send(embed=hand_embed)
            else:
                await player.card_embed.edit(embed=hand_embed)

    async def _build_hand_embed(self, player):
        """
        Builds an embed for the player’s hand.
        """
        hand_embed = discord.Embed(color=discord.Color.green())
        for idx, card in enumerate(player.cards, 1):
            hand_embed.add_field(
                name=f"Card #{idx}", value=f"{card.name}", inline=False)
        hand_embed.set_footer(
            text=f"When it’s your turn, type `play [card #] [space #]`" \
                 f"to play a card or `challenge` to challenge the current "
                 f"order.")
        return hand_embed

    def newround(self):
        """
        Starts a new round of the game.
        """
        self.board_no += 1
        self.board_embed = None
        self.board = []
        self.board.append(self.cards.pop())
        return

    async def showboard(self):
        """
        Shows/updates the game board.
        """
        board_embed = await self._build_board_embed()
        if self.board_embed is None:
            self.board_embed = await self.ctx.channel.send(embed=board_embed)
        else:
            await self.board_embed.edit(embed=board_embed)

    async def revealboard(self, board_embed):
        """
        Updates the game board.
        """
        # TODO: factor this out
        await self.board_embed.edit(embed=board_embed)
        return

    async def update_scores(self):
        """
        Run after a completed game to update players’ stats.
        """
        for player in self.players:
            stats = self.cog.config.member(player.member).all()
            stats["games"] += 1
            if len(player.cards) == 0:
                stats["wins"] += 1
            self.cog.config.member(player.member).set(stats)

    async def _build_board_embed(self, reveal: bool = False,
                                 correct: bool = False):
        """
        Builds an embed for the game board.

        Parameters
        ----------
        reveal : bool
            Includes the solutions to the cards on the board.
        correct : bool
            Indicates whether the order revealed was right/wrong.
        """
        colour = discord.Colour.dark_blue()
        if reveal and correct:
            text = "The order was correct!"
            colour = discord.Colour.green()
        elif reveal and not correct:
            text = "The order was incorrect!"
            colour = discord.Colour.red()
        board_embed = discord.Embed(color=colour)
        board_embed.set_author(name=f"Anno Domini Game {self.gid} Round #{self.board_no}")
        if not reveal:
            for idx, card in enumerate(self.board, 1):
                board_embed.add_field(
                    name=f"Card #{idx}", value=f"{card.name}", inline=False
                )
            player = self.players[self.turn_order]
            board_embed.set_footer(
                text=f"It’s {player.member.display_name}’s turn. Type `play [card #] [space #]`" \
                     f"to play a card after that space (0 for earliest) or `challenge` " \
                     f"to challenge the current order."
            )
        else:
            for idx, card in enumerate(self.board, 1):
                date = self._build_human_readable_date(card.start, card.end)
                board_embed.add_field(
                    name=f"Card #{idx} – {date}", value=f"{card.name}\n{card.desc}", inline=False
                )
            board_embed.set_footer(
                text=text
            )
        return board_embed

    def _build_human_readable_date(self, start_date, end_date):
        """
        Return normal date from boundaries.
        """
        if start_date[1:3] == [1, 1] and end_date[1:3] == [12, 31]:
            if start_date[0] == end_date[0]:
                return str(start_date[0])
            else:
                return f"{str(start_date[0])}–{str(end_date[0])}"
        elif start_date[1:3] == [1, 1] and end_date[1:3] == [1, 1] and abs(end_date[0] - start_date[0]) == 10:
            return f"circa {str(start_date[0]+5)}"  # FIXME: if date is exactly 10 years?
        elif start_date == end_date:
            return f"{str(start_date[2])}.{str(start_date[1])}.{str(start_date[0])}"  # TODO: prettify this
        else:
            return f"{str(start_date[2])}.{str(start_date[1])}.{str(start_date[0])}–{str(end_date[2])}.{str(end_date[1])}.{str(end_date[0])}"

    def _get_previous_idx(self):
        """
        Helper method to get the index of the previous player (when challenged).
        """
        return self.turn_order - 1 if self.turn_order > 0 else len(self.players) - 1
