from database.models.users import User
from database.sql import Session
from database.sql.users import UserORM


async def get_user_details(uid: str) -> User:
    """Get the details for a user by their ID."""

    # Assuming you have a database session and engine configured
    with Session() as session:
        # Perform the query to retrieve the user based on the uid
        user_orm = session.query(UserORM).filter(UserORM.uid == uid).first()
        # user_orm if user_orm will use the custom bool method in the class
        return User(**user_orm.to_dict()) if user_orm else None
