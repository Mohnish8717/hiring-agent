"""Module 14: IdentityTrustReportGenerator — Generates explainable trust reports."""
import logging
from models import IdentityTrustResult # type: ignore

logger = logging.getLogger("identity_trust.report_generator")


class IdentityTrustReportGenerator:
    """Generates a human-readable trust report for recruiters."""

    def generate(self, result: IdentityTrustResult) -> str:
        """Produce a formatted trust report string and attach it to the result."""
        lines = [
            "═══════════════════════════════════════",
            "        IDENTITY TRUST REPORT          ",
            "═══════════════════════════════════════",
            "",
        ]

        # LinkedIn
        li = result.linkedin
        li_label = "N/A"
        if li:
            if li.linkedin_profile_score >= 7:
                li_label = "High"
            elif li.linkedin_profile_score >= 4:
                li_label = "Medium"
            else:
                li_label = "Low"
        lines.append(f"LinkedIn credibility:      {li_label}")

        # GitHub
        gh = result.github
        gh_label = "N/A"
        if gh:
            avg = (gh.github_activity_score + gh.open_source_credibility_score + gh.repo_authenticity_score) / 3.0
            if avg >= 7:
                gh_label = "High"
            elif avg >= 4:
                gh_label = "Medium"
            else:
                gh_label = "Low"
        lines.append(f"GitHub authenticity:       {gh_label}")

        # Portfolio
        pf = result.portfolio
        pf_label = "N/A"
        if pf:
            avg = pf.portfolio_score
            if avg >= 7:
                pf_label = "High"
            elif avg >= 4:
                pf_label = "Medium"
            else:
                pf_label = "Low"
        lines.append(f"Portfolio validation:      {pf_label}")

        # Resume consistency
        rc = result.resume_consistency
        rc_label = "N/A"
        if rc:
            avg = (rc.timeline_consistency_score + rc.experience_consistency_score + rc.skill_consistency_score) / 3.0
            if avg >= 7:
                rc_label = "High"
            elif avg >= 4:
                rc_label = "Medium"
            else:
                rc_label = "Low"
        lines.append(f"Resume consistency:       {rc_label}")

        # Email
        em = result.email
        lines.append(f"Email legitimacy:         {em.email_domain_type if em else 'N/A'}")
        
        # Social Graph
        sg = result.social_graph
        sg_label = "N/A"
        if sg:
            if sg.social_graph_trust_score >= 8:
                sg_label = "Strong"
            elif sg.social_graph_trust_score >= 5:
                sg_label = "Moderate"
            else:
                sg_label = "Weak"
        lines.append(f"Social graph trust:       {sg_label} ({sg.social_graph_trust_score if sg else 0.0}/10)")
        if sg and sg.connections_detected:
            conn_str = ", ".join(sg.connections_detected)
            lines.append(f"  • Verified links: {conn_str}")

        # Code Authorship
        ca = result.code_authorship
        ca_label = "N/A"
        if ca:
            if ca.code_authorship_score >= 8:
                ca_label = "Strong"
            elif ca.code_authorship_score >= 5:
                ca_label = "Moderate"
            else:
                ca_label = "Weak"
        lines.append(f"Code authorship:          {ca_label} ({ca.code_authorship_score if ca else 0.0}/10)")
        if ca and ca.owned_repos > 0:
            lines.append(f"  • Owned Repos: {ca.owned_repos}/{ca.total_repos_checked} (Avg Auth: {ca.avg_authorship_percentage:.1f}%)")
        if ca and ca.suspicious_repos > 0:
            lines.append(f"  • Suspicious Repos: {ca.suspicious_repos}")

        # AI Resume
        ai_label = "Low" if result.ai_resume_probability < 0.3 else ("Medium" if result.ai_resume_probability < 0.6 else "High")
        lines.append(f"AI-generated probability: {ai_label} ({result.ai_resume_probability:.0%})")

        lines.append("")
        lines.append(f"Fraud Risk:               {result.fraud_risk_level}")
        lines.append(f"Overall Trust Score:      {result.identity_score:.2f} / 10")

        if result.fraud_flags:
            lines.append("")
            lines.append("⚠ Fraud Flags:")
            for flag in result.fraud_flags:
                lines.append(f"  • {flag}")

        lines.append("")
        lines.append("═══════════════════════════════════════")

        report = "\n".join(lines)
        logger.info("Trust report generated successfully")
        return report
