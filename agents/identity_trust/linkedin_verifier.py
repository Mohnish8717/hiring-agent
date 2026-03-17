"""Module 2: LinkedInVerifier — Estimates LinkedIn profile credibility via LLM heuristics."""
import asyncio
import json
import logging
from typing import Dict, Any
from models import LinkedInVerificationResult # type: ignore
from llm_utils import initialize_llm_provider, extract_json_from_response, get_model_for_task, ReasoningIntensity # type: ignore
from prompt import DEFAULT_MODEL # type: ignore

logger = logging.getLogger("identity_trust.linkedin_verifier")


class LinkedInVerifier:
    """Estimates LinkedIn credibility using LLM-based heuristic analysis.

    NOTE: Real LinkedIn API integration is not available. This module uses
    resume data and LLM reasoning to simulate LinkedIn credibility estimation.
    """

    def __init__(self):
        self.model_name = get_model_for_task(ReasoningIntensity.HIGH)
        self.provider = initialize_llm_provider(self.model_name)

    async def verify(self, profile: Dict[str, Any]) -> LinkedInVerificationResult:
        linkedin_url = profile.get("linkedin_url")
        name = profile.get("name", "Unknown")
        experience = profile.get("resume_experience", [])

        if not linkedin_url:
            logger.info(f"No LinkedIn URL for {name}, skipping verification")
            return LinkedInVerificationResult(
                linkedin_profile_score=0.0,
                linkedin_resume_consistency_score=0.0,
                linkedin_network_strength="No LinkedIn URL provided",
            )

        prompt = f"""You are the LinkedInVerifier agent.
Evaluate the credibility of a candidate's LinkedIn profile.

Candidate name: {name}
LinkedIn URL: {linkedin_url}
Resume experience summary: {json.dumps(experience[:5], default=str)}

Since you cannot access LinkedIn directly, estimate credibility based on:
1. Whether the LinkedIn URL looks legitimate (custom vanity URL vs random string)
2. Whether the resume experience looks consistent and professional
3. Profile maturity signals based on career timeline length
4. Estimated network strength based on seniority and company quality

Return ONLY a JSON object:
{{
    "linkedin_profile_score": float (0-10),
    "linkedin_resume_consistency_score": float (0-10),
    "linkedin_network_strength": string ("Weak" / "Moderate" / "Strong" / "Very Strong")
}}"""

        try:
            chat_params = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "options": {"temperature": 0.2},
            }
            response = await asyncio.to_thread(self.provider.chat, **chat_params)
            text = extract_json_from_response(response["message"]["content"])
            data = json.loads(text)

            return LinkedInVerificationResult(
                linkedin_profile_score=float(data.get("linkedin_profile_score", 5.0)),
                linkedin_resume_consistency_score=float(data.get("linkedin_resume_consistency_score", 5.0)),
                linkedin_network_strength=str(data.get("linkedin_network_strength", "Unknown")),
            )
        except Exception as e:
            logger.error(f"LinkedInVerifier error: {e}")
            return LinkedInVerificationResult(
                linkedin_profile_score=5.0,
                linkedin_resume_consistency_score=5.0,
                linkedin_network_strength="Error during verification",
            )
