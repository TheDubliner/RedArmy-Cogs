from .cobblers import Cobblers


__red_end_user_data_statement__ = (
    "This cog stores data attached to a user ID for the purpose of running "
    " the game and saving statistics.\n"
    "This cog supports data removal requests."
    )


def setup(bot):
    bot.add_cog(Cobblers(bot))
