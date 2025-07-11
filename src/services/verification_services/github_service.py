import logging
from typing import List, Dict, Optional

from pydantic import BaseModel
import httpx

from src.agents.openrouter_client import call_openrouter

GITHUB_API_URL = "https://api.github.com"


class GitHubProfile(BaseModel):
    login: str
    bio: Optional[str]
    html_url: Optional[str]
    public_repos: int
    followers: int


class GitHubRepo(BaseModel):
    name: str
    language: Optional[str]
    stargazers_count: int
    forks_count: int
    pushed_at: Optional[str]


class GitHubVerificationResult(BaseModel):
    verified: bool
    confidence_score: float
    explanation: str


class GitHubVerifier:
    def __init__(self, github_token: str):
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github+json",
        }

    async def fetch_user_profile(self, username: str) -> Optional[GitHubProfile]:
        url = f"{GITHUB_API_URL}/users/{username}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code == 200:
                data = resp.json()
                return GitHubProfile(
                    login=data["login"],
                    bio=data.get("bio"),
                    html_url=data.get("html_url"),
                    public_repos=data.get("public_repos", 0),
                    followers=data.get("followers", 0),
                )
        return None

    async def fetch_user_repos(self, username: str) -> List[GitHubRepo]:
        url = f"{GITHUB_API_URL}/users/{username}/repos?per_page=100&sort=updated"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code == 200:
                return [
                    GitHubRepo(
                        name=repo["name"],
                        language=repo.get("language"),
                        stargazers_count=repo.get("stargazers_count", 0),
                        forks_count=repo.get("forks_count", 0),
                        pushed_at=repo.get("pushed_at"),
                    )
                    for repo in resp.json()
                ]
        return []

    async def verify_with_ai(self, profile: GitHubProfile, repos: List[GitHubRepo]) -> GitHubVerificationResult:
        top_repos = sorted(repos, key=lambda r: r.stargazers_count, reverse=True)[:5]
        repo_summaries = [
            f"{r.name} (Lang: {r.language or 'N/A'}, Stars: {r.stargazers_count}, Last Push: {r.pushed_at or 'N/A'})"
            for r in top_repos
        ]
        languages = sorted({r.language for r in repos if r.language})

        prompt = self._build_prompt(profile, repo_summaries, languages)

        # noinspection PyTypeChecker
        result: GitHubVerificationResult = await call_openrouter(
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI evaluating GitHub profile authenticity and activity.",
                },
                {"role": "user", "content": prompt},
            ],
            output_model=GitHubVerificationResult,
            model="gpt-4o",
            temperature=0.3,
            max_tokens=500,
        )

        return result

    @staticmethod
    def _build_prompt(
            profile: GitHubProfile, repo_summaries: List[str], languages: List[str]
    ) -> str:
        return f"""
            Analyze the following GitHub user profile for authenticity and active usage.

            Profile:
            - Username: {profile.login}
            - Bio: {profile.bio or 'N/A'}
            - Public Repos: {profile.public_repos}
            - Followers: {profile.followers}

            Top Repositories:
            {chr(10).join(repo_summaries) or 'None'}

            Languages Used: {", ".join(languages) or 'N/A'}

            Return a JSON object:
            - verified: true | false
            - confidence_score: float (0.0 - 1.0)
            - explanation: short reasoning

            Only return valid JSON.
            """

    async def run_verification(self, username: str) -> Dict:
        try:
            profile = await self.fetch_user_profile(username)
            if not profile:
                return {"verified": False, "reason": "GitHub user not found"}

            repos = await self.fetch_user_repos(username)
            result = await self.verify_with_ai(profile, repos)

            return {
                "verified": result.verified,
                "github_profile_url": profile.html_url,
                "public_repos": profile.public_repos,
                "followers": profile.followers,
                "ai_analysis": result.dict(),
            }

        except Exception as e:
            logging.exception("GitHub verification failed.")
            return {
                "error": str(e),
                "verified": False,
            }
