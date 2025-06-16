import math

import pytest

from tests.jobs.factories import *


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
        status=JobStatusEnum.CLOSED.value,
        category_id=other_category.category_id
    )

    job_search_controller = get_controller

    # Act
    results = await job_search_controller.get_similar_jobs(target_job_id)

    # Assert
    assert len(results) == 1
    assert results[0].job_id == similar_job_id

@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["jobs_search"], indirect=True)
async def test_get_all_jobs_returns_only_active(get_controller, session):
    # Setup
    job_active = create_job(session, job_id=str(uuid.uuid4()), status=JobStatusEnum.ACTIVE.value)
    create_job(session, job_id=str(uuid.uuid4()), status=JobStatusEnum.CLOSED.value)

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
        created_at=datetime.now(timezone.utc) - timedelta(days=1)
    )
    recent_non_featured = create_job(
        session,
        job_id=str(uuid.uuid4()),
        is_featured=False,
        created_at=datetime.now(timezone.utc)
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
        status=JobStatusEnum.CLOSED.value
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
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
        status=JobStatusEnum.ACTIVE.value
    )

    # More recent non-featured
    non_featured = create_job(
        session,
        job_id=str(uuid.uuid4()),
        title="Non Featured",
        is_featured=False,
        created_at=datetime.now(timezone.utc),
        status=JobStatusEnum.ACTIVE.value
    )

    controller = get_controller

    result = await controller.search_jobs(keyword="")

    assert result["jobs"][0].job_id == featured.job_id  # Featured comes first
    assert result["jobs"][1].job_id == non_featured.job_id


####################################################################
###############     TEST CASES FOR list_categories 

@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["category_controller"], indirect=True)
async def test_list_job_categories_returns_categories_with_jobs(get_controller, session):
    # --- Setup ---
    category = create_category(session, name="Engineering")
    job = create_job(
        session,
        job_id=str(uuid.uuid4()),
        title="Software Engineer",
        category_id=category.category_id,
        status=JobStatusEnum.ACTIVE.value,
        created_at=datetime.now(timezone.utc)
    )

    controller = get_controller

    # --- Act ---
    result = await controller.list_job_categories()

    # --- Assert ---
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].name == "Engineering"
    assert len(result[0].jobs) == 1
    assert result[0].jobs[0].title == "Software Engineer"


@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["category_controller"], indirect=True)
async def test_list_job_categories_returns_empty_list_when_no_categories(get_controller, session):
    controller = get_controller

    result = await controller.list_job_categories()

    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["category_controller"], indirect=True)
async def test_list_job_categories_includes_multiple_categories_and_jobs(get_controller, session):
    # Create multiple categories and jobs
    cat1 = create_category(session, name="Marketing")
    cat2 = create_category(session, name="Finance")

    create_job(session, job_id=str(uuid.uuid4()), title="SEO Specialist", category_id=cat1.category_id)
    create_job(session, job_id=str(uuid.uuid4()), title="Financial Analyst", category_id=cat2.category_id)

    controller = get_controller
    result = await controller.list_job_categories()

    assert len(result) == 2
    category_names = {c.name for c in result}
    assert "Marketing" in category_names
    assert "Finance" in category_names
    total_jobs = sum(len(cat.jobs) for cat in result)
    assert total_jobs == 2


###############################################################
############### TEST CASES FOR SEARCH BY CATEGORY

@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["job_controller"], indirect=True)
async def test_search_jobs_by_category_returns_paginated_jobs(get_controller, session):
    # --- Setup ---
    category = create_category(session, name="Engineering")

    # Create 3 jobs in this category
    for _ in range(3):
        create_job(
            session=session,
            job_id=str(uuid.uuid4()),
            title="Backend Engineer",
            category_id=category.category_id,
            is_featured=True,
            status=JobStatusEnum.ACTIVE.value,
            created_at=datetime.now(timezone.utc)
        )

    controller = get_controller

    # --- Act ---
    result = await controller.search_jobs_by_category("Engineering", page=1, page_size=2)

    # --- Assert ---
    assert result["page"] == 1
    assert result["page_size"] == 2
    assert result["total_jobs"] == 3
    assert result["total_pages"] == math.ceil(3 / 2)
    assert len(result["jobs"]) == 2
    assert all(job.title == "Backend Engineer" for job in result["jobs"])


@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["job_controller"], indirect=True)
async def test_search_jobs_by_category_returns_empty_if_no_matching_category(get_controller, session):
    controller = get_controller

    result = await controller.search_jobs_by_category("NonExistentCategory")

    assert result["total_jobs"] == 0
    assert result["total_pages"] == 0
    assert result["page"] == 1
    assert result["jobs"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["job_controller"], indirect=True)
