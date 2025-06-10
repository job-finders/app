

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
import pytest
import uuid

@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["jobs_search"], indirect=True)
async def test_get_similar_jobs_basic(get_controller, session, test_app):
    # Setup
    category = create_category(session, name="Engineering")

    target_job_id = str(uuid.uuid4())
    similar_job_id = str(uuid.uuid4())
    non_similar_job_id = str(uuid.uuid4())

    # Target job
    target_job = create_job(
        session,
        job_id=target_job_id,
        title="Senior Python Developer",
        description="Work on API design and backend systems",
        skills="Python FastAPI",
        category_id=category.category_id
    )

    # Similar job
    similar_job = create_job(
        session,
        job_id=similar_job_id,
        title="Backend Engineer",
        description="Develop scalable services",
        skills="Python SQL",
        category_id=category.category_id
    )

    # Job that should be excluded (wrong category + inactive)
    other_category = create_category(session, name="Marketing")
    non_similar_job = create_job(
        session,
        job_id=non_similar_job_id,
        title="Marketing Specialist",
        description="Promote campaigns",
        skills="SEO",
        status=JobStatusEnum.INACTIVE.value,
        category_id=other_category.category_id
    )

    job_search_controller = get_controller

    # Act
    results = await job_search_controller.get_similar_jobs(target_job_id)

    # Assert
    assert len(results) == 1
    assert results[0].job_id == similar_job_id



import pytest
import uuid
from datetime import datetime, timedelta

@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["jobs_search"], indirect=True)
async def test_get_all_jobs_returns_only_active(get_controller, session):
    # Setup
    job_active = create_job(session, job_id=str(uuid.uuid4()), status=JobStatusEnum.ACTIVE.value)
    create_job(session, job_id=str(uuid.uuid4()), status=JobStatusEnum.INACTIVE.value)

    controller = get_controller

    # Act
    result = await controller.get_all_jobs()

    # Assert
    assert result["total_jobs"] == 1
    assert len(result["jobs"]) == 1
    assert result["jobs"][0].job_id == job_active.job_id

@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["jobs_search"], indirect=True)
async def test_get_all_jobs_pagination(get_controller, session):
    # Setup 25 jobs
    for _ in range(25):
        create_job(session, job_id=str(uuid.uuid4()), status=JobStatusEnum.ACTIVE.value)

    controller = get_controller

    # Act
    page_1 = await controller.get_all_jobs(page=1, page_size=10)
    page_2 = await controller.get_all_jobs(page=2, page_size=10)
    page_3 = await controller.get_all_jobs(page=3, page_size=10)

    # Assert
    assert page_1["page"] == 1
    assert len(page_1["jobs"]) == 10

    assert page_2["page"] == 2
    assert len(page_2["jobs"]) == 10

    assert page_3["page"] == 3
    assert len(page_3["jobs"]) == 5

    assert page_1["total_jobs"] == 25
    assert page_1["total_pages"] == 3

@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["jobs_search"], indirect=True)
async def test_get_all_jobs_prefers_featured(get_controller, session):
    # Setup
    featured_job = create_job(
        session,
        job_id=str(uuid.uuid4()),
        is_featured=True,
        created_at=datetime.utcnow() - timedelta(days=1)
    )
    recent_non_featured = create_job(
        session,
        job_id=str(uuid.uuid4()),
        is_featured=False,
        created_at=datetime.utcnow()
    )

    controller = get_controller

    # Act
    result = await controller.get_all_jobs(page=1, page_size=10)

    # Assert
    assert result["total_jobs"] == 2
    assert result["jobs"][0].job_id == featured_job.job_id  # Featured comes first

@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["jobs_search"], indirect=True)
async def test_get_all_jobs_empty_result(get_controller, session):
    controller = get_controller

    # Act
    result = await controller.get_all_jobs()

    # Assert
    assert result["total_jobs"] == 0
    assert result["total_pages"] == 0
    assert result["jobs"] == []

######### test search jobs #####

import pytest
import uuid
from datetime import datetime, timedelta
from app.models import JobStatusEnum


@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["jobs_search"], indirect=True)
async def test_search_jobs_returns_matching_title(get_controller, session):
    # Create matching and non-matching jobs
    matching = create_job(
        session,
        job_id=str(uuid.uuid4()),
        title="Python Developer",
        description="Something else",
        status=JobStatusEnum.ACTIVE.value
    )
    create_job(
        session,
        job_id=str(uuid.uuid4()),
        title="React Engineer",
        description="Frontend stuff",
        status=JobStatusEnum.ACTIVE.value
    )

    controller = get_controller

    # Act
    result = await controller.search_jobs(keyword="Python")

    # Assert
    assert result["total_jobs"] == 1
    assert result["jobs"][0].title == matching.title


@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["jobs_search"], indirect=True)
async def test_search_jobs_returns_matching_description(get_controller, session):
    matching = create_job(
        session,
        job_id=str(uuid.uuid4()),
        title="Unrelated",
        description="Looking for a FastAPI expert",
        status=JobStatusEnum.ACTIVE.value
    )

    controller = get_controller

    result = await controller.search_jobs(keyword="FastAPI")

    assert result["total_jobs"] == 1
    assert result["jobs"][0].description == matching.description


@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["jobs_search"], indirect=True)
async def test_search_jobs_ignores_inactive(get_controller, session):
    create_job(
        session,
        job_id=str(uuid.uuid4()),
        title="Inactive Job",
        description="Should not appear",
        status=JobStatusEnum.INACTIVE.value
    )

    controller = get_controller

    result = await controller.search_jobs(keyword="Inactive")

    assert result["total_jobs"] == 0
    assert len(result["jobs"]) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["jobs_search"], indirect=True)
async def test_search_jobs_pagination_works(get_controller, session):
    for i in range(30):
        create_job(
            session,
            job_id=str(uuid.uuid4()),
            title=f"Test Job {i}",
            description="Generic description",
            status=JobStatusEnum.ACTIVE.value
        )

    controller = get_controller

    page_1 = await controller.search_jobs(keyword="Test", page=1, page_size=10)
    page_2 = await controller.search_jobs(keyword="Test", page=2, page_size=10)
    page_3 = await controller.search_jobs(keyword="Test", page=3, page_size=10)

    assert page_1["total_jobs"] == 30
    assert page_1["total_pages"] == 3
    assert len(page_1["jobs"]) == 10
    assert len(page_2["jobs"]) == 10
    assert len(page_3["jobs"]) == 10


@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["jobs_search"], indirect=True)
async def test_search_jobs_sorts_by_featured_and_date(get_controller, session):
    # Less recent featured
    featured = create_job(
        session,
        job_id=str(uuid.uuid4()),
        title="Featured",
        is_featured=True,
        created_at=datetime.utcnow() - timedelta(days=1),
        status=JobStatusEnum.ACTIVE.value
    )

    # More recent non-featured
    non_featured = create_job(
        session,
        job_id=str(uuid.uuid4()),
        title="Non Featured",
        is_featured=False,
        created_at=datetime.utcnow(),
        status=JobStatusEnum.ACTIVE.value
    )

    controller = get_controller

    result = await controller.search_jobs(keyword="")

    assert result["jobs"][0].job_id == featured.job_id  # Featured comes first
    assert result["jobs"][1].job_id == non_featured.job_id


