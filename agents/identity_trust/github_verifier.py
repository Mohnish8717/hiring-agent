"""Module 3: GitHubVerifier — Verifies technical authenticity through GitHub activity."""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from models import GitHubVerificationResult # type: ignore

logger = logging.getLogger("identity_trust.github_verifier")


class GitHubVerifier:
    """Verifies candidate's technical authenticity using real GitHub data
    already fetched by the verification_agent pipeline."""

    def verify(self, profile: Dict[str, Any]) -> GitHubVerificationResult:
        github_data: Optional[Dict[str, Any]] = profile.get("github_data")
        resume_skills: List[str] = profile.get("resume_skills", [])

        if not github_data:
            logger.info("No GitHub data available, returning default scores")
            return GitHubVerificationResult(
                github_activity_score=0.0,
                open_source_credibility_score=0.0,
                repo_authenticity_score=0.0,
            )

        gh_profile = github_data.get("profile", {})
        projects: List[Dict[str, Any]] = github_data.get("projects", [])

        # --- 1. Activity Score ---
        activity_score = self._score_activity(gh_profile, projects)

        # --- 2. Open Source Credibility ---
        oss_score = self._score_oss_credibility(gh_profile, projects)

        # --- 3. Repo Authenticity (detect forks claimed as original) ---
        auth_score = self._score_repo_authenticity(projects, resume_skills)

        logger.info(
            f"GitHubVerifier: activity={activity_score:.1f}, oss={oss_score:.1f}, auth={auth_score:.1f}"
        )
        return GitHubVerificationResult(
            github_activity_score=activity_score,
            open_source_credibility_score=oss_score,
            repo_authenticity_score=auth_score,
        )

    def _score_activity(self, gh_profile: Dict, projects: List[Dict]) -> float:
        """Score based on account age, repo count, stars, commit frequency."""
        score = 5.0  # baseline

        # Account age
        created_at_str = gh_profile.get("created_at", "")
        if created_at_str:
            try:
                created = datetime.strptime(created_at_str, "%Y-%m-%dT%H:%M:%SZ")
                age_years = (datetime.utcnow() - created).days / 365.0
                if age_years >= 5:
                    score += 2.0
                elif age_years >= 2:
                    score += 1.0
                elif age_years < 0.5:
                    score -= 1.0
            except Exception:
                pass

        # Repo count
        repo_count = gh_profile.get("public_repos", 0)
        if isinstance(repo_count, int):
            if repo_count >= 20:
                score += 1.5
            elif repo_count >= 10:
                score += 1.0
            elif repo_count < 3:
                score -= 1.0

        # Stars across projects
        total_stars = sum(p.get("stars", 0) for p in projects if isinstance(p.get("stars"), int))
        if total_stars >= 50:
            score += 1.5
        elif total_stars >= 10:
            score += 0.5

        return max(0.0, min(10.0, score))

    def _score_oss_credibility(self, gh_profile: Dict, projects: List[Dict]) -> float:
        """Evaluate open source contribution depth."""
        score = 4.0

        followers = gh_profile.get("followers", 0)
        if isinstance(followers, int):
            if followers >= 100:
                score += 2.0
            elif followers >= 20:
                score += 1.0

        # Check for meaningful descriptions and diverse tech
        described_repos = sum(1 for p in projects if p.get("description"))
        if described_repos >= 5:
            score += 1.5
        elif described_repos >= 2:
            score += 0.5

        techs = set()
        for p in projects:
            for t in p.get("technologies", []):
                techs.add(t.lower() if isinstance(t, str) else "")
        if len(techs) >= 5:
            score += 1.0

        return max(0.0, min(10.0, score))

    def _score_repo_authenticity(self, projects: List[Dict], resume_skills: List[str]) -> float:
        """Detect forked repos presented as original, skill alignment."""
        score = 7.0

        forked_count = sum(1 for p in projects if p.get("fork", False))
        total = len(projects) if projects else 1
        fork_ratio = forked_count / total

        if fork_ratio > 0.7:
            score -= 3.0
        elif fork_ratio > 0.4:
            score -= 1.5

        # Skill alignment: do GitHub languages overlap with resume skills?
        gh_languages = set()
        for p in projects:
            for t in p.get("technologies", []):
                gh_languages.add(t.lower() if isinstance(t, str) else "")

        resume_lower = {s.lower() for s in resume_skills}
        overlap = gh_languages & resume_lower
        if len(overlap) >= 3:
            score += 1.5
        elif len(overlap) == 0 and gh_languages:
            score -= 1.0

        return max(0.0, min(10.0, score))