async def test_search_jobs_by_category_ignores_inactive_jobs(get_controller, session):
    category = create_category(session, name="Design")

    # Add one inactive job
    create_job(
        session=session,
        job_id=str(uuid.uuid4()),
        title="UI/UX Designer",
        category_id=category.category_id,
        status=JobStatusEnum.ARCHIVED.value,
        created_at=datetime.now(timezone.utc)
    )

    controller = get_controller
    result = await controller.search_jobs_by_category("Design")

    assert result["total_jobs"] == 0
    assert result["jobs"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["job_controller"], indirect=True)
async def test_search_jobs_by_category_case_insensitive_match(get_controller, session):
    category = create_category(session, name="Sales")
    create_job(
        session=session,
        job_id=str(uuid.uuid4()),
        title="Account Executive",
        category_id=category.category_id,
        status=JobStatusEnum.ACTIVE.value,
        created_at=datetime.now(timezone.utc)
    )

    controller = get_controller
    result = await controller.search_jobs_by_category("sales")

    assert result["total_jobs"] == 1
    assert result["jobs"][0].title == "Account Executive"


#######################################################################################
#####################   TEST CASES FOR GET JOB BY ID

@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["job_controller"], indirect=True)
async def test_get_job_by_id_returns_active_job(get_controller, session):
    job_id = str(uuid.uuid4())
    job = create_job(
        session=session,
        job_id=job_id,
        title="Software Engineer",
        status=JobStatusEnum.ACTIVE.value,
        created_at=datetime.now(timezone.utc)
    )

    controller = get_controller
    result = await controller.get_job_by_id(job_id)

    assert result is not None
    assert result.job_id == job_id
    assert result.title == "Software Engineer"


@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["job_controller"], indirect=True)
async def test_get_job_by_id_returns_none_for_nonexistent_id(get_controller, session):
    controller = get_controller
    result = await controller.get_job_by_id(str(uuid.uuid4()))

    assert result is None


@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["job_controller"], indirect=True)
async def test_get_job_by_id_ignores_inactive_jobs(get_controller, session):
    job_id = str(uuid.uuid4())
    create_job(
        session=session,
        job_id=job_id,
        title="Old Position",
        status=JobStatusEnum.ARCHIVED.value,
        created_at=datetime.now(timezone.utc)
    )

    controller = get_controller
    result = await controller.get_job_by_id(job_id)

    assert result is None


@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["job_controller"], indirect=True)
async def test_get_job_by_id_handles_invalid_uuid_format(get_controller):
    controller = get_controller
    # Assuming your database layer doesn't raise but just returns None if ID doesn't match format
    result = await controller.get_job_by_id("not-a-uuid")
    assert result is None

##################################################################################

@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["job_controller"], indirect=True)
async def test_get_job_by_reference_found(get_controller, session):
    reference = "REF123ABC"
    # Insert job with lowercase job_ref to test case insensitivity
    job = create_job_with_ref(session, job_ref=reference.lower(), title="Test Job")

    controller = get_controller
    result = await controller.get_job_by_reference(reference)

    assert result is not None
    assert result.job_ref == reference.lower()
    assert result.title == "Test Job"

@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["job_controller"], indirect=True)
async def test_get_job_by_reference_not_found_returns_none(get_controller):
    controller = get_controller
    result = await controller.get_job_by_reference("NON_EXISTENT_REF")
    assert result is None

@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["job_controller"], indirect=True)
async def test_get_job_by_reference_is_case_insensitive(get_controller, session):
    reference = "MixedCaseRef"
    job = create_job_with_ref(session, job_ref=reference.lower(), title="Case Insensitive Job")

    controller = get_controller
    # Pass different casing to ensure casefold() usage works
    result = await controller.get_job_by_reference("MIXEDcaseref")

    assert result is not None
    assert result.job_ref == reference.lower()



######################################################################################
######################      TEST JOB ARCHIVES
######################################################################################



@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["job_controller"], indirect=True)
async def test_archive_job_listing_success(get_controller, session):
    # Setup
    job = create_job(session, status="active")  # Assume this factory sets up a minimal valid job

    controller = get_controller
    result = await controller.archive_job_listing(job.id)

    assert result is not None
    assert result.job_id == job.id
    assert result.status == JobStatusEnum.ARCHIVED.value
    assert result.expiration_date == (datetime.now(timezone.utc).date() - timedelta(days=1))
    assert isinstance(result.updated_at, datetime)

    # Optional: Check ORM was updated in DB (not just the returned object)
    updated_job = session.get(type(job), job.id)
    assert updated_job.status == JobStatusEnum.ARCHIVED.value

