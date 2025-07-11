from typing import Dict, Any, List, Optional
import socket
from pydantic import BaseModel
from src.services.http_service import HttpRequestService
from src.agents.openrouter_client import call_openrouter


class WebsiteVerificationResult(BaseModel):
    verified: bool
    confidence_score: float
    reason: str


class WebsiteVerifier:
    """
    Asynchronous service to verify the professionalism and legitimacy of a website.

    - Checks DNS reachability.
    - Fetches homepage HTML using async HTTP service.
    - Evaluates content via OpenRouter AI model.
    """

    def __init__(self, http_service: Optional[HttpRequestService] = None):
        self.http_service = http_service or HttpRequestService()

    async def verify(self, url: str) -> Dict[str, Any]:
        """
        Asynchronously verify a website using HTTP and AI-based evaluation.

        Args:
            url (str): Full website URL.

        Returns:
            Dict[str, Any]: {
                verified: bool,
                confidence_score: float,
                reason: str
            }
        """
        if not self._is_domain_reachable(url):
            return WebsiteVerificationResult(
                verified=False,
                confidence_score=0.0,
                reason="Domain is unreachable or invalid."
            ).dict()

        try:
            html = await self._fetch_website_content(url)
        except Exception as e:
            return WebsiteVerificationResult(
                verified=False,
                confidence_score=0.0,
                reason=f"Website failed to load: {str(e)}"
            ).dict()

        try:
            return await self._evaluate_with_ai(url, html)
        except Exception as e:
            return WebsiteVerificationResult(
                verified=False,
                confidence_score=0.0,
                reason=f"AI evaluation failed: {str(e)}"
            ).dict()

    def _is_domain_reachable(self, url: str) -> bool:
        """
        Check DNS resolution for the domain in the URL.

        Args:
            url (str): Website URL

        Returns:
            bool: True if domain resolves
        """
        try:
            domain = url.split("//")[-1].split("/")[0]
            socket.gethostbyname(domain)
            return True
        except socket.error:
            return False

    async def _fetch_website_content(self, url: str) -> str:
        """
        Asynchronously fetch HTML content using HttpRequestService.

        Args:
            url (str): Website URL

        Returns:
            str: Truncated HTML (max 8000 chars)
        """
        response = await self.http_service.async_get(url)
        return response.text[:8000]

    async def _evaluate_with_ai(self, url: str, html: str) -> Dict[str, Any]:
        """
        Run the AI model to verify the content of the website.

        Args:
            url (str): The website URL
            html (str): Homepage HTML sample

        Returns:
            Dict[str, Any]: AI-evaluated verification response
        """
        messages: List[Dict[str, str]] = [
            {
                "role": "system",
                "content": "You are an AI verifier that checks websites for legitimacy and professionalism."
            },
            {
                "role": "user",
                "content": self._build_prompt(url, html)
            }
        ]

        result: WebsiteVerificationResult = await call_openrouter(
            messages=messages,
            output_model=WebsiteVerificationResult,
            model="deepseek-chat",
            temperature=0.5,
            max_tokens=800
        )

        return result.dict()

    def _build_prompt(self, url: str, html: str) -> str:
        """
        Construct the full user prompt for the AI.

        Args:
            url (str): Website URL
            html (str): HTML content of homepage

        Returns:
            str: Prompt string
        """
        return f"""
                Evaluate the following website HTML to determine if it is a professional, legitimate, and credible site.

                Respond strictly in JSON using the following structure:
                {{
                "verified": true or false,
                "confidence_score": float between 0.0 and 1.0,
                "reason": "brief explanation"
                }}

                Website URL: {url}
                HTML:
                ```html
                {html}
                ```
                Ensure the response is valid JSON and does not contain any additional text.
                """

