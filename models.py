from typing import List, Optional, Dict, Tuple, Any, Protocol, runtime_checkable
from pydantic import BaseModel, Field, field_validator # type: ignore
import logging
import json
from enum import Enum



logger = logging.getLogger(__name__)

class ModelProvider(Enum):
    """Enum for supported model providers."""

    OLLAMA = "ollama"
    GEMINI = "gemini"
    GROQ = "groq"


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM providers."""

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send a chat request to the LLM provider."""
        ...


class Location(BaseModel):
    """Location information for JSON Resume format."""

    address: Optional[str] = None
    postalCode: Optional[str] = None
    city: Optional[str] = None
    countryCode: Optional[str] = None
    region: Optional[str] = None


class Profile(BaseModel):
    """Social profile information for JSON Resume format."""

    network: Optional[str] = None
    username: Optional[str] = None
    url: str


class Basics(BaseModel):
    """Basic information for JSON Resume format."""

    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    url: Optional[str] = None
    summary: Optional[str] = None
    location: Optional[Location] = None
    profiles: Optional[List[Profile]] = None


class Work(BaseModel):
    """Work experience for JSON Resume format."""

    name: Optional[str] = None
    position: Optional[str] = None
    url: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    summary: Optional[str] = None
    highlights: Optional[List[str]] = None


class Volunteer(BaseModel):
    """Volunteer experience for JSON Resume format."""

    organization: Optional[str] = None
    position: Optional[str] = None
    url: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    summary: Optional[str] = None
    highlights: Optional[List[str]] = None


class Education(BaseModel):
    """Education information for JSON Resume format."""

    institution: Optional[str] = None
    url: Optional[str] = None
    area: Optional[str] = None
    studyType: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    score: Optional[str] = None
    courses: Optional[List[str]] = None


class Award(BaseModel):
    """Award information for JSON Resume format."""

    title: Optional[str] = None
    date: Optional[str] = None
    awarder: Optional[str] = None
    summary: Optional[str] = None


class Certificate(BaseModel):
    """Certificate information for JSON Resume format."""

    name: Optional[str] = None
    date: Optional[str] = None
    issuer: Optional[str] = None
    url: Optional[str] = None


class Publication(BaseModel):
    """Publication information for JSON Resume format."""

    name: Optional[str] = None
    publisher: Optional[str] = None
    releaseDate: Optional[str] = None
    url: Optional[str] = None
    summary: Optional[str] = None


class Skill(BaseModel):
    """Skill information for JSON Resume format."""

    name: Optional[str] = None
    level: Optional[str] = None
    keywords: Optional[List[str]] = None


class Language(BaseModel):
    """Language information for JSON Resume format."""

    language: Optional[str] = None
    fluency: Optional[str] = None


class Interest(BaseModel):
    """Interest information for JSON Resume format."""

    name: Optional[str] = None
    keywords: Optional[List[str]] = None


class Reference(BaseModel):
    """Reference information for JSON Resume format."""

    name: Optional[str] = None
    reference: Optional[str] = None


class Project(BaseModel):
    """Project information for JSON Resume format."""

    name: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    description: Optional[str] = None
    highlights: Optional[List[str]] = None
    url: Optional[str] = None
    technologies: Optional[List[str]] = None
    skills: Optional[List[str]] = None


class BasicsSection(BaseModel):
    """Basics section containing basic information."""

    basics: Optional[Basics] = None


class WorkSection(BaseModel):
    """Work section containing a list of work experiences."""

    work: Optional[List[Work]] = None


class EducationSection(BaseModel):
    """Education section containing a list of education entries."""

    education: Optional[List[Education]] = None


class SkillsSection(BaseModel):
    """Skills section containing a list of skill categories."""

    skills: Optional[List[Skill]] = None


class ProjectsSection(BaseModel):
    """Projects section containing a list of projects."""

    projects: Optional[List[Project]] = None


class AwardsSection(BaseModel):
    """Awards section containing a list of awards."""

    awards: Optional[List[Award]] = None


