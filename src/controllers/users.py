from datetime import datetime, timezone

from flask import Flask, flash

from src.controllers.controller import error_handler
from src.database.models.users import User
from src.database.sql.users import UserORM
from src.controllers.controller import Controllers


class UsersController(Controllers):
    def __init__(self):
        super().__init__()
        self.users: list[User] = list()


    def init_app(self, app: Flask):
        super().init_app(app=app)
        # self.load_users()


    @error_handler
    async def load_users(self):
        with self.get_session() as session:
            # Fetch all users from the database
            users_orm_list: list[UserORM] = session.query(UserORM).all()

            # Convert ORM users to Pydantic User models
            self.users = [User(**user.to_dict()) for user in users_orm_list]


    @error_handler
    async def create_user(self, user_data: User) -> User | None:
        """Create a new user."""
        with self.get_session() as session:
            # Create a new ORM user object
            user_exist = session.query(UserORM).filter_by(uid=user_data.uid).first()

            if user_exist:
                return None

            user_orm = UserORM(
                uid=str(user_data.uid),
                name=user_data.name,
                email=str(user_data.email),
                password_hash=user_data.password_hash,
                role=user_data.role,
                is_active=user_data.is_active,
                created_at=user_data.created_at)

            # Add the user to the session (commit handled in the controller)
            session.add(user_orm)
            return user_data

    @error_handler
    async def get_user_by_uid(self, uid: str) -> User | None:
        """Fetch user by ID."""
        with self.get_session() as session:
            user_orm = session.query(UserORM).filter_by(uid=uid).first()
            if user_orm is None:
                return None
            return User(**user_orm.to_dict())

    @error_handler
    async def get_user_by_email(self, email: str) -> User | None:
        """

        :param email:
        :return:
        """
        with self.get_session() as session:
            user_orm = session.query(UserORM).filter_by(email=email.casefold()).first()
            if user_orm is None:
                return None
            return User(**user_orm.to_dict())

    @error_handler
    async def login_user(self, email: str, password: str) -> User | None:
        """

        :param email:
        :param password:
        :return:
        """
        with self.get_session() as session:
            user_orm = session.query(UserORM).filter_by(email=email.casefold()).first()
            if user_orm is None:
                return None
            user = User(**user_orm.to_dict())
            if not user.check_password(password=password):
                return None
            user_orm.last_login = datetime.now(timezone.utc)
            return user

    @error_handler
    async def update_user(self, uid: str, data: dict) -> User | None:
        """Update an existing user."""
        with self.get_session() as session:
            user_orm = session.query(UserORM).filter_by(uid=uid).first()
            if not user_orm:
                return None

            # Update fields from the incoming data
            for key, value in data.items():
                if hasattr(user_orm, key):
                    setattr(user_orm, key, value)

            # Return the updated user (commit handled in controller)
            return User(**user_orm.to_dict())


    @error_handler
    async def delete_user(self, uid: str):
        """Delete a user by ID."""
        with self.get_session() as session:
            user_orm = session.query(UserORM).filter_by(uid=uid).first()
            if not user_orm:
                self.logger.info(f'User of UID: {uid} not found!')
                return None

            # Mark for deletion (commit handled in controller)
            session.delete(user_orm)
            self.logger.info(f"User with ID {uid} deleted successfully.")
            return {"message": "User deleted successfully."}


    @error_handler
    async def search_users(self, search_term: str):
        """Search for users by name or email."""
        with self.get_session() as session:
            users_orm_list = session.query(UserORM).filter(
                (UserORM.name.ilike(f"%{search_term}%")) |
                (UserORM.email.ilike(f"%{search_term}%"))
            ).all()

            if not users_orm_list:
                self.logger.info("No users found matching your search")
                return []

            return [User(**user.to_dict()) for user in users_orm_list]


    @error_handler
    async def get_users_by_role(self, role: str):
        """Fetch all users by a specific role."""
        with self.get_session() as session:
            if role not in ['seeker', 'employer', 'admin']:
                self.logger.info("Invalid role provided")
                return None
            users_orm_list = session.query(UserORM).filter_by(role=role).all()
            return [User(**user.to_dict()) for user in users_orm_list]

    async def send_reset_link(self, email: EnailModel):

        """

        :return:
        """
        pass

