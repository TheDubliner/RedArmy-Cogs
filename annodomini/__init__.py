from .annodomini import AnnoDomini


def setup(bot):
    bot.add_cog(AnnoDomini(bot))
