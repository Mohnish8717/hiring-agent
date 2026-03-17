"""Module 4: EmailVerifier — Determines legitimacy of the candidate's email."""
import logging
import re
from typing import Dict, Any
from models import EmailVerificationResult # type: ignore

logger = logging.getLogger("identity_trust.email_verifier")

# Known disposable email providers
DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "tempmail.com", "throwaway.email",
    "yopmail.com", "10minutemail.com", "trashmail.com", "sharklasers.com",
    "guerrillamailblock.com", "grr.la", "dispostable.com", "maildrop.cc",
    "fakeinbox.com", "temp-mail.org", "mohmal.com", "getnada.com",
}

PROFESSIONAL_DOMAINS = {
    "gmail.com", "outlook.com", "hotmail.com", "yahoo.com", "icloud.com",
    "protonmail.com", "zoho.com", "aol.com", "live.com",
}


class EmailVerifier:
    """Validates candidate email authenticity using heuristic analysis."""

    def verify(self, profile: Dict[str, Any]) -> EmailVerificationResult:
        email: str = profile.get("email") or ""

        if not email:
            logger.info("No email provided, skipping verification")
            return EmailVerificationResult(
                email_legitimacy_score=0.0,
                email_domain_age="Unknown",
                email_domain_type="Missing",
                disposable_email_flag=False,
            )

        # --- 1. Syntax validation ---
        if not self._validate_syntax(email):
            return EmailVerificationResult(
                email_legitimacy_score=1.0,
                email_domain_age="Unknown",
                email_domain_type="Invalid Format",
                disposable_email_flag=False,
            )

        domain = email.split("@")[-1].lower()

        # --- 2. Disposable email detection ---
        is_disposable = domain in DISPOSABLE_DOMAINS
        if is_disposable:
            logger.warning(f"Disposable email domain detected: {domain}")
            return EmailVerificationResult(
                email_legitimacy_score=1.0,
                email_domain_age="N/A",
                email_domain_type="Disposable",
                disposable_email_flag=True,
            )

        # --- 3. Domain type classification ---
        if domain in PROFESSIONAL_DOMAINS:
            domain_type = "Consumer"
            score = 7.0
        elif "edu" in domain:
            domain_type = "Educational"
            score = 8.5
        elif "gov" in domain:
            domain_type = "Government"
            score = 9.0
        else:
            # Custom / corporate domain — higher trust
            domain_type = "Corporate/Custom"
            score = 8.0

        logger.info(f"EmailVerifier: {email} → {domain_type}, score={score}")
        return EmailVerificationResult(
            email_legitimacy_score=score,
            email_domain_age="Estimated: Established",
            email_domain_type=domain_type,
            disposable_email_flag=False,
        )

    @staticmethod
    def _validate_syntax(email: str) -> bool:
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))