@pytest.mark.asyncio
@pytest.mark.parametrize("get_controller", ["job_controller"], indirect=True)
async def test_archive_job_listing_job_not_found(get_controller):
    controller = get_controller
    result = await controller.archive_job_listing("non-existent-job-id")

    assert result is None


############################################################################
####################TEST FEATURED JOBS WITH RESULTS
############################################################################


@pytest.mark.asyncio
async def test_get_featured_jobs_with_results(get_controller, session):
    # Setup: Add multiple featured jobs
    job1 = create_job(session, is_featured=True, status=JobStatusEnum.ACTIVE.value, updated_at=datetime.now(timezone.utc))
    job2 = create_job(session, is_featured=True, status=JobStatusEnum.ACTIVE.value, updated_at=datetime.now(timezone.utc) - timedelta(hours=1))

    controller = get_controller
    result = await controller.get_featured_jobs(page=1, page_size=10)

    assert result["total_jobs"] == 2
    assert result["page"] == 1
    assert result["page_size"] == 10
    assert result["total_pages"] == 1
    assert len(result["jobs"]) == 2
    assert result["jobs"][0].updated_at >= result["jobs"][1].updated_at  # Order check

@pytest.mark.asyncio
async def test_get_featured_jobs_empty_result(get_controller, session):
    # No jobs in DB
    controller = get_controller
    result = await controller.get_featured_jobs()

    assert result["total_jobs"] == 0
    assert result["jobs"] == []
    assert result["total_pages"] == 0

@pytest.mark.asyncio
async def test_get_featured_jobs_ignores_non_featured(get_controller, session):
    create_job(session, is_featured=False, status=JobStatusEnum.ACTIVE.value)
    controller = get_controller
    result = await controller.get_featured_jobs()
    assert result["total_jobs"] == 0
    assert result["jobs"] == []

@pytest.mark.asyncio
async def test_get_featured_jobs_ignores_inactive(get_controller, session):
    create_job(session, is_featured=True, status="archived")
    controller = get_controller
    result = await controller.get_featured_jobs()
    assert result["total_jobs"] == 0
    assert result["jobs"] == []

@pytest.mark.asyncio
async def test_get_featured_jobs_pagination(get_controller, session):
    # 30 featured jobs
    for _ in range(30):
        create_job(session, is_featured=True, status=JobStatusEnum.ACTIVE.value)

    controller = get_controller
    result_page_1 = await controller.get_featured_jobs(page=1, page_size=10)
    result_page_2 = await controller.get_featured_jobs(page=2, page_size=10)
    result_page_3 = await controller.get_featured_jobs(page=3, page_size=10)

    assert result_page_1["page"] == 1
    assert result_page_2["page"] == 2
    assert result_page_3["page"] == 3
    assert result_page_3["jobs"] != []  # Last page should still have jobs
    assert result_page_3["total_pages"] == 3

@pytest.mark.asyncio
async def test_get_featured_jobs_page_beyond_range(get_controller, session):
    create_job(session, is_featured=True, status=JobStatusEnum.ACTIVE.value)

    controller = get_controller
    result = await controller.get_featured_jobs(page=10, page_size=10)

    assert result["page"] == 10
    assert result["jobs"] == []
    assert result["total_jobs"] == 1
    assert result["total_pages"] == 1



################################################################################
############### TEST CASES FOR GET JOBS BY TITLE ###############################


@pytest.mark.asyncio
async def test_get_jobs_by_title_exact_match(get_controller, session):
    create_job(session, title="Senior Python Developer")

    controller = get_controller
    result = await controller.get_jobs_by_title("Senior Python Developer")

    assert result["total_jobs"] == 1
    assert result["jobs"][0].title == "Senior Python Developer"

@pytest.mark.asyncio
async def test_get_jobs_by_title_partial_match(get_controller, session):
    create_job(session, title="Frontend Engineer")
    create_job(session, title="Frontend Lead Engineer")

    controller = get_controller
    result = await controller.get_jobs_by_title("Frontend")

    assert result["total_jobs"] == 2
    assert all("Frontend" in job.title for job in result["jobs"])

@pytest.mark.asyncio
async def test_get_jobs_by_title_case_insensitive(get_controller, session):
    create_job(session, title="React Developer")

    controller = get_controller
    result = await controller.get_jobs_by_title("react developer")

    assert result["total_jobs"] == 1
    assert result["jobs"][0].title == "React Developer"

