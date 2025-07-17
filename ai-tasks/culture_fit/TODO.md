# Company Culture Fit Module – Development Plan

## 🔧 Milestone 1: Setup & Scaffolding
- [ ] Create new route/module: `culture-fit/`
- [ ] Add new DB models (see below)
- [ ] Setup basic UI component layout for:
  - Company Culture Definition Form
  - Questionnaire Builder
  - Jobseeker Response UI
  - Culture Fit Results Page

## ✍️ Milestone 2: Company Culture Definition
- [ ] Allow companies to define values, mission, work style, and expectations
- [ ] Include AI-assisted culture document generator (OpenAI integration or local model)
- [ ] Save culture definitions per `CompanyProfile`

## 🧩 Milestone 3: Questionnaire System
- [ ] Questionnaire builder interface for companies
- [ ] Support:
  - Multiple question types (MCQ, Likert scale, open-ended)
  - Tagging questions by cultural trait (e.g., "collaboration", "independence")
- [ ] Save questionnaires per company

## 🧠 Milestone 4: Culture Fit Evaluation (AI/Logic Layer)
- [ ] Implement AI-based analysis:
  - Analyze jobseeker answers vs. company cultural definitions
  - Score and categorize matches
- [ ] Algorithm must return:
  - Match % score
  - Matched traits
  - Potential conflicts
- [ ] Option to give feedback or advice to jobseeker (generated via AI)

## 👀 Milestone 5: Display + Admin
- [ ] Show jobseeker results with explanation
- [ ] Employer dashboard: overview of applicant fit
- [ ] API endpoints for external use

## 🧪 Milestone 6: Testing & Feedback
- [ ] Add validation + test coverage
- [ ] Collect beta feedback from employers & jobseekers

## 📦 Future Ideas
- [ ] Culture Fit Leaderboard per job role
- [ ] Integrate with existing Job Matching system
- [ ] Detect contradictions in company culture via AI
- [ ] Career coaching tools for seekers
