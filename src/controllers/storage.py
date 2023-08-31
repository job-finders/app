from flask import Flask

from src.database.models import Job
from src.database.sql.jobs import JobsORM
from src.controllers.controller import Controllers


class StorageController(Controllers):

    def __init__(self):
        super().__init__()
        self.jobs: list[Job] = []

    def load_jobs_from_database(self) -> list[Job]:
        """
            will load all the jobs from database then return them
        :return:
        """
        with self.get_session() as session:
            # TODO in future maybe load only jobs which are not expired
            jobs_list = session.query(JobsORM).filter().all()
            return [Job(**job.to_dict()) for job in jobs_list if job] if jobs_list else []

    def store_jobs_to_database(self, jobs: list[Job]):
        """
            this will either create new records on database or update existing ones
        :param jobs:
        :return:
        """
        with self.get_session() as session:
            session.bulk_save_objects([JobsORM(**job.disp_dict()) for job in jobs if job], return_defaults=True)
            session.commit()

    def init_app(self, app: Flask):
        self.jobs = self.load_jobs_from_database()