@pytest.mark.asyncio
async def test_get_jobs_by_title_pagination(get_controller, session):
    for i in range(30):
        create_job(session, title=f"Backend Developer {i}")

    controller = get_controller
    result = await controller.get_jobs_by_title("Backend", page=2, page_size=10)

    assert result["page"] == 2
    assert len(result["jobs"]) == 10




@pytest.mark.asyncio
async def test_get_jobs_by_title_no_match(get_controller, session):
    create_job(session, title="iOS Developer")

    controller = get_controller
    result = await controller.get_jobs_by_title("Android")

    assert result["total_jobs"] == 0
    assert result["jobs"] == []

@pytest.mark.asyncio
async def test_get_jobs_by_title_ignores_inactive(get_controller, session):
    create_job(session, title="Go Developer", status="archived")

    controller = get_controller
    result = await controller.get_jobs_by_title("Go Developer")

    assert result["total_jobs"] == 0
    assert result["jobs"] == []

@pytest.mark.asyncio
async def test_get_jobs_by_title_special_chars_escaped(get_controller, session):
    # `%` would match everything unless escaped
    create_job(session, title="100% Remote Developer")
    controller = get_controller

    result = await controller.get_jobs_by_title("100% Remote")
    assert result["total_jobs"] == 1
    assert "100%" in result["jobs"][0].title

@pytest.mark.asyncio
async def test_get_jobs_by_title_page_out_of_range(get_controller, session):
    create_job(session, title="Data Engineer")

    controller = get_controller
    result = await controller.get_jobs_by_title("Data", page=5, page_size=10)

    assert result["page"] == 5
    assert result["jobs"] == []

@pytest.mark.asyncio
async def test_get_jobs_by_title_empty_title_returns_all(get_controller, session):
    create_job(session, title="Rust Developer")
    create_job(session, title="C++ Engineer")

    controller = get_controller
    result = await controller.get_jobs_by_title("")

    assert result["total_jobs"] == 2
    assert len(result["jobs"]) == 2



#           TESTS CASES FOR GET JOBS BY QUALIFICATIONS

@pytest.mark.asyncio
async def test_get_jobs_by_qualification_basic_match(get_controller, session):
    create_job(session, education_requirements={"bachelor": "Computer Science"})

    controller = get_controller
    result = await controller.get_jobs_by_qualification("computer")

    assert result["total_jobs"] == 1
    assert "Computer Science" in result["jobs"][0].education_requirements["bachelor"]

@pytest.mark.asyncio
async def test_get_jobs_by_qualification_multiple_fields_match(get_controller, session):
    create_job(session, education_requirements={"bachelor": "CS", "diploma": "CS"})

    controller = get_controller
    result = await controller.get_jobs_by_qualification("CS", qualification_types=["bachelor", "diploma"])

    assert result["total_jobs"] == 1

@pytest.mark.asyncio
async def test_get_jobs_by_qualification_case_insensitive(get_controller, session):
    create_job(session, education_requirements={"bachelor": "Physics"})

    controller = get_controller
    result = await controller.get_jobs_by_qualification("physics")

    assert result["total_jobs"] == 1

@pytest.mark.asyncio
async def test_get_jobs_by_qualification_pagination(get_controller, session):
    for i in range(30):
        create_job(session, education_requirements={"masters": "AI"})

    controller = get_controller
    result = await controller.get_jobs_by_qualification("AI", page=2, page_size=10)

    assert result["page"] == 2
    assert len(result["jobs"]) == 10



@pytest.mark.asyncio
async def test_get_jobs_by_qualification_no_match(get_controller, session):
    create_job(session, education_requirements={"phd": "Mathematics"})

    controller = get_controller
    result = await controller.get_jobs_by_qualification("Engineering")

    assert result["total_jobs"] == 0
    assert result["jobs"] == []

@pytest.mark.asyncio
async def test_get_jobs_by_qualification_invalid_field(get_controller, session):
    # Even though the field 'random_cert' exists, it won't be queried unless explicitly specified.
    create_job(session, education_requirements={"random_cert": "Quantum"})

    controller = get_controller
    result = await controller.get_jobs_by_qualification("Quantum")

    assert result["total_jobs"] == 0  # Not in default qualification_types

@pytest.mark.asyncio
async def test_get_jobs_by_qualification_with_empty_qualification(get_controller, session):
    create_job(session, education_requirements={"bachelor": "CS"})

    controller = get_controller
    result = await controller.get_jobs_by_qualification("")

    assert result["total_jobs"] >= 1  # Should return job(s) if fields aren't empty