class JSONResume(BaseModel):
    """Complete JSON Resume format model."""

    basics: Optional[Basics] = None
    work: Optional[List[Work]] = None
    volunteer: Optional[List[Volunteer]] = None
    education: Optional[List[Education]] = None
    awards: Optional[List[Award]] = None
    certificates: Optional[List[Certificate]] = None
    publications: Optional[List[Publication]] = None
    skills: Optional[List[Skill]] = None
    languages: Optional[List[Language]] = None
    interests: Optional[List[Interest]] = None
    references: Optional[List[Reference]] = None
    projects: Optional[List[Project]] = None


class CategoryScore(BaseModel):
    score: float = Field(ge=0, description="Score achieved in this category")
    max: int = Field(gt=0, description="Maximum possible score")
    evidence: str = Field(min_length=1, description="Evidence supporting the score")


class Scores(BaseModel):
    open_source: CategoryScore
    self_projects: CategoryScore
    production: CategoryScore
    technical_skills: CategoryScore


class BonusPoints(BaseModel):
    total: float = Field(ge=0, le=20, description="Total bonus points")
    breakdown: str = Field(description="Breakdown of bonus points")


class Deductions(BaseModel):
    total: float = Field(
        ge=0,
        description="Total deduction points (stored as positive, applied as negative)",
    )
    reasons: str = Field(description="Reasons for deductions")


class LinkedInVerificationResult(BaseModel):
    linkedin_profile_score: float = Field(default=0.0, ge=0, le=10)
    linkedin_resume_consistency_score: float = Field(default=0.0, ge=0, le=10)
    linkedin_network_strength: str = Field(default="Unknown")

class GitHubVerificationResult(BaseModel):
    github_activity_score: float = Field(default=0.0, ge=0, le=10)
    open_source_credibility_score: float = Field(default=0.0, ge=0, le=10)
    repo_authenticity_score: float = Field(default=0.0, ge=0, le=10)

class EmailVerificationResult(BaseModel):
    email_legitimacy_score: float = Field(default=0.0, ge=0, le=10)
    email_domain_age: str = Field(default="Unknown")
    email_domain_type: str = Field(default="Unknown")
    disposable_email_flag: bool = Field(default=False)

class ResumeConsistencyResult(BaseModel):
    timeline_consistency_score: float = Field(default=0.0, ge=0, le=10)
    experience_consistency_score: float = Field(default=0.0, ge=0, le=10)
    skill_consistency_score: float = Field(default=0.0, ge=0, le=10)


class SocialGraphResult(BaseModel):
    """Structured result from SocialGraphAnalyzer."""
    social_graph_trust_score: float = Field(default=0.0, ge=0, le=10)
    platforms_present: List[str] = Field(default_factory=list, description="Validated platform names found")
    connections_detected: List[str] = Field(default_factory=list, description="Detected cross-platform links, e.g. 'github→portfolio'")


class CodeAuthorshipResult(BaseModel):
    code_authorship_score: float = Field(default=0.0, ge=0, le=10)
    commit_author_match: bool = Field(default=False)
    loc_authored: int = Field(default=0)
    owned_repos: int = Field(default=0)
    total_repos_checked: int = Field(default=0)
    avg_authorship_percentage: float = Field(default=0.0, ge=0, le=100.0)
    suspicious_repos: int = Field(default=0)
    language_diversity_bonus: float = Field(default=0.0)

class PortfolioResult(BaseModel):
    portfolio_score: float = Field(ge=0, le=10, description="Overall verification and feature alignment score")
    evidence_found: List[str] = Field(default_factory=list, description="Proven technical evidence matching the resume")
    project_complexity: str = Field(description="Analysis of project technical difficulty and alignment")
    oss_contribution_impact: Optional[str] = None
    project_verification_report: str = Field(default="", description="Detailed markdown report breakdown for each matched project")
    suggested_improvements: List[str] = Field(default_factory=list, description="Recommendations for the candidate's resume or portfolio")
    unverifiable_claims: List[str] = Field(default_factory=list, description="Claims lacking concrete GitHub or portfolio evidence")


