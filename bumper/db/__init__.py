"""Export database repository classes."""

from .bots import BotRepo
from .clean_logs import CleanLogRepo
from .clients import ClientRepo
from .photos import PhotoRepo
from .tokens import TokenRepo
from .users import UserRepo

user_repo = UserRepo()
token_repo = TokenRepo()
clean_log_repo = CleanLogRepo()
client_repo = ClientRepo(user_repo.get_by_id)
bot_repo = BotRepo()
photo_repo = PhotoRepo()

__all__ = ["BotRepo", "CleanLogRepo", "ClientRepo", "PhotoRepo", "TokenRepo", "UserRepo"]
