from .quakestats import QuakeStats


def setup(bot):
    bot.add_cog(QuakeStats(bot))
