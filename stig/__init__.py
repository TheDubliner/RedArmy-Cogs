from .stig import Stig


def setup(bot):
    bot.add_cog(Stig(bot))
