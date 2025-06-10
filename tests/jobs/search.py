

import pytest
from src.database import JobsORM, JobCategoryORM
from src.database.models.jobs_model import JobStatusEnum

"""
    get_all_jobs, search_jobs, list_job_categories, search_jobs_by_category, get_job_by_id, get_job_by_reference
"""
import pytest
from src.database import JobsORM, JobCategoryORM
from src.database.models.jobs_model import JobStatusEnum

@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["jobs_search"], indirect=True)
async def test_get_similar_jobs_basic(get_controller, session, test_app):
    # Setup test data
    category = JobCategoryORM(name="Engineering")
    session.add(category)
    session.commit()

    job1 = JobsORM(
        job_id="1", title="Software Engineer",
        description="Develop APIs", skills="Python FastAPI",
        status=JobStatusEnum.ACTIVE.value, category_id=category.id
    )
    job2 = JobsORM(
        job_id="2", title="Backend Developer",
        description="Build services", skills="Python SQL",
        status=JobStatusEnum.ACTIVE.value, category_id=category.id
    )
    session.add_all([job1, job2])
    session.commit()

    # Resolve controller
    job_search_controller = get_controller

    # Act
    results = await job_search_controller.get_similar_jobs("1")

    # Assert
    assert len(results) == 1
    assert results[0].job_id == "2"

