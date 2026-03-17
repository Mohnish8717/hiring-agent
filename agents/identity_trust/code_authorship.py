"""Module 8: CodeAuthorshipAnalyzer — Verifies that the candidate actually wrote the code."""
import logging
from typing import Dict, Any, List
from models import CodeAuthorshipResult # type: ignore

logger = logging.getLogger("identity_trust.code_authorship")


class CodeAuthorshipAnalyzer:
    """Analyzes commit authorship and code ownership from GitHub data."""

    def analyze(self, profile: Dict[str, Any]) -> CodeAuthorshipResult:
        github_data = profile.get("github_data")
        candidate_name = (profile.get("name") or "").lower()

        if not github_data:
            return CodeAuthorshipResult()

        projects: List[Dict[str, Any]] = github_data.get("projects", [])
        gh_profile = github_data.get("profile", {})
        gh_username = str(gh_profile.get("login", "")).lower()

        if not projects:
            logger.info("CodeAuthorship: no projects found. Returning baseline.")
            return CodeAuthorshipResult(code_authorship_score=4.0)

        # --- Commit Authorship & Ownership Analysis ---
        owned_repos: int = 0
        owned_ratios: List[float] = []
        suspicious_repos_list: List[str] = []
        languages: set = set()
        loc_estimate: int = 0
        
        for p in projects:
            repo_name = p.get("name", "Unknown")
            gh_details = p.get("github_details", {})
            is_fork = p.get("fork", False) or gh_details.get("fork", False)
            
            # Use owner_login if available for robust ownership check
            repo_owner = p.get("owner_login") or gh_details.get("owner_login")
            if repo_owner:
                repo_owner_lower = repo_owner.lower()
                is_owned = False
                if repo_owner_lower == gh_username:
                    is_owned = True
                else:
                    # Fallback: Check if substantial name tokens match the repo owner
                    name_tokens = [t for t in str(candidate_name).split() if len(t) > 3]
                    if name_tokens and any(t in repo_owner_lower for t in name_tokens):
                        is_owned = True
            else:
                is_owned = not is_fork
                
            author_commits = max(0, p.get("author_commit_count", 0))
            total_commits = max(0, p.get("total_commit_count", 0))
            
            # 1 commit ~ 30 lines of code changed (conservative average)
            loc_estimate += author_commits * 50  # type: ignore

            if is_owned:
                owned_repos += 1  # type: ignore
                
                # Copy-paste detection: owned repo with >10 total commits but <5% by candidate
                if total_commits > 10 and (author_commits / total_commits) < 0.05:
                    suspicious_repos_list.append(repo_name)

                if total_commits > 0:
                    owned_ratios.append(author_commits / total_commits)
                else:
                    owned_ratios.append(0.0)
                    
                lang = p.get("language") or gh_details.get("language")
                if lang:
                    languages.add(str(lang).lower())

        total = len(projects)
        suspicious_count = len(suspicious_repos_list)

        # --- Average Authorship (Owned Repos Only) ---
        if owned_ratios:
            avg_authorship_percentage = (sum(owned_ratios) / len(owned_ratios)) * 100.0
        else:
            avg_authorship_percentage = 0.0

        # --- Language Diversity Bonus ---
        unique_langs = len(languages)
        diversity_bonus = 0.0
        if unique_langs >= 5:
            diversity_bonus = 1.0
        elif unique_langs >= 3:
            diversity_bonus = 0.5

        # --- Suspicious Penalty ---
        suspicious_penalty = min(suspicious_count * 1.0, 2.0)

        # --- Final Score Calculation ---
        baseline_score = 4.0
        ownership_score = (avg_authorship_percentage / 100.0) * 7.0
        
        total_score = baseline_score + ownership_score + diversity_bonus - suspicious_penalty
        final_score = max(0.0, min(10.0, total_score))

        logger.info(
            f"CodeAuthorship: owned={owned_repos}/{total}, "
            f"avg_auth={avg_authorship_percentage:.1f}%, suspicious={suspicious_count}, "
            f"diversity_bonus={diversity_bonus:.1f}, score={final_score:.1f}"
        )
        
        return CodeAuthorshipResult(
            code_authorship_score=round(final_score, 1),  # type: ignore
            commit_author_match=avg_authorship_percentage > 20.0,
            loc_authored=loc_estimate,
            owned_repos=owned_repos,
            total_repos_checked=total,
            avg_authorship_percentage=round(avg_authorship_percentage, 1),  # type: ignore
            suspicious_repos=suspicious_count,
            language_diversity_bonus=diversity_bonus
        )
