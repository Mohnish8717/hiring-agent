"""Module 7: SocialGraphAnalyzer — Analyzes cross-platform identity connections.

Refactored to implement a "Positive Evidence Weighting" model:
- BASE_SCORE = 4.0
- Presence Bonus: +1.0 per validated platform (LinkedIn, GitHub, Portfolio).
- Connection Bonus: High-trust cross-links (GH→LI, Port→GH, Port→LI).
- GitHub Quality Bonus: Account age, followers, and repo count.
- Final score clamped to 0-10.
"""
import logging
import datetime
from typing import Dict, Any, List, Optional, Set
from urllib.parse import urlparse

from models import SocialGraphResult  # type: ignore

logger = logging.getLogger("identity_trust.social_graph")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_scheme(url: str) -> str:
    """Ensure the URL has an http(s) scheme (GitHub blog fields often omit it)."""
    url = url.strip()
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _is_valid_url(url: Optional[str]) -> bool:
    """Check that the string is a real URL with a scheme and netloc."""
    if not url:
        return False
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def _normalize_domain(url: str) -> str:
    """Extract a canonical domain: lowercase, no www, no trailing slash."""
    try:
        parsed = urlparse(_add_scheme(url))
        domain = (parsed.netloc or "").lower().replace("www.", "")
        return domain.rstrip("/")
    except Exception:
        return ""


def _canonicalize_url(url: str) -> str:
    """Lowercase, strip trailing slash, remove www from netloc."""
    url = _add_scheme(url)
    try:
        parsed = urlparse(url)
        netloc = (parsed.netloc or "").lower().replace("www.", "")
        path = (parsed.path or "").rstrip("/")
        return f"{parsed.scheme}://{netloc}{path}"
    except Exception:
        return url.lower().rstrip("/")


