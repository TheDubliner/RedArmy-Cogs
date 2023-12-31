from .quakestats import QuakeStats

__red_end_user_data_statement__ = (
    "This cog stores data attached to a user ID for the purpose of displaying "
    "player stats. It does store any other data.\n"
    "This cog supports data removal requests."
)


async def setup(bot):
    await bot.add_cog(QuakeStats(bot))
