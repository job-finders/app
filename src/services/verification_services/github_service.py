import requests
from typing import Optional, Dict, Any
from datetime import datetime
import openai  # Assuming OpenAI GPT model for AI analysis

GITHUB_API_URL = "https://api.github.com"
OPENAI_API_KEY = "your_openai_api_key"

openai.api_key = OPENAI_API_KEY


class GitHubVerificationService:
    def __init__(self, github_token: str):
        self.github_token = github_token
        self.headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def get_user_profile(self, username: str) -> Optional[Dict[str, Any]]:
        url = f"{GITHUB_API_URL}/users/{username}"
        resp = requests.get(url, headers=self.headers)
        if resp.status_code == 200:
            return resp.json()
        return None

    def get_user_repos(self, username: str) -> Optional[list]:
        url = f"{GITHUB_API_URL}/users/{username}/repos?per_page=100"
        resp = requests.get(url, headers=self.headers)
        if resp.status_code == 200:
            return resp.json()
        return None

    def analyze_profile_with_ai(self, profile: dict, repos: list) -> Dict[str, Any]:
        # Construct a prompt with profile and repo summaries
        repo_names = [repo['name'] for repo in repos[:5]]
        repo_langs = list({repo.get('language') for repo in repos if repo.get('language')})
        bio = profile.get('bio', '')
        public_repos = profile.get('public_repos', 0)
        followers = profile.get('followers', 0)

        prompt = (
            f"Analyze this GitHub user profile for authenticity and activity.\n"
            f"Bio: {bio}\n"
            f"Public repos (sample): {repo_names}\n"
            f"Languages used: {repo_langs}\n"
            f"Public repos count: {public_repos}\n"
            f"Followers: {followers}\n\n"
            "Is this profile likely to be genuine and active? Rate confidence from 0 to 1 and explain briefly."
        )

        completion = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.3,
        )

        response = completion.choices[0].message['content'].strip()
        # Here you would parse the AI response more robustly; simplified:
        confidence = 0.5  # fallback
        explanation = response
        # parse confidence if formatted properly...

        return {
            "confidence_score": confidence,
            "explanation": explanation,
        }

    def verify_github(self, username: str) -> Dict[str, Any]:
        profile = self.get_user_profile(username)
        if not profile:
            return {"verified": False, "reason": "GitHub user not found"}

        repos = self.get_user_repos(username) or []

        ai_analysis = self.analyze_profile_with_ai(profile, repos)

        verified = ai_analysis.get("confidence_score", 0) > 0.7  # threshold
        return {
            "verified": verified,
            "github_profile_url": profile.get("html_url"),
            "public_repos": profile.get("public_repos"),
            "followers": profile.get("followers"),
            "ai_analysis": ai_analysis,
        }