def _domains_match(url_a: str, url_b: str) -> bool:
    """Compare two URLs by their normalized domains."""
    da = _normalize_domain(url_a)
    db = _normalize_domain(url_b)
    return bool(da and db and da == db)


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class SocialGraphAnalyzer:
    """Builds a graph of candidate identities across platforms and scores interlinking."""

    # Set to True to attempt fetching portfolio HTML for link extraction.
    enable_portfolio_scan: bool = False
    # Timeout in seconds for portfolio HTTP requests.
    portfolio_scan_timeout: int = 5

    def analyze(self, profile: Dict[str, Any]) -> SocialGraphResult:
        """Returns a SocialGraphResult using Positive Evidence Weighting."""
        BASE_SCORE = 4.0
        presence_bonus = 0.0
        connection_bonus = 0.0
        quality_bonus = 0.0

        # --- 1. Extract raw URLs ---
        raw_linkedin = profile.get("linkedin_url") or ""
        raw_github = profile.get("github_url") or ""
        raw_portfolio = profile.get("portfolio_url") or ""
        github_data: Optional[Dict[str, Any]] = profile.get("github_data")

        # --- 2. Normalize and Validate Presence ---
        valid_urls: Dict[str, str] = {}
        platforms_present: List[str] = []

        # LinkedIn Validation
        li_url = _add_scheme(raw_linkedin) if raw_linkedin.strip() else ""
        if _is_valid_url(li_url) and "linkedin.com" in _normalize_domain(li_url):
            valid_urls["linkedin"] = _canonicalize_url(li_url)
            presence_bonus += 1.0
            platforms_present.append("linkedin")

        # GitHub Validation
        gh_url = _add_scheme(raw_github) if raw_github.strip() else ""
        if _is_valid_url(gh_url) and "github.com" in _normalize_domain(gh_url):
            valid_urls["github"] = _canonicalize_url(gh_url)
            presence_bonus += 1.0
            platforms_present.append("github")

        # Portfolio Validation
        port_url = _add_scheme(raw_portfolio) if raw_portfolio.strip() else ""
        if _is_valid_url(port_url):
            port_domain = _normalize_domain(port_url)
            # Portfolio domain should be distinct from social platforms
            if "linkedin.com" not in port_domain and "github.com" not in port_domain:
                valid_urls["portfolio"] = _canonicalize_url(port_url)
                presence_bonus += 1.0
                platforms_present.append("portfolio")

        # --- 3. Detect Connections (Strong Evidence) ---
        connections_detected: Set[str] = set()

        has_linkedin = "linkedin" in valid_urls
        has_github = "github" in valid_urls
        has_portfolio = "portfolio" in valid_urls

        # GitHub → LinkedIn (+1.5)
        if has_github and has_linkedin and isinstance(github_data, dict):
            gh_profile = github_data.get("profile")
            if isinstance(gh_profile, dict):
                gh_blog = str(gh_profile.get("blog", "") or "").strip()
                gh_bio = str(gh_profile.get("bio", "") or "").strip()
                
                if "linkedin.com" in _normalize_domain(gh_blog) or "linkedin.com" in gh_bio.lower():
                    connections_detected.add("github→linkedin")
                    connection_bonus += 1.5  # type: ignore

        # Portfolio connections (requires portfolio URL)
        if has_portfolio:
            portfolio_links = self._extract_portfolio_links(valid_urls["portfolio"])
            
            # Portfolio → GitHub (+1.0)
            if has_github:
                # Check if GitHub username is in Portfolio URL
                gh_username = valid_urls["github"].rstrip("/").split("/")[-1].lower()
                if gh_username and gh_username in valid_urls["portfolio"].lower():
                    if "portfolio→github" not in connections_detected:
                        connections_detected.add("portfolio→github")
                        connection_bonus += 1.0  # type: ignore
                
                # Check HTML links if scanned
                elif portfolio_links:
                    for link in portfolio_links:
                        if "github.com" in _normalize_domain(link):
                            if "portfolio→github" not in connections_detected:
                                connections_detected.add("portfolio→github")
                                connection_bonus += 1.0  # type: ignore
                            break

            # Portfolio → LinkedIn (+1.0)
            if has_linkedin and portfolio_links:
                for link in portfolio_links:
                    if "linkedin.com" in _normalize_domain(link):
                        if "portfolio→linkedin" not in connections_detected:
                            connections_detected.add("portfolio→linkedin")
                            connection_bonus += 1.0  # type: ignore
                        break

        # --- 4. GitHub Quality Signals (+1.5 total) ---
        if github_data and isinstance(github_data, dict):
            gh_profile = github_data.get("profile")
            if isinstance(gh_profile, dict):
                # Repositories > 5 (+0.5)
                public_repos = int(gh_profile.get("public_repos", 0) or 0)
                if public_repos > 5:
                    quality_bonus += 0.5  # type: ignore
                
                # Followers > 10 (+0.5)
                followers = int(gh_profile.get("followers", 0) or 0)
                if followers > 10:
                    quality_bonus += 0.5  # type: ignore
                
                # Account Age > 1 year (+0.5)
                created_at = gh_profile.get("created_at")
                if created_at:
                    try:
                        created_date = datetime.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        age_days = (datetime.datetime.now(datetime.timezone.utc) - created_date).days
                        if age_days > 365:
                            quality_bonus += 0.5  # type: ignore
                    except Exception:
                        pass

        # --- 5. Final Calculation ---
        total_score = BASE_SCORE + presence_bonus + connection_bonus + quality_bonus
        final_score = min(10.0, round(total_score, 1))  # type: ignore

        # --- 6. Logging ---
        logger.info(
            f"SocialGraph:\n"
            f"platforms={platforms_present}\n"
            f"connections={list(connections_detected)}\n"
            f"presence_bonus={presence_bonus}\n"
            f"connection_bonus={connection_bonus}\n"
            f"quality_bonus={quality_bonus}\n"
            f"score={final_score}"
        )

        return SocialGraphResult(
            social_graph_trust_score=final_score,
            platforms_present=platforms_present,
            connections_detected=list(connections_detected)
        )

    def _extract_portfolio_links(self, portfolio_url: str) -> Optional[List[str]]:
        """Fetch portfolio HTML and extract <a href> links."""
        if not self.enable_portfolio_scan:
            return None
        try:
            import urllib.request
            from html.parser import HTMLParser

            class _LinkParser(HTMLParser):
                def __init__(self) -> None:
                    super().__init__()
                    self.links: List[str] = []

                def handle_starttag(self, tag: str, attrs: list) -> None:  # type: ignore[override]
                    if tag == "a":
                        for attr_name, attr_val in attrs:
                            if attr_name == "href" and attr_val:
                                self.links.append(attr_val)

            req = urllib.request.Request(
                portfolio_url,
                headers={"User-Agent": "HiringAgentBot/1.0"},
            )
            with urllib.request.urlopen(req, timeout=self.portfolio_scan_timeout) as resp:
                html = resp.read(512_000).decode("utf-8", errors="ignore")

            parser = _LinkParser()
            parser.feed(html)
            return parser.links

        except Exception as exc:
            logger.debug(f"SocialGraph: portfolio scan failed for {portfolio_url}: {exc}")
            return None