@pytest.mark.asyncio
async def test_get_jobs_by_qualification_escaped_characters(get_controller, session):
    create_job(session, education_requirements={"bachelor": "C++ Engineer"})

    controller = get_controller
    result = await controller.get_jobs_by_qualification("C++")

    assert result["total_jobs"] == 1
    assert "C++" in result["jobs"][0].education_requirements["bachelor"]

@pytest.mark.asyncio
async def test_get_jobs_by_qualification_ignores_inactive_jobs(get_controller, session):
    create_job(session, education_requirements={"bachelor": "Engineering"}, status="archived")

    controller = get_controller
    result = await controller.get_jobs_by_qualification("Engineering")

    assert result["total_jobs"] == 0

@pytest.mark.asyncio
async def test_get_jobs_by_qualification_with_custom_types(get_controller, session):
    create_job(session, education_requirements={"trade_certificate": "Electrician"})

    controller = get_controller
    result = await controller.get_jobs_by_qualification("Electrician", qualification_types=["trade_certificate"])

    assert result["total_jobs"] == 1

@pytest.mark.asyncio
async def test_get_jobs_by_qualification_page_out_of_range(get_controller, session):
    create_job(session, education_requirements={"phd": "Robotics"})

    controller = get_controller
    result = await controller.get_jobs_by_qualification("Robotics", page=10, page_size=10)

    assert result["jobs"] == []
    assert result["total_pages"] < 10




############################################################################################
# TEST CASES FOR JOBS BY LOCATION
############################################################################################

@pytest.mark.asyncio
async def test_get_jobs_by_location_case_insensitive(get_controller, session):
    create_job(session, city="Bloemfontein", province="Free State", country="South Africa", status="active")
    result = await get_controller.get_jobs_by_location("bloem")
    assert result["total_jobs"] == 1


@pytest.mark.asyncio
async def test_get_jobs_by_location_matches_city(get_controller, session):
    create_job(session, city="Cape Town", province="Western Cape", country="South Africa", status="active")
    result = await get_controller.get_jobs_by_location("cape")
    assert result["total_jobs"] == 1
    assert result["jobs"][0].city == "Cape Town"

@pytest.mark.asyncio
async def test_get_jobs_by_location_matches_province(get_controller, session):
    create_job(session, city="Durban", province="KwaZulu-Natal", country="South Africa", status="active")
    result = await get_controller.get_jobs_by_location("natal")
    assert result["total_jobs"] == 1
    assert result["jobs"][0].province == "KwaZulu-Natal"

@pytest.mark.asyncio
async def test_get_jobs_by_location_matches_country(get_controller, session):
    create_job(session, city="Nairobi", province="Nairobi", country="Kenya", status="active")
    result = await get_controller.get_jobs_by_location("Kenya")
    assert result["total_jobs"] == 1
    assert result["jobs"][0].country == "Kenya"

@pytest.mark.asyncio
async def test_get_jobs_by_location_case_insensitive(get_controller, session):
    create_job(session, city="Bloemfontein", province="Free State", country="South Africa", status="active")
    result = await get_controller.get_jobs_by_location("bloem")
    assert result["total_jobs"] == 1


@pytest.mark.asyncio
async def test_get_jobs_by_location_no_match(get_controller, session):
    create_job(session, city="Joburg", province="Gauteng", country="South Africa", status="active")
    result = await get_controller.get_jobs_by_location("Tokyo")
    assert result["total_jobs"] == 0
    assert result["jobs"] == []

@pytest.mark.asyncio
async def test_get_jobs_by_location_inactive_job_ignored(get_controller, session):
    create_job(session, city="Pretoria", province="Gauteng", country="South Africa", status="archived")
    result = await get_controller.get_jobs_by_location("Pretoria")
    assert result["total_jobs"] == 0


################################################################################################
###############         TEST CASES FOR JOBS BY TYPE


@pytest.mark.asyncio
async def test_search_by_type_full_time_match(get_controller, session):
    create_job(session, position_type="Full-Time", status="active")
    result = await get_controller.search_by_type("full-time")
    assert result["total_jobs"] == 1
    assert result["jobs"][0].event_type.lower() == "full-time"

@pytest.mark.asyncio
async def test_search_by_type_case_insensitive(get_controller, session):
    create_job(session, position_type="Part-Time", status="active")
    result = await get_controller.search_by_type("part-time")
    assert result["total_jobs"] == 1
    assert result["jobs"][0].event_type.lower() == "part-time"


@pytest.mark.asyncio
async def test_search_by_type_no_match(get_controller, session):
    create_job(session, position_type="Contract", status="active")
    result = await get_controller.search_by_type("freelance")
    assert result["total_jobs"] == 0
    assert result["jobs"] == []

