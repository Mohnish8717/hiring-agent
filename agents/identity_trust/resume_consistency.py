"""Module 5: ResumeConsistencyChecker — Detects inconsistencies between resume and external data."""
import asyncio
import json
import logging
from typing import Dict, Any, List
from models import ResumeConsistencyResult # type: ignore
from llm_utils import initialize_llm_provider, extract_json_from_response, get_model_for_task, ReasoningIntensity # type: ignore
from prompt import DEFAULT_MODEL # type: ignore

logger = logging.getLogger("identity_trust.resume_consistency")


class ResumeConsistencyChecker:
    """Compares resume claims against LinkedIn and GitHub data using LLM reasoning."""

    def __init__(self):
        self.model_name = get_model_for_task(ReasoningIntensity.HIGH)
        self.provider = initialize_llm_provider(self.model_name)

    async def check(self, profile: Dict[str, Any], github_data: Dict[str, Any] | None) -> ResumeConsistencyResult:
        experience = profile.get("resume_experience", [])
        skills = profile.get("resume_skills", [])
        projects = profile.get("resume_projects", [])

        if not experience and not skills:
            return ResumeConsistencyResult()

        # Build GitHub context
        gh_languages: List[str] = []
        gh_repos: List[str] = []
        if github_data:
            for p in github_data.get("projects", []):
                gh_repos.append(p.get("name", ""))
                gh_languages.extend(p.get("technologies", []))

        prompt = f"""You are the ResumeConsistencyChecker agent.
Compare resume information with external profile signals.

Resume Experience (last 5):
{json.dumps(experience[:5], default=str)}

Resume Skills: {', '.join(skills)}

Resume Projects: {json.dumps(projects[:5], default=str)}

GitHub Languages: {', '.join(set(gh_languages))}
GitHub Repositories: {', '.join(gh_repos[:10])}

Check:
1. Work timeline consistency (gaps, overlapping roles, realistic progressions)
2. Skill alignment (do GitHub languages match resume skills?)
3. Project alignment (do GitHub repos match resume projects?)

Return ONLY a JSON object:
{{
    "timeline_consistency_score": float (0-10),
    "experience_consistency_score": float (0-10),
    "skill_consistency_score": float (0-10)
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

            return ResumeConsistencyResult(
                timeline_consistency_score=float(data.get("timeline_consistency_score", 5.0)),
                experience_consistency_score=float(data.get("experience_consistency_score", 5.0)),
                skill_consistency_score=float(data.get("skill_consistency_score", 5.0)),
            )
        except Exception as e:
            logger.error(f"ResumeConsistencyChecker error: {e}")
            return ResumeConsistencyResult(
                timeline_consistency_score=5.0,
                experience_consistency_score=5.0,
                skill_consistency_score=5.0,
            )
