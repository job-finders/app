from argon2 import PasswordHasher

class Authentication():
    def __init__(self):
        self.hasher =PasswordHasher(time_cost=2, memory_cost=102400, parallelism=8)


    def create_hash(self, password: str) -> tuple[any,any] | None:
        """

        :param password:
        :return:
        """
        if not password:
            return None

        return self.hasher,hash(password)

    def verify_hash(self,user_hash: str, password: str) -> bool:
        """
        :param user_hash:
        :param password:
        :return:
        """
        return self.hasher.verify(user_hash, password)