@pytest.mark.asyncio
async def test_search_by_type_inactive_job_excluded(get_controller, session):
    create_job(session, position_type="Full-Time", status="archived")
    result = await get_controller.search_by_type("full-time")
    assert result["total_jobs"] == 0


@pytest.mark.asyncio
async def test_search_by_type_empty_string(get_controller, session):
    create_job(session, position_type="Full-Time", status="active")
    create_job(session, position_type="Part-Time", status="active")
    result = await get_controller.search_by_type("")
    # Will return nothing if no job has empty string as a event_type
    assert result["total_jobs"] == 0

@pytest.mark.asyncio
async def test_search_by_type_with_whitespace(get_controller, session):
    create_job(session, position_type="Part-Time", status="active")
    result = await get_controller.search_by_type(" part-time ")
    assert result["total_jobs"] == 0  # Should fail unless stripped

@pytest.mark.asyncio
async def test_search_by_type_special_characters(get_controller, session):
    create_job(session, position_type="C++ Engineer", status="active")
    result = await get_controller.search_by_type("C++ Engineer")
    assert result["total_jobs"] == 1

@pytest.mark.asyncio
async def test_search_by_type_pagination(get_controller, session):
    for _ in range(30):
        create_job(session, position_type="Remote", status="active")
    result = await get_controller.search_by_type("Remote", page=2, page_size=10)
    assert result["page"] == 2
    assert len(result["jobs"]) == 10

@pytest.mark.asyncio
async def test_search_by_type_page_out_of_bounds(get_controller, session):
    create_job(session, position_type="Internship", status="active")
    result = await get_controller.search_by_type("Internship", page=100, page_size=10)
    assert result["jobs"] == []
    assert result["page"] == 100
    assert result["total_jobs"] == 1

##################################################################################################
###############             TEST CASES FOR GET RECENT JOBS
##################################################################################################


@pytest.mark.asyncio
async def test_get_recent_jobs_returns_active_jobs_sorted(get_controller, session):
    create_job(session, status="active", posted_at=datetime(2024, 6, 10), is_featured=False)
    create_job(session, status="active", posted_at=datetime(2024, 6, 11), is_featured=True)
    
    result = await get_controller.get_recent_jobs()

    assert result["total_jobs"] == 2
    assert result["jobs"][0].is_featured  # Featured should come first
    assert result["jobs"][1].posted_at < result["jobs"][0].posted_at


@pytest.mark.asyncio
async def test_get_recent_jobs_excludes_inactive_jobs(get_controller, session):
    create_job(session, status="archived", posted_at=datetime(2024, 6, 11))
    result = await get_controller.get_recent_jobs()
    assert result["total_jobs"] == 0
    assert result["jobs"] == []



@pytest.mark.asyncio
async def test_get_recent_jobs_empty_db(get_controller, session):
    result = await get_controller.get_recent_jobs()
    assert result["jobs"] == []
    assert result["total_jobs"] == 0
    assert result["total_pages"] == 0

@pytest.mark.asyncio
async def test_get_recent_jobs_page_size_capped_to_100(get_controller, session):
    for _ in range(150):
        create_job(session, status="active", posted_at=datetime.now())
    
    result = await get_controller.get_recent_jobs(page=1, page_size=150)
    assert result["page_size"] == 100
    assert len(result["jobs"]) == 100

@pytest.mark.asyncio
async def test_get_recent_jobs_page_out_of_bounds(get_controller, session):
    create_job(session, status="active", posted_at=datetime.now())
    result = await get_controller.get_recent_jobs(page=100, page_size=10)
    assert result["jobs"] == []


@pytest.mark.asyncio
async def test_get_recent_jobs_pagination(get_controller, session):
    for i in range(30):
        create_job(session, status="active", posted_at=datetime(2024, 6, i+1))
    
    result = await get_controller.get_recent_jobs(page=2, page_size=10)
    assert result["page"] == 2
    assert len(result["jobs"]) == 10


#####################################################################################
##########      TEST CASES FOR GET JOBS BY SALARY RANGE
#####################################################################################

@pytest.mark.asyncio
async def test_search_by_salary_range_returns_correct_jobs(session, get_controller):
    # Create jobs with different salary ranges (yearly)
    create_job(session, salary_min=30000, salary_max=50000, status="active")
    create_job(session, salary_min=60000, salary_max=80000, status="active")
    create_job(session, salary_min=90000, salary_max=120000, status="active")

    result = await get_controller.search_by_salary_range(min_salary=40000, max_salary=90000, unit="yearly")
    
    # Should include the 2nd job and possibly 1st (since min_salary=40000)
    assert all(job.salary_min >= 40000 and job.salary_max <= 90000 for job in result['jobs'])
    assert result['total_jobs'] == len(result['jobs'])

