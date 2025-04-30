"""Export database repository classes."""

from .bots import BotRepo
from .clean_logs import CleanLogRepo
from .clients import ClientRepo
from .tokens import TokenRepo
from .users import UserRepo

user_repo = UserRepo()
token_repo = TokenRepo()
clean_log_repo = CleanLogRepo()
client_repo = ClientRepo()
bot_repo = BotRepo()

__all__ = ["BotRepo", "CleanLogRepo", "ClientRepo", "TokenRepo", "UserRepo"]
