import time


def boot():

    from src.database.sql.jobs import JobsORM
    from src.database.sql.users import UserORM
    classes_to_create = [JobsORM, UserORM]

    for cls in classes_to_create:
        try:
            cls.create_if_not_table()
        except Exception as e:
            print(str(e))

        time.sleep(2)

