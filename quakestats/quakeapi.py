"""
Basic interface to download stats from the Quake Champions API.

Inspired by https://github.com/phy1um/stats.quake.com-API-Wrapper
"""
import requests
from io import BytesIO
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from .constants import (
    APIEXT,
    BASEURL,
    HUMAN_RANKS,
    RANKS
)

from redbot.core import (
    commands,
    data_manager
)


def _get_resource_bytes(path, name, ext):
    return requests.get(BASEURL + f"/{path}/{name}.{ext}")


def get_icon_bytes(name):
    return _get_resource_bytes("icons", name, "png")


def get_weapon_icon_bytes(name):
    return _get_resource_bytes("weapons", name, "png")


def get_nameplate_bytes(name):
    return _get_resource_bytes("nameplates", name, "png")


def get_champion_portrait_bytes(name):
    return _get_resource_bytes("champions", name, "png")


def get_map_portrait_bytes(name):
    return _get_resource_bytes("maps", name, "jpg")


def get_medal_bytes(name):
    return _get_resource_bytes("medals", name, "png")


def get_rank_bytes(name):
    return _get_resource_bytes("ranks", name, "png")



class QuakeWrapper():
    """
    Basic interface for downloading stats from the API.

    Parameters
    ----------
    parent : `commands.Cog`
        Controlling cog.

    Attributes
    ----------
    baseurl : `str`
        Root URL for the service (required for accessing images)
    apiurl : `str`
        Root URL for the API
    """
    def __init__(self, parent):
        self.baseurl = BASEURL
        self.apiurl = BASEURL + APIEXT
        self.cog = parent

    def _dispatcher(self, url: str, params: dict) -> Optional[dict]:
        """
        Internal helper method for sending get requests and returning JSON
        data.

        Parameters
        ----------
        url : `str`
            Full URL for request
        params : `dict`
            Parameters to pass in the request
        """
        result = requests.get(
            url=url,
            params=params
        )
        if result.status_code == 200 and \
           result.headers.get('content-type') == 'application/json' and not \
           result.json().get('code') == 404:
            return result.json()
        return None

    def get_player_stats(self, name: str) -> dict:
        """
        Queries the API for a player’s stats.

        Parameters
        ----------
        name : `str`
            Player name
        """
        url = self.apiurl + "Player/Stats"
        stats = self._dispatcher(
            url=url,
            params={"name": name}
            )
        if stats:
            return stats
        return None

    def get_match_stats(self, uid: str, name: str = None) -> Optional[dict]:
        """
        Queries the API for specific match stats.

        Parameters
        ----------
        uid : `str`
            Match ID
        """
        url = self.apiurl + "Player/Games"
        params = {
            "id": uid
        }
        if name:
            params["name"] = name
        stats = self._dispatcher(
            url=url,
            params=params
        )
        if stats:
            return stats
        return None

    def get_match_summary(self, name: str) -> Optional[dict]:
        """
        Queries the API for a player’s recent match stats.

        Parameters
        ----------
        name : `str`
            Player name
        """
        url = self.apiurl + "Player/GamesSummary"
        stats = self._dispatcher(
            url=url,
            params={"name": name}
        )
        if stats:
            return stats
        return None

    def get_leaderboard(
        self, board: str, from_: str, season: str = "current") \
            -> Optional[dict]:
        """
        Queries the API for a player’s recent match stats.

        Parameters
        ----------
        board : `str`
            Either ``duel`` or ``tdm``
        from_ : `int`
            Starting number
        season : `str`
            Season name (defaults to ``current``)
        """
        url = self.apiurl + "Leaderboard"
        stats = self._dispatcher(
            url=url,
            params={
                "from": from_,
                "season": season,
                "board": board
                }
        )
        if stats:
            return stats
        return None

    @staticmethod
    def get_player_rank(rank, human=False):
        """
        Returns rank name from number.

        Parameters
        ----------
        human : `bool`
            True, returns the human-readable value.
            False, returns value used by Quake API.
        """
        grade = "Zero_01"
        for value in RANKS:
            if int(rank) >= value[0]:
                grade = value[1]
                break
        if human:
            return HUMAN_RANKS[grade]
        return grade

    def get_player_image(self, stats):
        """
        Creates the player’s background/profile image imprinted with name and
        level.

        Parameters
        ----------
        stats : `dict`
            JSON data returned by API

        Returns
        -------
        buffer : `BytesIO`
            PNG image
        """
        # merge background and icon images
        background = Image.open(
            BytesIO(
                get_nameplate_bytes(
                    stats["playerLoadOut"]["namePlateId"]).content))
        icon = Image.open(
            BytesIO(
                get_icon_bytes(
                    stats["playerLoadOut"]["iconId"]).content))
        background.paste(icon, (8, 8))

        # select bundled font
        WHITE = (255, 255, 255)
        fontpath = Path.joinpath(data_manager.bundled_data_path(self.cog),
                                 f"Exo-Bold.otf")
        font = ImageFont.truetype(font=str(fontpath), size=14)
        pen = ImageDraw.Draw(background)

        pen.text((73, 21), stats["name"],
                 font=font, fill=WHITE)
        pen.text((73, 37), "Level " + str(stats["playerLevelState"]["level"]),
                 font=font, fill=WHITE)

        buffer = BytesIO()
        background.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer
