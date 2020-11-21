import random
import requests

from typing import Optional


BASEURL = "https://api.chucknorris.io/jokes/"


class ChuckNorrisWrapper:
    """
    Basic interface for grabbing quotes from the ChuckNorris.io API.

    Parameters
    ----------
    parent : `commands.Cog`
        Controlling cog.

    Attributes
    ----------
    baseurl : `str`
        Root URL for the service
    """
    def __init__(self, parent):
        self.baseurl = BASEURL
        self.cog = parent

    def _dispatcher(self, url: str, params: dict = None) -> Optional[dict]:
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
        if result.status_code == 200:
            return result.json()
        return None

    def get_random(self, category: str = None, name: str = None) -> dict:
        """
        Returns a random Chuck Norris quote.

        Attributes
        ----------
        category : `str`, optional
            Categories to get quote from separated by commas
        name : `str`, optional
            Name to place instead of Chuck Norris
        """
        url = self.baseurl + "random"
        params = {}
        if category:
            params["category"] = category
        if name:
            params["name"] = name
        return self._dispatcher(url, params)

    def get_categories(self) -> list:
        """
        Return a list of available categories.

        Returns
        -------
        `list`
        """
        url = self.baseurl + "categories"
        return self._dispatcher(url)

    def get_random_search(self, query: str):
        """
        Returns a random Chuck Norris quote containing search term.

        If multiple quotes are found, a random one is returned from the list.

        Attributes
        ----------
        query : `str`, optional
            Search term to look for
        """
        url = self.baseurl + "search"
        params = {"query": query}
        results = self._dispatcher(url, params)
        if results.get('total') != 0:
            return random.choice(results.get('result'))
        return None
