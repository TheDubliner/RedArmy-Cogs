from .chuck import ChuckNorris


def setup(bot):
    bot.add_cog(ChuckNorris(bot))
