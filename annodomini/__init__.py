from .annodomini import AnnoDomini

__red_end_user_data_statement__ = (
    "This cog stores data attached to a user ID for the purpose of running "
    " the game and saving statistics.\n"
    "This cog supports data removal requests."
)


async def setup(bot):
    await bot.add_cog(AnnoDomini(bot))
