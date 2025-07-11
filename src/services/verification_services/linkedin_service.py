import requests
import logging
from typing import Dict

# Optional: Use OpenAI if you're piping into GPT
import openai

# === CONFIG ===
LINKEDIN_CLIENT_ID = "your_client_id"
LINKEDIN_CLIENT_SECRET = "your_client_secret"
LINKEDIN_REDIRECT_URI = "https://yourapp.com/oauth/linkedin/callback"

OPENAI_API_KEY = "sk-..."  # Only if you're using OpenAI for the AI model
openai.api_key = OPENAI_API_KEY

# === SERVICE ===

class LinkedInVerifier:
    def __init__(self):
        self.token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        self.profile_url = "https://api.linkedin.com/v2/me"
        self.email_url = "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))"

    def exchange_code_for_token(self, code: str) -> str:
        response = requests.post(self.token_url, data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": LINKEDIN_REDIRECT_URI,
            "client_id": LINKEDIN_CLIENT_ID,
            "client_secret": LINKEDIN_CLIENT_SECRET
        })
        response.raise_for_status()
        return response.json().get("access_token")

    def fetch_linkedin_profile(self, token: str) -> Dict:
        headers = {"Authorization": f"Bearer {token}"}

        profile_resp = requests.get(self.profile_url, headers=headers)
        email_resp = requests.get(self.email_url, headers=headers)

        profile = profile_resp.json()
        email = email_resp.json().get("elements", [{}])[0].get("handle~", {}).get("emailAddress")

        return {
            "first_name": profile.get("localizedFirstName"),
            "last_name": profile.get("localizedLastName"),
            "headline": profile.get("headline", {}).get("localized", {}).get("en_US", "N/A"),
            "email": email
        }

    def verify_with_ai(self, profile_data: Dict) -> Dict:
        prompt = self._build_verification_prompt(profile_data)

        # You can replace this with your own LLM call or API
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional LinkedIn profile evaluator."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        ai_output = response.choices[0].message.content
        return self._parse_ai_response(ai_output)

    def _build_verification_prompt(self, profile: Dict) -> str:
        return f"""
You're an AI assistant verifying LinkedIn profiles.

Profile details:
- First Name: {profile.get('first_name')}
- Last Name: {profile.get('last_name')}
- Headline: {profile.get('headline')}
- Email: {profile.get('email')}

Evaluate if this LinkedIn profile appears authentic and relevant for a professional user. Return a JSON with:

- verified: true | false
- confidence_score: float (0.0 - 1.0)
- reason: short explanation

Only return JSON.

If the profile is incomplete or suspicious (no headline, fake name, etc.), return verified: false with reasoning.
"""

    def _parse_ai_response(self, text: str) -> Dict:
        try:
            import json
            return json.loads(text.strip())
        except Exception:
            logging.warning("Could not parse AI response.")
            return {
                "verified": False,
                "confidence_score": 0.0,
                "reason": "AI response was malformed or missing."
            }

    def run_verification(self, code: str) -> Dict:
        try:
            token = self.exchange_code_for_token(code)
            profile = self.fetch_linkedin_profile(token)
            result = self.verify_with_ai(profile)

            return {
                "profile": profile,
                "verification": result
            }

        except Exception as e:
            logging.exception("LinkedIn verification failed.")
            return {
                "error": str(e),
                "verified": False
            }
