# Flask Core
from flask import Flask

# Controllers
from src.controllers.controller import Controllers, error_handler

# Constants
from src.database.constants import utc_time

# Domain Models
from src.database.models import User

# SQL Models (ORMs)
from src.database import UserORM

# Email
from src.emailer import EmailModel


class UsersController(Controllers):
    __dict__ = """        
        UsersController handles all user-related operations for the application.
    
        Responsibilities:
        - Loading users from the database and converting ORM objects to Pydantic models.
        - Creating new users, ensuring uniqueness by UID.
        - Fetching users by UID or email.
        - Authenticating users by email and password, updating last login timestamp.
        - Updating user details and roles with validation.
        - Deleting users by UID.
        - Searching users by name or email.
        - Fetching users by specific roles.
        - (Stub) Sending password reset links via email.
    
        Requirements:
        - SQLAlchemy session management via `get_session()`.
        - UserORM SQLAlchemy model for database operations.
        - User Pydantic model for data validation and serialization.
        - Error handling via the `error_handler` decorator.
        - Logging via `self.logger`.
        - EmailModel for email-related operations (for password reset).
        - The controller expects a factory object for initialization.
        - The controller does not commit changes to the database; commit is handled externally.
    
        Methods:
        - init_app(app: Flask): Initialize the controller with a Flask app.
        - load_users(): Load all users from the database.
        - create_user(user_data: User): Create a new user.
        - get_user_by_uid(uid: str): Fetch a user by UID.
        - get_user_by_email(email: str): Fetch a user by email.
        - login_user(email: str, password: str): Authenticate a user.
        - update_user(uid: str, data: dict): Update user details.
        - update_user_role(user_id: str, role: str): Update a user's role with validation.
        - delete_user(uid: str): Delete a user by UID.
        - search_users(search_term: str): Search users by name or email.
        - get_users_by_role(role: str): Fetch users by role.
        - send_reset_link(email: EmailModel): (Stub) Send a password reset link.
    
    """
    def __init__(self, factory):
        super().__init__(factory)
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
                email=str(str(user_data.email).casefold()),
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
            self.logger.info(f" async def get_user_by_uid : Finding User by UID : {uid}")
            user_orm = session.query(UserORM).filter_by(uid=uid).first()
            if user_orm is None:
                self.logger.info("Did not find User ")
                return None
            self.logger.info("User Found : ")
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
            self.logger.info(f"Inside Login User : {email} - {password}")
            user_orm = session.query(UserORM).filter_by(email=email.casefold()).first()
            if user_orm is None:
                self.logger.info("User Not Found : ")
                return None
            self.logger.info("Is User Found : ")
            user = User(**user_orm.to_dict())
            if not user.check_password(password=password):
                self.logger.info("Password Invalid")
                return None

            _last_login = utc_time()
            user_orm.last_login = _last_login
            user.last_login = _last_login
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
    async def update_user_role(self, user_id: str, role: str) -> User:
        """
        Update a user's role with validation
        :param user_id: UUID of the user to update
        :param role: New role to assign
        :return: Updated User object
        """
        with self.get_session() as session:
            # Validate allowed roles
            valid_roles = ["seeker", "employer", "admin"]  # Adjust based on your Enum
            if role.lower() not in valid_roles:
                raise ValueError(f"Invalid role: {role}. Valid roles are {', '.join(valid_roles)}")

            # Get and validate user exists
            user_orm = session.query(UserORM).filter_by(uid=user_id).first()
            if not user_orm:
                raise ValueError(f"User with ID {user_id} not found")

            # Skip update if role hasn't changed
            if user_orm.role.lower() == role.lower():
                return User(**user_orm.to_dict())

            # Update and commit
            user_orm.role = role.lower()
            # session.commit()

            # Return fresh user object
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

    async def send_reset_link(self, email: EmailModel):

        """

        :return:
        """
        pass

