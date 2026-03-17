"""Module 13: TrustScoreAggregator — Combines all trust signals into final scores."""
import logging
from typing import Dict, Any, List, Optional
from models import (  # type: ignore
    IdentityTrustResult,
    LinkedInVerificationResult,
    GitHubVerificationResult,
    EmailVerificationResult,
    ResumeConsistencyResult,
    PortfolioResult,
    CodeAuthorshipResult,
    SocialGraphResult,
)

logger = logging.getLogger("identity_trust.trust_aggregator")

# Weights represent relative influence. Dynamic normalization adjusts them automatically.
WEIGHTS = {
    "github": 0.25,
    "linkedin": 0.20,
    "resume_consistency": 0.15,
    "code_authorship": 0.15,
    "social_graph": 0.10,
    "email": 0.10,
    "portfolio": 0.05,
    "behavioral": 0.05,
    "device": 0.05,
    "application_authenticity": 0.05,
}


class TrustScoreAggregator:
    """Combines all trust module signals into a final weighted score."""

    def aggregate(
        self,
        linkedin: LinkedInVerificationResult,
        github: GitHubVerificationResult,
        email: EmailVerificationResult,
        resume_consistency: ResumeConsistencyResult,
        portfolio: PortfolioResult,
        code_authorship: CodeAuthorshipResult,
        social_graph: SocialGraphResult,
        ai_resume_probability: float,
        behavioral_score: Optional[float],
        device_score: Optional[float],
        application_authenticity_score: Optional[float],
        fraud_flags: List[str],
    ) -> IdentityTrustResult:
        """Compute weighted identity_score, profile_consistency_score, and fraud_risk_level."""

        # --- Base Metrics Calculation ---
        # Note: All module scores are assumed to be on a 0-10 scale.
        
        # GitHub: Average of activity, credibility, and authenticity
        github_avg = (
            github.github_activity_score +
            github.open_source_credibility_score +
            github.repo_authenticity_score
        ) / 3.0

        # LinkedIn: Average of profile and consistency
        linkedin_avg = (
            linkedin.linkedin_profile_score +
            linkedin.linkedin_resume_consistency_score
        ) / 2.0

        # Resume Consistency: Average of timeline, experience, and skill
        resume_avg = (
            resume_consistency.timeline_consistency_score +
            resume_consistency.experience_consistency_score +
            resume_consistency.skill_consistency_score
        ) / 3.0

        # Portfolio: Direct score from unified verification
        portfolio_avg = portfolio.portfolio_score

        # --- Dynamic Weighing Logic ---
        # We only include modules that have valid data objects.
        # We do NOT exclude them just because the score is 0.
        
        active_modules = {
            "github": github_avg,
            "linkedin": linkedin_avg,
            "resume_consistency": resume_avg,
            "code_authorship": code_authorship.code_authorship_score,
            "social_graph": social_graph.social_graph_trust_score,
            "email": email.email_legitimacy_score,
            "portfolio": portfolio_avg,
        }
        
        # Optional metadata-dependent scores
        if behavioral_score is not None:
            active_modules["behavioral"] = behavioral_score
        if device_score is not None:
            active_modules["device"] = device_score
        if application_authenticity_score is not None:
            active_modules["application_authenticity"] = application_authenticity_score

        weighted_sum = 0.0
        active_weight_total = 0.0
        
        for name, score in active_modules.items():
            weight = WEIGHTS.get(name, 0.0)
            weighted_sum += (score * weight)
            active_weight_total += weight

        # Safety Guard: avoid division by zero
        if active_weight_total > 0:
            base_identity_score = weighted_sum / active_weight_total
        else:
            base_identity_score = 0.0

        # --- Penalties (Consistently Applied) ---
        
        # AI Resume Penalty: threshold 0.85, max 1.0 penalty
        if ai_resume_probability > 0.85:
            ai_penalty = min((ai_resume_probability - 0.85) * 2, 1.0)
        else:
            ai_penalty = 0.0
            
        # Fraud Flag Penalty: max 1.0 penalty total
        flag_penalty = min(len(fraud_flags) * 0.2, 1.0)
        
        total_penalties = ai_penalty + flag_penalty
        
        # Final clamped identity score (0-10)
        final_identity_score = max(0.0, min(10.0, base_identity_score - total_penalties))

        # --- Profile Consistency Score ---
        # Now includes LinkedIn consistency as a third pillar
        profile_consistency_score = (resume_avg + linkedin_avg + social_graph.social_graph_trust_score) / 3.0

        # --- Fraud Risk Level ---
        # LOW >= 8, MEDIUM >= 6, HIGH >= 4, else CRITICAL
        if final_identity_score >= 8.0:
            fraud_risk_level = "LOW"
        elif final_identity_score >= 6.0:
            fraud_risk_level = "MEDIUM"
        elif final_identity_score >= 4.0:
            fraud_risk_level = "HIGH"
        else:
            fraud_risk_level = "CRITICAL"

        # --- Structured Logging ---
        logger.info(
            f"TrustAggregator:\n"
            f"github={github_avg:.1f}\n"
            f"linkedin={linkedin_avg:.1f}\n"
            f"resume={resume_avg:.1f}\n"
            f"social_graph={social_graph.social_graph_trust_score:.1f}\n"
            f"email={email.email_legitimacy_score:.1f}\n"
            f"portfolio={portfolio_avg:.1f}\n"
            f"code_authorship={code_authorship.code_authorship_score:.1f}\n"
            f"active_weight_total={active_weight_total:.2f}\n"
            f"base_identity_score={base_identity_score:.2f}\n"
            f"penalties={total_penalties:.2f}\n"
            f"final identity_score={final_identity_score:.2f}\n"
            f"fraud risk level={fraud_risk_level}"
        )

        return IdentityTrustResult(
            identity_score=round(final_identity_score, 2),  # type: ignore
            profile_consistency_score=round(profile_consistency_score, 2),  # type: ignore
            fraud_risk_level=fraud_risk_level,
            fraud_flags=fraud_flags,
            linkedin=linkedin,
            github=github,
            email=email,
            resume_consistency=resume_consistency,
            portfolio=portfolio,
            code_authorship=code_authorship,
            social_graph=social_graph,
            ai_resume_probability=ai_resume_probability,
            behavioral_trust_score=behavioral_score or 0.0,
            device_trust_score=device_score or 0.0,
            application_authenticity_score=application_authenticity_score or 0.0,
            github_consistency=(
                github.repo_authenticity_score >= 6.0 and 
                github.github_activity_score >= 5.0
            ),
        )