@pytest.mark.asyncio
async def test_search_by_salary_range_monthly_unit_conversion(session, get_controller):
    create_job(session, salary_min=30000, salary_max=60000, status="active")  # yearly salary
    
    # Monthly input - 2500 monthly min = 30000 yearly
    result = await get_controller.search_by_salary_range(min_salary=2500, max_salary=5000, unit="monthly")
    
    # Should match job since min_salary=30000 yearly after conversion
    assert any(job.salary_min == 30000 for job in result['jobs'])



@pytest.mark.asyncio
async def test_search_by_salary_range_excludes_inactive_jobs(session, get_controller):
    create_job(session, salary_min=40000, salary_max=60000, status="archived")
    
    result = await get_controller.search_by_salary_range(min_salary=30000, max_salary=70000)
    
    # No active jobs should be returned
    assert result['total_jobs'] == 0
    assert result['jobs'] == []

@pytest.mark.asyncio
async def test_search_by_salary_range_no_results(session, get_controller):
    create_job(session, salary_min=10000, salary_max=20000, status="active")
    
    result = await get_controller.search_by_salary_range(min_salary=50000, max_salary=60000)
    
    assert result['total_jobs'] == 0
    assert result['jobs'] == []

@pytest.mark.asyncio
async def test_search_by_salary_range_min_salary_none(session, get_controller):
    create_job(session, salary_min=20000, salary_max=40000, status="active")
    create_job(session, salary_min=50000, salary_max=70000, status="active")
    
    # No min_salary filter, max_salary only
    result = await get_controller.search_by_salary_range(min_salary=None, max_salary=60000)
    
    assert all(job.salary_max <= 60000 for job in result['jobs'])


@pytest.mark.asyncio
async def test_search_by_salary_range_max_salary_none(session, get_controller):
    create_job(session, salary_min=20000, salary_max=40000, status="active")
    create_job(session, salary_min=50000, salary_max=70000, status="active")
    
    # No max_salary filter, min_salary only
    result = await get_controller.search_by_salary_range(min_salary=30000, max_salary=None)
    
    assert all(job.salary_min >= 30000 for job in result['jobs'])


@pytest.mark.asyncio
async def test_search_by_salary_range_invalid_unit_defaults_to_yearly(session, get_controller):
    create_job(session, salary_min=20000, salary_max=40000, status="active")
    
    # Pass invalid unit - fallback expected (function does not explicitly handle invalid, so behaves as yearly)
    result = await get_controller.search_by_salary_range(min_salary=1500, max_salary=5000, unit="weekly")
    
    # Should NOT convert salary, treat as yearly (likely no results if min_salary=1500 yearly)
    assert isinstance(result['jobs'], list)

@pytest.mark.asyncio
async def test_search_by_salary_range_pagination(session, get_controller):
    for i in range(50):
        create_job(session, salary_min=30000 + i * 1000, salary_max=40000 + i * 1000, status="active")

    result = await get_controller.search_by_salary_range(min_salary=30000, max_salary=100000, page=2, page_size=10)

    assert result['page'] == 2
    assert result['page_size'] == 10
    assert len(result['jobs']) <= 10


##############################################################################################
######3                     TEST CASES FOR GET ACTIVE JOBS

@pytest.mark.asyncio
async def test_get_active_jobs_returns_only_active_not_expired_jobs(session, get_controller):
    # Active and not expired job
    active_job = create_job(
        session,
        status="active",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        posted_at=datetime.now(timezone.utc) - timedelta(days=1)
    )

    # Inactive job
    inactive_job = create_job(
        session,
        status="archived",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        posted_at=datetime.now(timezone.utc) - timedelta(days=2)
    )

    # Expired job
    expired_job = create_job(
        session,
        status="active",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        posted_at=datetime.now(timezone.utc) - timedelta(days=3)
    )

    jobs = await get_controller.get_active_jobs()

    assert any(job.id == active_job.id for job in jobs)
    assert all(job.id != inactive_job.id for job in jobs)
    assert all(job.id != expired_job.id for job in jobs)


@pytest.mark.asyncio
async def test_get_active_jobs_with_job_expiring_now_included(session, get_controller):
    # Job expires exactly now (should be included since expires_at >= current_time)
    job_expiring_now = create_job(
        session,
        status="active",
        expires_at=datetime.now(timezone.utc),
        posted_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )

    jobs = await get_controller.get_active_jobs()

    assert any(job.id == job_expiring_now.id for job in jobs)


