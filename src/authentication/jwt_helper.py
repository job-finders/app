from datetime import datetime, timedelta,  timezone

import jwt

from src.config import config_instance
from src.logger import init_logger

jwt_logger = init_logger("jwt")

SECRET_KEY = config_instance().JWT_SECRETS.SECRET_KEY  # ideally from environment variables
ALGORITHM = config_instance().JWT_SECRETS.ALGO
EXPIRATION_MINUTES = 60  # 1 hour

def create_jwt(user_data: dict) -> str:
    payload = {
        "sub": user_data["uid"],
        "role": user_data.get("role"),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=EXPIRATION_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def decode_jwt(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        jwt_logger.warning("JWT expired.")
    except jwt.InvalidTokenError:
        jwt_logger.warning("Invalid JWT.")
    return None
