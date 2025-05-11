import json
import os
import re
import aiohttp
from typing import Dict, List, Optional

import docx2txt
import fitz  # PyMuPDF
import spacy
from flask import Request, Flask
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

from src.database.models.jobs import Job, ATSReport
from src.database.sql.config import ConfigurationORM
from src.controllers.controller import Controllers, error_handler
from src.controllers.resume_controller import ResumeController
from src.database.models.resume import JobSeekerCV

# CPU-optimized NLP model
nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
CLEAN_TEXT_PATTERN = re.compile(r'[^a-zA-Z0-9\+#\.\s]')
ACTION_VERBS = {"managed", "developed", "led", "created", "implemented"}


class ATSToolController(Controllers):
    """CPU-optimized ATS Analysis Toolkit"""

    def __init__(self):
        super().__init__()
        self.top_n_keywords = 30
        self._vectorizer_cache = {}
        self.nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
        self.industry_keywords = self._load_industry_keywords()
        self.required_sections = ['experience', 'education', 'skills']
        self.resume_controller: ResumeController | None = None

    def init_app(self, app: Flask, resume: ResumeController):
        super().init_app(app=app)
        self.resume_controller = resume


    # Helper methods
    @staticmethod
    def _detect_experience_level(text: str) -> str:
        """Detect experience level from job description"""
        text = text.lower()
        if 'senior' in text: return 'senior'
        if 'junior' in text or 'entry' in text: return 'entry'
        return 'mid'


    @staticmethod
    async def _clean_cover_draft(text: str) -> str:
        """Format cover letter draft"""
        return '\n'.join(line.strip() for line in text.split('\n') if line.strip())

    # CV Specifc ATS Checker
    @staticmethod
    def _load_industry_keywords():
        """Load industry-standard keywords from file or database"""
        # Example implementation - replace with actual data source
        return {
            'technology': ['python', 'aws', 'docker', 'kubernetes'],
            'business': ['project management', 'budgeting', 'strategic planning'],
            'common': ['communication', 'team leadership', 'problem solving']}

    @staticmethod
    def _analyze_sections(cv: JobSeekerCV) -> dict:
        """Check for presence of critical sections"""
        return {
            'experience': bool(cv.experience),
            'education': bool(cv.education),
            'skills': bool(cv.skills),
            'certifications': bool(cv.certifications)
        }

    def _flatten_keywords(self) -> list:
        """Combine all industry keywords"""
        return [
            kw for category in self.industry_keywords.values()
            for kw in category
        ]

    @staticmethod
    def _generate_human_readable_feedback(match_result, sections, quality) -> str:
        """Generate human-readable feedback"""
        feedback = []

        if match_result['score'] < 50:
            feedback.append("Your CV is missing many industry-standard keywords.")
        if not sections['experience']:
            feedback.append("Add work experience section.")
        if not sections['education']:
            feedback.append("Add Education section.")
        if not sections['certifications']:
            feedback.append("Add Certifications section.")
        if not sections['certifications']:
            feedback.append("Add Certifications section.")
        if not sections['languages']:
            feedback.append("Add Languages section.")
        if not sections['projects']:
            feedback.append("Add Projects section. [Optional]")
        if not sections['publications']:
            feedback.append("Add Publications section. [Optional]")
        if quality['verb_ratio'] < 20:
            feedback.append("Use more action verbs in descriptions.")
        return ' '.join(feedback) or "Looking good! Keep these suggestions in mind for future updates."


    async def _generate_feedback(
            self,
            combined_text: str,
            job_description: str
    ) -> str:
        """
        Generate actionable feedback by comparing candidate materials with job requirements
        Returns formatted feedback string with specific improvement suggestions
        """
        feedback = []

        try:
            # Keyword analysis
            job_keywords = await self.extract_keywords(job_description, top_n=50)
            cv_keywords = await self.extract_keywords(combined_text, top_n=50)
            missing_keywords = list(set(job_keywords) - set(cv_keywords))[:10]  # Top 10 missing

            if missing_keywords:
                feedback.append(
                    f"**Keyword Improvement**: Add these job-specific terms: "
                    f"{', '.join(missing_keywords)}"
                )

            # Section completeness check
            section_checks = self._analyze_sections_in_text(combined_text)
            missing_sections = [s for s, present in section_checks.items() if not present]
            if missing_sections:
                feedback.append(
                    f"**Content Structure**: Missing key sections - "
                    f"{', '.join(missing_sections).title()}"
                )

            # Action verb analysis
            verb_analysis = await self._analyze_action_verbs(combined_text)
            if verb_analysis['score'] < 0.2:
                feedback.append(
                    "**Writing Style**: Use more action verbs like "
                    f"{', '.join(verb_analysis['suggestions'])}"
                )

            # Readability score
            readability = await self._calculate_readability(combined_text)
            if readability < 50:
                feedback.append(
                    "**Readability**: Simplify complex sentences and reduce jargon"
                )

            # Keyword density check
            density = await self._calculate_keyword_density(combined_text, job_keywords)
            if density < 0.05:
                feedback.append(
                    "**Optimization**: Increase relevant keyword usage by 20-30%"
                )

        except Exception as e:
            self.logger.error(f"Feedback generation error: {str(e)}")
            return "We couldn't generate detailed feedback. Please check your input formats."

        return "\n\n".join(feedback) if feedback else "Great job! Your materials look well-optimized."

    @staticmethod
    def _analyze_sections_in_text(text: str) -> dict:
        """Check for presence of key sections in text"""
        return {
            'experience': bool(re.search(r'(experience|work\s+history)', text, re.I)),
            'education': bool(re.search(r'(education|qualifications)', text, re.I)),
            'skills': bool(re.search(r'(skills|technical\s+skills)', text, re.I))
        }

    async def _analyze_action_verbs(self, text: str) -> dict:
        """Analyze presence of action verbs"""
        doc = self.nlp(text.lower())
        found_verbs = [token.lemma_ for token in doc if token.lemma_ in ACTION_VERBS]

        return {
            'count': len(found_verbs),
            'score': len(found_verbs) / len(list(doc)) if doc else 0,
            'suggestions': list(ACTION_VERBS - set(found_verbs))[:3]
        }

    async def _calculate_readability(self, text: str) -> float:
        """Simple readability score (0-100) using Flesch-Kincaid approximation"""
        sentences = [sent for sent in self.nlp(text).sents]
        words = [token.text for token in self.nlp(text) if token.is_alpha]

        if not sentences or not words:
            return 0

        avg_sentence_length = len(words) / len(sentences)
        avg_word_length = sum(len(word) for word in words) / len(words)

        return max(0, min(100, 100 - (avg_sentence_length + avg_word_length * 3)))

    @staticmethod
    def _combine_cv_text_old(cv: JobSeekerCV) -> str:
        """Combine relevant CV sections for analysis"""
        sections = [
            cv.professional_title or "",
            cv.summary or "",
            ' '.join(cv.skills),
            ' '.join([exp.description for exp in cv.experience]),
            ' '.join([edu.field_of_study for edu in cv.education])
        ]
        return ' '.join(sections)
    #-----------------end of helper methods -----

    @staticmethod
    def _combine_cv_text(cv: JobSeekerCV) -> str:
        """Optimized CV text combiner for ATS analysis with validation"""
        sections = []

        # Core Identity - Using tuple unpacking for faster iteration
        title, summary, location = (
            cv.professional_title,
            cv.summary or "",
            cv.location or ""
        )
        if title or summary or location:
            sections.append(f"{title} {summary} {location}".strip())

        # Skills & Expertise - Pre-join lists to avoid multiple joins
        skills = ' '.join(cv.skills) if cv.skills else ""
        languages = ' '.join(l.language for l in cv.languages or [] if l.language)
        if skills or languages:
            sections.append(f"{skills} {languages}".strip())

        # Experience & Achievements - Generator expression for memory efficiency
        experience = ' '.join(
            f"{e.job_title} {e.company} {e.description}".strip()
            for e in cv.experience
            if e.job_title and e.company
        )
        if experience:
            sections.append(experience)

        # Education & Credentials - Filter incomplete entries
        education = ' '.join(
            f"{e.qualification} {e.field_of_study} {e.institution}".strip()
            for e in cv.education
            if e.qualification and e.institution
        )
        if education:
            sections.append(education)

        # Certifications - Validate complete entries
        certifications = ' '.join(
            f"{c.name} {c.issuer}"
            for c in cv.certifications or []
            if c.name and c.issuer  # Only include complete certifications
        )
        if certifications:
            sections.append(certifications)

        # Project Work - Fast string building
        projects = []
        for p in cv.projects or []:
            if p.title and p.description:
                proj_str = f"{p.title} {p.description}"
                if p.technologies:
                    proj_str += f" {' '.join(p.technologies)}"
                projects.append(proj_str.strip())
        if projects:
            sections.append(' '.join(projects))

        # Professional Recognition - Validate issuer/publisher
        awards = ' '.join(
            f"{a.title} {a.description} {a.issuer}".strip()
            for a in cv.awards or []
            if a.title and a.issuer
        )
        publications = ' '.join(
            f"{p.title} {p.publisher}".strip()
            for p in cv.publications or []
            if p.title and p.publisher
        )
        if awards or publications:
            sections.append(f"{awards} {publications}".strip())

        # Custom Content - Fast filtering
        custom = ' '.join(
            f"{s.title} {s.content}".strip()
            for s in cv.custom_sections or []
            if s.title and s.content
        )
        if custom:
            sections.append(custom)

        return ' '.join(filter(None, sections))

    @staticmethod
    async def _stream_pdf_text(file_stream) -> str:
        """Memory-efficient PDF text extraction"""
        text = []
        with fitz.open(stream=file_stream.read(), filetype="pdf") as doc:
            for page in doc:
                text.append(page.get_text())
        return "\n".join(text)


    async def _generate_single_report(self,job_id: str, job_description: str, cv: JobSeekerCV) -> ATSReport:
        """Generate ATS report for a single CV Based on Job Description"""
        self.set_industry_keywords(job_description)
        combined_text = self._combine_cv_text(cv)

        cv_ats_score = await self._calculate_ats_score(cv_text=combined_text, job_description=job_description)
        cv_matched_kw = await self._get_matched_keywords(combined_text=combined_text, job_description=job_description)
        cv_missing_kw = await self._get_missing_keywords(combined_text=combined_text, job_description=job_description)
        cv_feedback = await self._generate_feedback(combined_text, job_description)

        return ATSReport(**{
            'score': cv_ats_score,
            'cv_id': cv.cv_id,
            'job_id': job_id,
            'matched_keywords': cv_matched_kw,
            'missing_keywords': cv_missing_kw,
            'feedback': cv_feedback
        })


    async def _calculate_ats_score(self, cv_text: str, job_description: str) -> float:
        """Calculate ATS match score based on Text Input"""
        cv_keywords = await self.extract_keywords(cv_text)
        job_keywords = await self.extract_keywords(job_description)
        return (len(set(cv_keywords) & set(job_keywords)) / len(job_keywords)) * 100

    @error_handler
    async def _get_matched_keywords(self, combined_text: str, job_description: str) -> List[str]:
        """
        Identify matching keywords between candidate's materials and job description
        Returns sorted list of matched keywords for better readability
        """
        # Extract keywords with same parameters used in score calculation
        cv_keywords = await self.extract_keywords(combined_text, top_n=100)
        job_keywords = await self.extract_keywords(job_description, top_n=100)

        # Use set operations for efficient matching
        cv_set = set(cv_keywords)
        job_set = set(job_keywords)

        # Return alphabetically sorted matches
        return sorted(cv_set.intersection(job_set))

    @error_handler
    async def _get_missing_keywords(self,combined_text: str,job_description: str) -> List[str]:
        """
        Identify keywords present in job description but missing from candidate materials
        Returns sorted list of missing keywords by relevance
        """
        # Extract keywords with same parameters used for scoring
        cv_keywords = await self.extract_keywords(combined_text, top_n=100)
        job_keywords = await self.extract_keywords(job_description, top_n=100)

        # Convert to sets for efficient comparison
        cv_set = set(cv_keywords)
        job_set = set(job_keywords)

        # Calculate missing keywords and sort by original job description order
        missing_keywords = [kw for kw in job_keywords if kw in job_set - cv_set]

        return missing_keywords

    async def generate_industry_ats_report(self, cv: JobSeekerCV) -> dict:
        """Generate comprehensive ATS analysis report based on Industry Keywords"""
        try:
            # Extract combined keywords from multiple sections
            combined_text = self._combine_cv_text(cv)
            cv_keywords = await self.extract_keywords(combined_text, top_n=50)

            # Get keyword matches
            industry_keywords = self._flatten_keywords()
            match_result = await self.calculate_match_score(cv_keywords, industry_keywords)

            # Calculate section completeness
            section_completeness = self._analyze_sections(cv)

            # Generate quality insights
            quality_metrics = await self.get_resume_quality_insights(combined_text)

            # Generate human-readable feedback
            feedback = self._generate_human_readable_feedback(match_result, section_completeness, quality_metrics)

            return {
                'score': match_result['score'],
                'matched_keywords': match_result['matched_keywords'],
                'missing_keywords': match_result['missing_keywords'],
                'section_completeness': section_completeness,
                'quality_metrics': quality_metrics,
                'feedback': feedback
            }

        except Exception as e:
            return {
                'score': 0,
                'feedback': f"Error generating report: {str(e)}",
                'error': True
            }

    async def partial_ats_check(self, cv: JobSeekerCV) -> dict:
        """Quick ATS check for partial/incomplete CVs"""
        try:
            summary_keywords = await self.extract_keywords(cv.summary or "", top_n=15)
            industry_keywords = self._flatten_keywords()
            match_result = await self.calculate_match_score(summary_keywords, industry_keywords[:50])

            return {
                'score': match_result['score'],
                'matched_keywords': match_result['matched_keywords'],
                'missing_keywords': match_result['missing_keywords'][:5],
                'feedback': "Partial analysis based on summary only"
            }
        except Exception:
            return {'score': 0, 'feedback': "Quick analysis failed"}

    async def queue_ats_analysis(self, cv_id: str):
        """Simulated async analysis queue"""
        # In production, this would add to a task queue
        cv = await self.resume_controller.get_cv_by_id(cv_id)
        report = await self.generate_industry_ats_report(cv)
        self.cache_report(cv_id, report)

    def cache_report(self, cv_id: str, report: dict):
        """Simple in-memory cache (replace with Redis/Memcached)"""
        if not hasattr(self, '_report_cache'):
            self._report_cache = {}
        self._report_cache[cv_id] = report

    @error_handler
    async def clean_text(self, text: str) -> str:
        """Optimized text cleaning for CPU"""
        text = CLEAN_TEXT_PATTERN.sub('', text).lower()
        return ' '.join(text.split())

    @error_handler
    async def extract_keywords(self, text: str, top_n: Optional[int] = None, vectorizer_type: str = "count") -> list[str] | None:
        """Memory-efficient keyword extraction"""
        clean_text = await self.clean_text(text)
        top_n = top_n or self.top_n_keywords

        if vectorizer_type == "tfidf":
            vectorizer = TfidfVectorizer(stop_words='english', max_features=top_n)
        else:
            vectorizer = CountVectorizer(stop_words='english', max_features=top_n)

        try:
            matrix = vectorizer.fit_transform([clean_text])
            return vectorizer.get_feature_names_out().tolist()
        finally:
            del vectorizer  # Explicit cleanup

    @error_handler
    async def categorize_keywords(self, text: str) -> Dict[str, List[str]]:
        """CPU-optimized keyword categorization"""
        doc = self.nlp(text)
        categories = {
            "technical_skills": [],
            "action_verbs": [],
            "tools": [],
            "certifications": []
        }

        # Efficient pattern matching
        for token in doc:
            if token.pos_ == "VERB" and token.lemma_ in ACTION_VERBS:
                categories["action_verbs"].append(token.lemma_)
            elif token.pos_ == "NOUN" and token.is_alpha:
                categories["technical_skills"].append(token.text)

        # Simple pattern matching for certifications
        cert_patterns = [r'\bAWS\b', r'\bPMP\b', r'\bCCNA\b']
        categories["certifications"] = [
            match.group() for pattern in cert_patterns
            for match in re.finditer(pattern, text, re.IGNORECASE)
        ]

        return categories

    @error_handler
    async def extract_text(self, uploaded_file) -> str:
        """Memory-safe text extraction"""
        file_ext = os.path.splitext(uploaded_file.filename)[-1].lower()

        if file_ext == ".pdf":
            return await self._stream_pdf_text(uploaded_file)
        if file_ext in (".docx", ".doc"):
            return docx2txt.process(uploaded_file)
        return uploaded_file.read().decode('utf-8', errors='ignore')


    @error_handler
    async def calculate_match_score(self, resume_keywords: list[str], job_keywords: list[str]) -> Dict[str, float | list[str]]:
        """Optimized matching algorithm"""
        job_set = set(job_keywords[:100])  # Limit for performance
        resume_set = set(resume_keywords[:100])

        matched = job_set & resume_set
        score = (len(matched) / len(job_set)) * 100 if job_set else 0

        return {
            "score": round(score, 2),
            "matched_keywords": sorted(matched),
            "missing_keywords": sorted(job_set - resume_set)
        }

    @error_handler
    async def get_resume_quality_insights(self, text: str) -> Dict:
        """Optimized quality metrics"""
        words = text.split()
        action_verbs = [word for word in words if word.lower() in ACTION_VERBS]

        return {
            "word_count": len(words),
            "action_verbs": action_verbs,
            "verb_ratio": round(len(action_verbs) / len(words) * 100, 2) if words else 0
        }

    @error_handler
    async def handle_ats_match(self, request: Request) -> Dict:
        """Optimized main endpoint"""
        uploaded_file = request.files.get("resume")
        job_desc = request.form.get("job_description", "")

        if not uploaded_file:
            raise ValueError("Resume file required")

        resume_text: str = await self.extract_text(uploaded_file=uploaded_file)
        resume_keywords = await self.extract_keywords(text=resume_text)
        job_keywords = await self.extract_keywords(tex=job_desc)

        return await self.calculate_match_score(resume_keywords=resume_keywords, job_keywords=job_keywords)


    # Add to ATSToolController class

    async def _generate_basic_cover_letter(self, job: Job, cv: JobSeekerCV) -> str:
        """Generate a cover letter draft using CV and job details"""
        # Basic template-based implementation - extend with AI/NLP as needed
        template = f"""
        Dear Hiring Manager,
    
        I'm excited to apply for the {job.title} position at {job.company}. 
        With my {cv.years_experience} years of experience in {cv.primary_skill}, 
        I believe I would be a great fit for this role.
    
        In my previous role at {cv.most_recent_employer}, I:
        - {cv.key_achievements[0]}
        - {cv.key_achievements[1]}
        - {cv.key_achievements[2]}
    
        I'm particularly drawn to this position because {job.description[:100]}...
    
        Sincerely,
        {cv.full_name}
        """
        return await self._clean_cover_draft(template)


    # Add to ATSToolController class

    async def generate_cover_letter(
            self,
            job: Job,
            cv: JobSeekerCV,
            use_ai: bool = False,
            ai_config: Optional[dict] = None
    ) -> str:
        """
            Generate cover letter with optional AI enhancement
            :param use_ai: Premium feature flag
            :param ai_config: API keys/prompt customization
        """
        if use_ai:
            try:
                return await self._generate_ai_cover_letter(job, cv, ai_config or {})
            except Exception as e:
                self.logger.error(f"AI cover letter failed: {str(e)}")
                # Fall back to basic template
                return await self._generate_basic_cover_letter(job=job, cv=cv)

        return await self._generate_basic_cover_letter(job=job, cv=cv)

    async def _generate_ai_cover_letter(self, job: Job, cv: JobSeekerCV, config: dict) -> str:
        """Generate AI-powered cover letter using GPT"""
        prompt = self._create_ai_professional_cover_letter_prompt(job, cv)

        # Example using OpenAI API - implement your preferred AI service
        response = await self._call_ai_api(
            prompt=prompt,
            api_key=config.get('api_key'),
            model=config.get('model', 'gpt-4')
        )

        return await self._clean_cover_draft(response)

    @staticmethod
    def _create_ai_professional_cover_letter_prompt(job: Job, cv: JobSeekerCV) -> str:
        """Create structured prompt for AI generation"""
        return f"""
        Generate a professional cover letter for a job application with these details:

        Job Requirements:
        - Position: {job.title}
        - Company: {job.company}
        - Key Skills: {', '.join(job.required_skills)}
        - Description: {job.description[:1000]}

        Applicant Profile:
        - Name: {cv.full_name}
        - Experience: {cv.years_experience} years
        - Top Skills: {', '.join(cv.skills[:5])}
        - Recent Achievement: {cv.key_achievements[0] if cv.key_achievements else ''}

        Guidelines:
        - 3-4 concise paragraphs
        - Match company culture: {job.company_description[:500]}
        - Highlight relevant experience
        - Include specific metrics
        - Professional tone
        - Max 400 words
        """

    async def _call_ai_api(self, prompt: str, api_key: str, model: str = "deepseek-chat") -> str:
        """Call Deepseek API with proper formatting and error handling"""
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": model,
                "messages": [
                    {"role": "system",
                     "content": "You are a professional career advisor helping create a tailored cover letter."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1000,
                "top_p": 0.9,
                "frequency_penalty": 0.2
            }

            try:
                async with session.post(
                        "https://api.deepseek.com/v1/chat/completions",
                        json=data,
                        headers=headers,
                        timeout=10
                ) as response:
                    response.raise_for_status()
                    result = await response.json()

                    # Handle Deepseek's response format
                    return result['choices'][0]['message']['content'].strip()

            except aiohttp.ClientError as e:
                self.logger.error(f"Deepseek API connection error: {str(e)}")
                raise ConnectionError("Failed to connect to AI service")
            except KeyError as e:
                self.logger.error(f"Malformed Deepseek API response: {str(e)}")
                raise ValueError("Unexpected response format from AI service")
            except Exception as e:
                self.logger.error(f"Deepseek API error: {str(e)}")
                raise

    async def recommend_salary(
            self,
            job: Job,
            use_ai: bool = False,
            ai_config: Optional[dict] = None
    ) -> dict:
        """Generate salary recommendation with optional AI enhancement"""
        if use_ai and ai_config:
            try:
                return await self._generate_ai_salary(job, ai_config)
            except Exception as e:
                self.logger.error(f"AI salary recommendation failed: {str(e)}")
                # Fall back to basic calculation
                return self._basic_salary_recommendation(job)

        return self._basic_salary_recommendation(job)

    async def _generate_ai_salary(self, job: Job, config: dict) -> dict:
        """Get AI-powered salary recommendation using Deepseek"""
        prompt = self._create_salary_prompt(job)
        response = await self._call_ai_api(
            prompt=prompt,
            api_key=config.get('api_key'),
            model=config.get('model', 'deepseek-chat')
        )
        return self._parse_ai_salary_response(response)

    @staticmethod
    def _create_salary_prompt(job: Job) -> str:
        """Create structured prompt for salary recommendations"""
        return f"""
        Analyze this job posting and provide a salary recommendation in JSON format:

        Job Title: {job.title}
        Location: {job.location}
        Description: {job.description[:2000]}
        Required Skills: {', '.join(job.required_skills)}

        Consider these factors:
        - Industry standards for similar roles
        - Geographic location adjustments
        - Skill-specific premiums
        - Company size and funding stage

        Response format:
        {{
            "range": [min, max],
            "basis": "summary of factors",
            "currency": "ZAR/USD",
            "confidence": 0-100
        }}
        """

    def _parse_ai_salary_response(self, response: str) -> dict:
        """Parse and validate AI salary response"""
        try:
            # Extract JSON from markdown if present
            json_str = re.search(r'\{.*\}', response, re.DOTALL).group()
            data = json.loads(json_str)

            if not all(key in data for key in ['range', 'basis', 'currency']):
                raise ValueError("Missing required fields in AI response")

            # Validate number format
            if len(data['range']) != 2 or not all(isinstance(n, (int, float)) for n in data['range']):
                raise ValueError("Invalid salary range format")

            return {
                'range': [float(data['range'][0]), float(data['range'][1])],
                'basis': data['basis'],
                'currency': data['currency'],
                'confidence': data.get('confidence', 75),
                'source': 'AI Market Analysis'
            }
        except (json.JSONDecodeError, AttributeError, ValueError) as e:
            self.logger.error(f"Failed to parse AI salary response: {str(e)}")
            raise ValueError("Invalid AI salary response format")



    def _basic_salary_recommendation(self, job: Job) -> dict:
        """Improved fallback salary estimation with Configuration support."""

        # 1. Try to fetch a configuration salary range for this job category
        if job.category:
            config_key = f"salary_range:{job.search_term.lower().replace(' ', '_')}"  # e.g. "salary_range:software_engineer"
            with self.get_session() as session:
                config = session.query(ConfigurationORM).filter_by(type=config_key).first()

            if config:
                value = ConfigurationORM._cast_value(config.value, config.data_type)
                if isinstance(value, list) and len(value) == 2:
                    try:
                        low = float(value[0])
                        high = float(value[1])
                        return {
                            'range': [low, high],
                            'basis': f"Configured range for {job.category}",
                            'currency': 'ZAR',
                            'confidence': 95,
                            'source': 'Platform Configuration'
                        }
                    except (ValueError, TypeError):
                        self.logger.warning(f"Invalid configuration salary range for {job.category}: {value}")

        # 2. Use job.salary if available
        if job.salary and ',' in job.salary:
            try:
                salary_parts = [s.strip() for s in job.salary.split(',')]
                if len(salary_parts) == 2:
                    low = float(salary_parts[0].replace('$', '').replace(',', ''))
                    high = float(salary_parts[1].replace('$', '').replace(',', ''))

                    return {
                        'range': [low, high],
                        'basis': "Employer's listed salary range",
                        'currency': 'USD',
                        'confidence': 85,
                        'source': 'Job Posting Data'
                    }
            except (ValueError, TypeError) as e:
                self.logger.warning(f"Failed to parse salary '{job.salary}': {str(e)}")

        # 3. Fallback to experience-based estimate
        base_salaries = {
            'entry': (40000, 60000),
            'mid': (60000, 90000),
            'senior': (90000, 130000)
        }
        level = self._detect_experience_level(job.description)

        return {
            'range': base_salaries.get(level, (50000, 80000)),
            'basis': f"Market average for {level} positions",
            'currency': 'ZAR',
            'confidence': 65,
            'source': 'Basic Estimation'
        }

    def set_industry_keywords(self, job_description: str):
        """Dynamically set industry keywords based on job description"""
        # Enhanced implementation using NLP
        doc = self.nlp(job_description.lower())

        # Extract nouns and noun phrases as potential keywords
        self.industry_keywords = {
            'industry_specific': [chunk.text for chunk in doc.noun_chunks],
            'general_skills': ['communication', 'teamwork', 'problem solving']
        }

    async def evaluate_application(self, job: Job, cv_id: str, cover_letter: str) -> ATSReport:
        """Full ATS evaluation for an application"""
        cv = await self.resume_controller.get_cv_by_id(cv_id)
        self.set_industry_keywords(job.ats_description)

        # Combine CV and cover letter text
        combined_text: str = self._combine_cv_text(cv) + " " + cover_letter
        resume_keywords: list[str] = await self.extract_keywords(text=combined_text)

        # Calculate match score
        job_keywords: list[str] = await self.extract_keywords(text=job.ats_description)
        match_result = await self.calculate_match_score(resume_keywords=resume_keywords, job_keywords=job_keywords)
        feedback = await self._generate_feedback(combined_text=combined_text, job_description=job.ats_description)
        ats_report = ATSReport(
            job_id=job.job_id,
            cv_id=cv.cv_id,
            score= match_result['score'],
            matched_keywords=match_result['matched_keywords'],
            missing_keywords=match_result['missing_keywords'],
            feedback =feedback)

        return ats_report



    async def generate_cvs_job_description_ats_report(self,job_id: str, job_description: str, cvs: list[JobSeekerCV]) -> dict:
        """Generate comprehensive ATS report for multiple CVs"""
        best_score = 0
        best_report = {}
        ats_reports = []
        for cv in cvs:
            report: ATSReport = await self._generate_single_report(job_id, job_description, cv)
            ats_reports.append(report)
            if report.score > best_score:
                best_score = report.score
                best_report = report


        return best_report