class IdentityTrustResult(BaseModel):
    """Comprehensive identity trust result from the 14-module pipeline."""
    # Aggregate scores
    identity_score: float = Field(default=0.0, ge=0, le=10, description="Final weighted trust score (0-10)")
    profile_consistency_score: float = Field(default=0.0, ge=0, le=10)
    fraud_risk_level: str = Field(default="UNKNOWN", description="LOW / MEDIUM / HIGH / CRITICAL")
    fraud_flags: List[str] = Field(default_factory=list)

    # Per-module results
    linkedin: Optional[LinkedInVerificationResult] = None
    github: Optional[GitHubVerificationResult] = None
    email: Optional[EmailVerificationResult] = None
    resume_consistency: Optional[ResumeConsistencyResult] = None
    portfolio: Optional[PortfolioResult] = None
    code_authorship: Optional[CodeAuthorshipResult] = None
    social_graph: Optional[SocialGraphResult] = None

    # Scalar module scores
    social_graph_trust_score: float = Field(default=0.0, ge=0, le=10)
    ai_resume_probability: float = Field(default=0.0, ge=0, le=1)
    behavioral_trust_score: float = Field(default=0.0, ge=0, le=10)
    device_trust_score: float = Field(default=0.0, ge=0, le=10)
    application_authenticity_score: float = Field(default=0.0, ge=0, le=10)

    # Report
    trust_report: str = Field(default="", description="Human-readable trust report")
    authenticity_signals: Dict[str, Any] = Field(default_factory=dict)

    # Backwards compat
    github_consistency: bool = Field(default=False)
    linkedin_verification: Optional[str] = Field(default=None)



class AssessmentResult(BaseModel):
    skill_match_score: float = Field(ge=0, le=10)
    suggested_tasks: List[str] = Field(description="Tailored coding or system design tasks")
    actual_capability_evidence: str = Field(description="Evidence of real-world capability vs claims")


class AnalyticsResult(BaseModel):
    success_probability: float = Field(ge=0, le=1, description="Probability of candidate success")
    team_fit_likelihood: float = Field(ge=0, le=1)
    attrition_risk: float = Field(ge=0, le=1)
    retention_prediction: str = Field(description="Reasoning for retention/success predictions")
    salary_estimate_band: Optional[str] = None


class ApplicationQualityResult(BaseModel):
    ai_generated_probability: float = Field(ge=0, le=1)
    application_intent_score: float = Field(ge=0, le=10)
    is_spam: bool = False
    spam_signals: List[str] = Field(default_factory=list)


class EvaluationData(BaseModel):
    scores: Scores
    bonus_points: BonusPoints
    deductions: Deductions
    key_strengths: List[str] = Field(min_items=1, max_items=5)
    areas_for_improvement: List[str] = Field(min_items=1, max_items=5)
    jd_fit_analysis: Optional[str] = Field(None, description="Detailed analysis of how the candidate fits or mismatches the JD")
    mismatch_reasons: List[str] = Field(default_factory=list, description="Specific reasons why the candidate did not match the JD requirements")
    
    # Next-Gen Signals
    identity_trust: Optional[IdentityTrustResult] = None
    portfolio_intelligence: Optional[PortfolioResult] = None
    skill_assessment: Optional[AssessmentResult] = None
    hiring_analytics: Optional[AnalyticsResult] = None
    application_quality: Optional[ApplicationQualityResult] = None

    @property
    def total_score(self) -> float:
        """Calculate the true final ATS score inclusive of bonuses and deductions."""
        base = (
            self.scores.open_source.score +
            self.scores.self_projects.score +
            self.scores.production.score +
            self.scores.technical_skills.score
        )
        return base + self.bonus_points.total - self.deductions.total



class GitHubProfile(BaseModel):
    """Pydantic model for GitHub profile data."""

    username: str
    name: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    company: Optional[str] = None
    public_repos: Optional[int] = None
    followers: Optional[int] = None
    following: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    avatar_url: Optional[str] = None
    blog: Optional[str] = None
    twitter_username: Optional[str] = None
    hireable: Optional[bool] = None


