"""Module 6: PortfolioVerifier — Validates authenticity of claimed portfolio projects."""
import asyncio
import json
import logging
from typing import Dict, Any, List
from models import PortfolioResult # type: ignore
from llm_utils import initialize_llm_provider, extract_json_from_response, get_model_for_task, ReasoningIntensity # type: ignore
from prompt import DEFAULT_MODEL # type: ignore

logger = logging.getLogger("identity_trust.portfolio_verifier")


class PortfolioVerifier:
    """Validates portfolio authenticity using project metadata and LLM analysis.

    NOTE: Real URL crawling is not implemented. Uses project metadata for analysis.
    """

    def __init__(self):
        self.model_name = get_model_for_task(ReasoningIntensity.HIGH)
        self.provider = initialize_llm_provider(self.model_name)

    async def verify(self, profile: Dict[str, Any]) -> PortfolioResult:
        portfolio_url = profile.get("portfolio_url")
        resume_projects_data = profile.get("resume_projects", [])
        github_data = profile.get("github_data")

        if not github_data or not github_data.get("projects"):
            logger.info("No GitHub data available for cross-verification.")
            return PortfolioResult(
                portfolio_score=0.0,
                evidence_found=[],
                project_complexity="No external portfolio evidence found."
            )

        resume_projects = []
        for rp in resume_projects_data:
            if not rp:
                continue
            name = rp.get('name', 'Unknown')
            desc = rp.get('description', '')
            tech = rp.get('technologies', []) or []
            highlights = rp.get('highlights', []) or []
            rp_info = f"Name: {name}\nDescription: {desc}\nTech: {', '.join(tech)}\nHighlights: {', '.join(highlights)}"
            resume_projects.append(rp_info)



        gh_projects = github_data.get("projects", [])
        gh_summaries = []
        for p in gh_projects[:10]:
            owner = p.get('owner_login') or p.get('github_details', {}).get('owner_login', 'Unknown')
            commits = p.get('author_commit_count', 0)
            gh_info = f"Repo: {p.get('name', 'Unnamed')} (Owner: {owner})\nDescription: {p.get('description', 'None')}\nTech Stack: {', '.join(p.get('technologies', []))}\nAuthor Commits: {commits}"
            gh_summaries.append(gh_info)

        prompt = f"""You are an expert candidate verification agent. Your goal is to cross-verify every project listed in a candidate's resume against available online evidence (GitHub repositories, live deployments, portfolios, LinkedIn, etc.) to determine authenticity, completeness, and ownership. Follow these steps:

1. FOR EACH RESUME PROJECT:
   a. Match with GitHub repository:
      - Compare project names and descriptions.
      - Check tech stack and code files for alignment with resume claims.
      - Verify commit history and contribution ownership.
   b. Check for live evidence:
      - Look for deployed apps, live demos, or portfolio URLs.
   c. Semantic alignment:
      - Compare repo details with resume feature descriptions.
      - Highlight discrepancies or missing evidence.

2. AGGREGATE:
   - Generate an overall project verification report.
   - Suggest improvements for the resume or portfolio to maximize credibility.

Constraints:
- Be strict but fair: only verify what can be supported by evidence.
- Avoid assumptions; flag unverifiable claims clearly.

INPUT DATA:
--- Resume Projects ---
{chr(10).join(resume_projects) if resume_projects else 'None explicitly listed'}
--- GitHub Repositories (Evidence) ---
{chr(10).join(gh_summaries)}
--- Optional Links (Portfolios/Profiles) ---
Portfolio URL: {portfolio_url or 'None'}

Return ONLY a JSON object containing:
{{
    "portfolio_score": float (0-10, overall alignment/ownership score),
    "evidence_found": list of strings (Specific verified technical claims),
    "project_complexity": string (Summary of project technical difficulty),
    "oss_impact": string or null,
    "project_verification_report": string (Detailed markdown report formatted cleanly with Matched Repo, Ownership, Score (0-10), Confidence, and Notes for each project),
    "suggested_improvements": list of strings (Actionable advice for the candidate),
    "unverifiable_claims": list of strings (Resume claims lacking concrete evidence)
}}
"""

        try:
            chat_params = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "options": {"temperature": 0.2},
            }
            response = await asyncio.to_thread(self.provider.chat, **chat_params)
            text = extract_json_from_response(response["message"]["content"])
            analysis = json.loads(text, strict=False)

            return PortfolioResult(
                portfolio_score=float(analysis.get("portfolio_score", 5.0)),
                evidence_found=list(analysis.get("evidence_found", [])),
                project_complexity=str(analysis.get("project_complexity", "Moderate")),
                oss_contribution_impact=analysis.get("oss_impact"),
                project_verification_report=str(analysis.get("project_verification_report", "")),
                suggested_improvements=list(analysis.get("suggested_improvements", [])),
                unverifiable_claims=list(analysis.get("unverifiable_claims", []))
            )
        except Exception as e:
            logger.error(f"PortfolioVerifier error: {e}")
            return PortfolioResult(
                portfolio_score=5.0,
                evidence_found=["See GitHub for details"],
                project_complexity="Could not analyze complexity via LLM"
            )

