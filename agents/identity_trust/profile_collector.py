"""Module 1: ProfileCollector — Builds a unified candidate identity profile."""
import logging
from typing import Dict, Any, Optional, List
from models import JSONResume # type: ignore

logger = logging.getLogger("identity_trust.profile_collector")


class ProfileCollector:
    """Collects and normalizes all identity-related information into a unified profile."""

    def collect(self, resume_data: Optional[JSONResume], github_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build a unified candidate identity profile from resume and external data.

        Returns:
            candidate_identity_profile dict
        """
        profile: Dict[str, Any] = {
            "name": None,
            "email": None,
            "phone": None,
            "linkedin_url": None,
            "github_url": None,
            "portfolio_url": None,
            "resume_skills": [],
            "resume_experience": [],
            "resume_projects": [],
            "github_data": github_data,
        }

        if not resume_data:
            logger.warning("No resume data provided to ProfileCollector")
            return profile

        # --- Extract identity fields from resume basics ---
        basics = resume_data.basics
        if basics:
            profile["name"] = basics.name
            profile["email"] = basics.email
            profile["phone"] = basics.phone

            # Normalize social URLs
            if basics.profiles:
                for p in basics.profiles:
                    network = (p.network or "").lower()
                    url = p.url or ""
                    if network == "github":
                        profile["github_url"] = self._normalize_url(url)
                    elif network == "linkedin":
                        profile["linkedin_url"] = self._normalize_url(url)
                    elif network in ("portfolio", "website"):
                        profile["portfolio_url"] = self._normalize_url(url)

            # Fallback: check basics.url for portfolio
            if not profile["portfolio_url"] and basics.url:
                profile["portfolio_url"] = self._normalize_url(basics.url)

        # --- Skills ---
        if resume_data.skills:
            profile["resume_skills"] = [s.name for s in resume_data.skills if s.name]

        # --- Experience ---
        if resume_data.work:
            profile["resume_experience"] = [
                {
                    "company": w.name or "",
                    "position": w.position or "",
                    "start": w.startDate or "",
                    "end": w.endDate or "",
                    "summary": w.summary or "",
                }
                for w in resume_data.work
            ]

        # --- Projects ---
        if resume_data.projects:
            profile["resume_projects"] = [
                {
                    "name": proj.name or "",
                    "description": proj.description or "",
                    "url": proj.url or "",
                    "technologies": getattr(proj, "technologies", []) or [],
                    "highlights": getattr(proj, "highlights", []) or [],
                }
                for proj in resume_data.projects
            ]


        logger.info(f"ProfileCollector: built profile for {profile['name'] or 'Unknown'}")
        return profile

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Ensure URL has scheme and strip trailing slashes."""
        url = url.strip().rstrip("/")
        if url and not url.startswith(("http://", "https://")):
            url = "https://" + url
        return url
