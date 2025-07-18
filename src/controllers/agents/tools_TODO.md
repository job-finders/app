# TODO.md – Keyword-Mining Tool Implementation Tasks  
(Each checklist is tagged with the exact tool it belongs to.)

---

## ✅  IndustryTaxonomyTool
```python
# File: tools/industry_taxonomy.py



    TASK 1  – Acquire controller
        Call get_controller("industry_taxonomy") → controller object.

    TASK 2  – Build query payload
        Payload = {
            "title": job.title,
            "description": job.description,
            "required_skills": job.required_skills,
            "preferred_skills": job.preferred_skills,
            "location": f"{job.city}, {job.province}, {job.country}".strip(" ,,")
        }

    TASK 3  – Execute query
        keywords_with_freq = controller.fetch_keywords(payload)  # returns [(kw, freq)]

    TASK 4  – Filter & return
        Return only keywords whose frequency ≥ 1 and whose similarity score ≥ 0.7
        (controller already returns pre-filtered data).

    The returned keywords must be **industry-standard** and **role-specific**.
 

 PeerJOBSTool


     TASK 1  – Acquire controller
        Call get_controller("jobs") → controller object.

    TASK 2  – Build similarity query
        Query = {
            "title": job.title,
            "skills": job.required_skills + job.preferred_skills,
            "limit": 50,
            "status": ["filled", "active"],
            "min_avg_ats_score": 70
        }

    TASK 3  – Retrieve jobs
        similar_jobs = controller.search_similar_jobs(query)

    TASK 4  – Extract keywords
        all_keywords = []
        for j in similar_jobs:
            tokens = tokenize(j.title + " " + j.description)
            all_keywords.extend(tokens)
        keyword_freq = Counter(all_keywords).most_common()

    TASK 5  – Rank & threshold
        Keep keywords whose tf-idf weight ≥ 0.05 and frequency ≥ 3 across the peer set.

    Return type must be list[tuple[str, int]] sorted by descending frequency.



ParsedCVTool


    TASK 1  – Acquire controller
        Call get_controller("resumes") → controller object.

    TASK 2  – Build filter query
        Query = {
            "job_similarity_title": job.title,
            "skills_overlap_ratio": 0.6,
            "min_ats_score": 70,
            "outcome": ["interviewed", "hired"]
        }

    TASK 3  – Fetch successful resumes
        resumes = controller.get_successful_resumes(query)

    TASK 4  – Extract keywords
        all_keywords = []
        for r in resumes:
            tokens = tokenize(" ".join([r.skills, r.experience_text, r.projects]))
            all_keywords.extend(tokens)
        keyword_freq = Counter(all_keywords).most_common()

    TASK 5  – Post-filter
        Remove generic stop-words and keep the top 50 by tf-idf.

    Return list[tuple[str, int]] sorted by descending frequency.
 
 