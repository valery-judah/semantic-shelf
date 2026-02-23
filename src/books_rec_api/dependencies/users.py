from books_rec_api.repositories.users_repository import UsersRepository
from books_rec_api.services.user_service import UserService

_users_repository = UsersRepository()


def get_users_repository() -> UsersRepository:
    return _users_repository


def get_user_service() -> UserService:
    return UserService(repo=get_users_repository())
