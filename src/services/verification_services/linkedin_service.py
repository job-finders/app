import logging
from typing import Dict, Optional, List
from pydantic import BaseModel

import httpx
from src.agents.openrouter_client import call_openrouter

# Config
LINKEDIN_CLIENT_ID = "your_client_id"
LINKEDIN_CLIENT_SECRET = "your_client_secret"
LINKEDIN_REDIRECT_URI = "https://yourapp.com/oauth/linkedin/callback"


class LinkedInProfile(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    headline: Optional[str]
    email: Optional[str]


class LinkedInVerificationResult(BaseModel):
    verified: bool
    confidence_score: float
    reason: str


class LinkedInVerifier:
    """
    Asynchronous LinkedIn verification service.
    - OAuth2 token exchange
    - Fetch user profile & email
    - Evaluate using AI model
    """

    def __init__(self):
        self.token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        self.profile_url = "https://api.linkedin.com/v2/me"
        self.email_url = (
            "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))"
        )

    async def exchange_code_for_token(self, code: str) -> str:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": LINKEDIN_REDIRECT_URI,
            "client_id": LINKEDIN_CLIENT_ID,
            "client_secret": LINKEDIN_CLIENT_SECRET,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_url, data=data)
            response.raise_for_status()
            return response.json().get("access_token")

    async def fetch_linkedin_profile(self, token: str) -> LinkedInProfile:
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            profile_resp = await client.get(self.profile_url, headers=headers)
            email_resp = await client.get(self.email_url, headers=headers)

        profile_data = profile_resp.json()
        email_data = email_resp.json()
        email = email_data.get("elements", [{}])[0].get("handle~", {}).get("emailAddress")

        return LinkedInProfile(
            first_name=profile_data.get("localizedFirstName"),
            last_name=profile_data.get("localizedLastName"),
            headline=profile_data.get("headline", {}).get("localized", {}).get("en_US"),
            email=email,
        )

    async def verify_with_ai(self, profile: LinkedInProfile) -> LinkedInVerificationResult:
        messages: List[Dict[str, str]] = [
            {
                "role": "system",
                "content": "You are a professional LinkedIn profile evaluator.",
            },
            {
                "role": "user",
                "content": self._build_verification_prompt(profile),
            },
        ]

        # noinspection PyTypeChecker
        result: LinkedInVerificationResult = await call_openrouter(
            messages=messages,
            output_model=LinkedInVerificationResult,
            model="deepseek-chat",
            temperature=0.2,
            max_tokens=512,
        )

        return result

    @staticmethod
    def _build_verification_prompt(profile: LinkedInProfile) -> str:
        return f"""
                You're an AI assistant verifying LinkedIn profiles.

                Profile details:
                - First Name: {profile.first_name}
                - Last Name: {profile.last_name}
                - Headline: {profile.headline}
                - Email: {profile.email}

                Evaluate if this LinkedIn profile appears authentic and relevant for a professional user. Return a JSON with:

                - verified: true | false
                - confidence_score: float (0.0 - 1.0)
                - reason: short explanation

                Only return JSON.

                If the profile is incomplete or suspicious (e.g. no headline, fake name, etc.), return verified: false with reasoning.
                """

    async def run_verification(self, code: str) -> Dict:
        """
        Exchange auth code, fetch profile, and return verification.

        Args:
            code (str): LinkedIn OAuth2 code

        Returns:
            Dict: Profile data + AI verification result or error
        """
        try:
            token = await self.exchange_code_for_token(code)
            profile = await self.fetch_linkedin_profile(token)
            result = await self.verify_with_ai(profile)

            return {
                "profile": profile.dict(),
                "verification": result.dict(),
            }

        except Exception as e:
            logging.exception("LinkedIn verification failed.")
            return {
                "error": str(e),
                "verified": False,
            }
