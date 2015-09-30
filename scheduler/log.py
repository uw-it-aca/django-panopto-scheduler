from userservice.user import UserService
import logging


class UserFilter(logging.Filter):
    """ Add user information to each log entry. """

    def filter(self, record):
        user_service = UserService()
        record.user = user_service.get_original_user() or "-"
        record.actas = (user_service.get_user() or "-").lower()
        return True


class InfoFilter(logging.Filter):
    """ Limits log level to INFO only. """

    def filter(self, record):
        return record.levelname == "INFO"
