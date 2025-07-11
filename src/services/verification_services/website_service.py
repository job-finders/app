import requests
import socket
import openai
from typing import Dict

# === CONFIG ===
OPENAI_API_KEY = "sk-..."  # Replace with actual API key
openai.api_key = OPENAI_API_KEY


class WebsiteVerifier:
    """sumary_line
        TODO - should use the http-service to fetch the website content
        TODO - should use the open_router service to evaluate the content
    Keyword arguments:
    argument -- description
    Return: return_description
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})

    def verify(self, url: str) -> Dict:
        """sumary_line

            Call this method to verify a website's legitimacy and professionalism.

        Keyword arguments:
        argument -- description
        Return: return_description
        """
        
        # Step 1: Basic domain check
        if not self._is_domain_reachable(url):
            return {
                "verified": False,
                "confidence_score": 0.0,
                "reason": "Domain is unreachable or invalid."
            }

        # Step 2: Fetch homepage content
        try:
            html = self._fetch_website_content(url)
        except Exception:
            return {
                "verified": False,
                "confidence_score": 0.0,
                "reason": "Website failed to load or timed out."
            }

        # Step 3: AI-based content verification
        return self._evaluate_with_ai(url, html)

    def _is_domain_reachable(self, url: str) -> bool:
        try:
            domain = url.split("//")[-1].split("/")[0]
            socket.gethostbyname(domain)
            return True
        except socket.error:
            return False

    def _fetch_website_content(self, url: str) -> str:
        response = self.session.get(url, timeout=6)
        response.raise_for_status()
        return response.text[:8000]  # Limit to 8K chars for AI prompt

    def _evaluate_with_ai(self, url: str, html: str) -> Dict:
        prompt = f"""
                    You are an AI verifier reviewing a website for professionalism and credibility.

                    Evaluate the following homepage HTML and return whether this appears to be a legitimate, professional website that clearly represents a real person, company, or project.

                    Respond in JSON format like this:
                    {{
                    "verified": true/false,
                    "confidence_score": float between 0.0 and 1.0,
                    "reason": "Brief explanation"
                    }}

                    Website URL: {url}
                    Homepage HTML sample:
                    {html}
                """

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "system", "content": "You are a website verification AI."},
                          {"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.5
            )
            result = response.choices[0].message.content.strip()
            return eval(result)  # Convert string to dict
        except Exception as e:
            return {
                "verified": False,
                "confidence_score": 0.0,
                "reason": f"AI evaluation failed: {str(e)}"
            }