class OllamaProvider:
    """Ollama LLM provider implementation."""

    def __init__(self):
        import ollama

        self.client = ollama

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send a chat request to Ollama."""

        ollama_options = options.copy() if options else {}

        # remove steam from ollama options
        ollama_options.pop("stream", None)

        # Add num_ctx 32K context window to options
        ollama_options["num_ctx"] = 32768

        # convert to chat params
        chat_params = {
            "model": model,
            "messages": messages,
            "options": ollama_options,
        }

        # add it to top level
        if "stream" in kwargs:
            chat_params["stream"] = kwargs["stream"]

        if "format" in kwargs:
            chat_params["format"] = kwargs["format"]

        return self.client.chat(**chat_params)


class GeminiProvider:
    """Google Gemini API provider implementation."""

    def __init__(self, api_key: str):
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self.client = genai

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send a chat request to Google Gemini API."""
        # Map options to Gemini parameters
        generation_config = {}
        if options:
            if "temperature" in options:
                generation_config["temperature"] = options["temperature"]
            if "top_p" in options:
                generation_config["top_p"] = options["top_p"]

        # Create a Gemini model
        gemini_model = self.client.GenerativeModel(
            model_name=model, generation_config=generation_config
        )

        # Convert messages to Gemini format
        gemini_messages = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            gemini_messages.append({"role": role, "parts": [msg["content"]]})

        # Send the chat request
        response = gemini_model.generate_content(gemini_messages)

        # Convert Gemini response to Ollama-like format for compatibility
        return {"message": {"role": "assistant", "content": response.text}}


class GroqProvider:
    """Groq API provider implementation."""

    def __init__(self, api_key: str):
        from groq import Groq

        self.client = Groq(api_key=api_key)

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send a chat request to Groq API with rate limiting and backoff."""
        from utils.resilience import GroqThrottler, execute_with_backoff
        
        chat_params = {
            "model": model,
            "messages": messages,
        }

        if options:
            if "temperature" in options:
                chat_params["temperature"] = options["temperature"]
            if "top_p" in options:
                chat_params["top_p"] = options["top_p"]
            if "max_tokens" in options:
                chat_params["max_tokens"] = options["max_tokens"]

        # 1. Use centralized throttler to serialize requests and manage budget
        throttler = GroqThrottler()
        
        # Estimate prompt tokens (very rough: chars / 4) to proactively wait
        prompt_len = sum(len(m["content"]) for m in messages)
        estimated_tokens = (prompt_len // 4) + 1000 # Buffer for response
        
        def _make_request():
            # Proactive wait if budget is already exhausted
            throttler.wait_if_needed(estimated_tokens)
            
            with throttler.semaphore:
                # Use raw response to access headers for rate limiting
                raw_response = self.client.chat.completions.with_raw_response.create(**chat_params)
                
                # Update throttler with actual limits from headers
                throttler.update_limits(raw_response.headers)
                
                return raw_response.parse()

        # 2. Execute with exponential backoff on 429s (RPM/TPM)
        try:
            response = execute_with_backoff(_make_request)
        except Exception as e:
            # Specifically tag TPD/Daily limit errors for the FailoverProvider to catch
            if "TPD" in str(e) or "tokens per day" in str(e):
                logger.error("🛑 Groq DAILY Token Limit (TPD) reached.")
            raise e

        # Convert Groq response to Ollama-like format for compatibility
        return {"message": {"role": "assistant", "content": response.choices[0].message.content}}


class FailoverProvider:
    """A wrapper provider that handles failover between multiple providers."""

    def __init__(self, primary: LLMProvider, secondary: LLMProvider, model_map: Dict[str, str] = None):
        self.primary = primary
        self.secondary = secondary
        self.model_map = model_map or {}
        self.active_provider = primary
        self.is_failed_over = False

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Attempt primary provider, fallback to secondary on terminal errors."""
        target_model = model
        
        # If we are already in failover mode, use secondary immediately
        if self.is_failed_over:
            target_model = self.model_map.get(model, model)
            # Ensure we don't use Groq models with Gemini etc.
            if "llama" in target_model and not isinstance(self.secondary, GroqProvider):
                 target_model = "gemini-2.0-flash" if "gemini" in str(type(self.secondary)).lower() else target_model
            
            return self.secondary.chat(target_model, messages, options, **kwargs)

        try:
            return self.primary.chat(model, messages, options, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            # Detect terminal daily limits or other failures that justify failover
            if "tpd" in error_str or "tokens per day" in error_str or "rate_limit_exceeded" in error_str:
                logger.warning(f"🚨 Primary provider hit daily limit or terminal error. Failing over to secondary...")
                self.is_failed_over = True
                self.active_provider = self.secondary
                
                # Recursive call will now use secondary
                return self.chat(model, messages, options, **kwargs)
            else:
                # Re-raise if it's not a failover-worthy error
                raise e