@pytest.mark.asyncio
async def test_get_active_jobs_returns_empty_list_if_no_jobs(session, get_controller):
    # Ensure no jobs exist
    session.query(JobsORM).delete()
    session.commit()

    jobs = await get_controller.get_active_jobs()

    assert jobs == []


@pytest.mark.asyncio
async def test_get_active_jobs_ordered_by_posted_at_desc(session, get_controller):
    job_old = create_job(
        session,
        status="active",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        posted_at=datetime.now(timezone.utc) - timedelta(days=3)
    )
    job_new = create_job(
        session,
        status="active",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        posted_at=datetime.now(timezone.utc) - timedelta(days=1)
    )

    jobs = await get_controller.get_active_jobs()

    # Assert jobs are ordered by posted_at descending (newest first)
    posted_dates = [job.posted_at for job in jobs]
    assert posted_dates == sorted(posted_dates, reverse=True)


@pytest.mark.asyncio
async def test_get_active_jobs_excludes_jobs_with_null_expires_at(session, get_controller):
    # Job with expires_at = None (should be excluded)
    job_no_expiry = create_job(
        session,
        status="active",
        expires_at=None,
        posted_at=datetime.now(timezone.utc) - timedelta(days=1)
    )

    jobs = await get_controller.get_active_jobs()

    assert all(job.job_id != job_no_expiry.job_id for job in jobs)


##################################################################################
#################       CREATE SAVED JOBS TEST CASES

@pytest.mark.asyncio
async def test_get_saved_jobs_for_user_returns_jobs_in_order(session, get_controller):
    user_id = "user123"
    now = datetime.now(timezone.utc)

    # Create jobs
    job1 = create_job(session, job_id="job1", posted_at=now - timedelta(days=3))
    job2 = create_job(session, job_id="job2", posted_at=now - timedelta(days=2))
    job3 = create_job(session, job_id="job3", posted_at=now - timedelta(days=1))

    # Saved jobs by user, with different created_at timestamps (saved times)
    saved1 = create_saved_job(session, user_id=user_id, job=job1, created_at=now - timedelta(hours=3))
    saved2 = create_saved_job(session, user_id=user_id, job=job2, created_at=now - timedelta(hours=2))
    saved3 = create_saved_job(session, user_id=user_id, job=job3, created_at=now - timedelta(hours=1))

    result = await get_controller.get_saved_jobs_for_user(user_id)

    # Should be ordered by saved (created_at) desc, so saved3, saved2, saved1
    assert [job.job_id for job in result] == ["job3", "job2", "job1"]

@pytest.mark.asyncio
async def test_get_saved_jobs_for_user_returns_empty_when_none(session, get_controller):
    user_id = "nonexistent_user"
    # Ensure no saved jobs exist for user
    saved_jobs = await get_controller.get_saved_jobs_for_user(user_id)
    assert saved_jobs == []

@pytest.mark.asyncio
async def test_get_saved_jobs_for_user_excludes_orphaned_entries(session, get_controller):
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Create a job and a saved job referencing it
    use_key = str(uuid.uuid4())
    job1 = create_job(session, job_id=use_key, posted_at=now)
    saved1 = create_saved_job(session, user_id=user_id, job_id=use_key, created_at=now)

    # Create an orphaned saved job (job relationship is None)
    saved_orphan = SavedJobORM(user_id=user_id, job_id=None, created_at=now)
    session.add(saved_orphan)
    session.commit()

    result = await get_controller.get_saved_jobs_for_user(user_id)

    # Only job1 should be returned, orphan excluded
    assert len(result) == 1
    assert result[0].job_id == use_key

@pytest.mark.asyncio
async def test_get_saved_jobs_for_user_large_number_of_saved_jobs(session, get_controller):
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Create many saved jobs
    keys = []
    for i in range(100):
        keys.append(str(uuid.uuid4()))
        job = create_job(session, job_id=keys[i], posted_at=now - timedelta(days=i))
        create_saved_job(session, saved_job_id=str(uuid.uuid4()), user_id=user_id, job=job,
                         created_at=now - timedelta(minutes=i))

    saved_jobs = await get_controller.get_saved_jobs_for_user(user_id)

    # Ensure 100 jobs returned, ordered by created_at desc
    assert len(saved_jobs) == len(keys)
    assert saved_jobs[0].job_id == keys[0]
    assert saved_jobs[-1].job_id == keys[-1]  # Oldest saved job
