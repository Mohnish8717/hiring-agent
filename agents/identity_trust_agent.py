"""IdentityTrustAgent — Full 14-module pipeline for candidate identity verification.

Pipeline:
    ProfileCollector → LinkedInVerifier → GitHubVerifier → EmailVerifier
        → ResumeConsistencyChecker → PortfolioVerifier
            → SocialGraphAnalyzer → CodeAuthorshipAnalyzer
                → AIResumeDetector → BehavioralSignalsEngine
                    → DeviceFingerprintAnalyzer → ApplicationFraudDetector
                        → TrustScoreAggregator → IdentityTrustReportGenerator
"""
import asyncio
from typing import Dict, Any, Optional, List
from agents.base_agent import Agent # type: ignore
from models import IdentityTrustResult, JSONResume # type: ignore

# Sub-module imports
from agents.identity_trust.profile_collector import ProfileCollector # type: ignore
from agents.identity_trust.linkedin_verifier import LinkedInVerifier # type: ignore
from agents.identity_trust.github_verifier import GitHubVerifier # type: ignore
from agents.identity_trust.email_verifier import EmailVerifier # type: ignore
from agents.identity_trust.resume_consistency import ResumeConsistencyChecker # type: ignore
from agents.identity_trust.portfolio_verifier import PortfolioVerifier # type: ignore
from agents.identity_trust.social_graph import SocialGraphAnalyzer # type: ignore
from agents.identity_trust.code_authorship import CodeAuthorshipAnalyzer # type: ignore
from agents.identity_trust.behavioral_signals import BehavioralSignalsEngine # type: ignore
from agents.identity_trust.device_fingerprint import DeviceFingerprintAnalyzer # type: ignore
from agents.identity_trust.application_fraud import ApplicationFraudDetector # type: ignore
from agents.identity_trust.trust_aggregator import TrustScoreAggregator # type: ignore
from agents.identity_trust.report_generator import IdentityTrustReportGenerator # type: ignore


class IdentityTrustAgent(Agent):
    """Agent specialized in multi-stage identity verification and fraud detection.

    Runs a 14-module sequential pipeline covering:
    - Profile collection & normalization
    - Multi-platform verification (LinkedIn, GitHub, Email, Portfolio)
    - Cross-reference & consistency checks
    - Code authorship verification
    - AI-generated resume detection
    - Behavioral & device fraud analysis
    - Weighted trust aggregation
    - Human-readable report generation
    """

    def __init__(self):
        Agent.__init__(self, "IdentityTrustAgent")

        # Initialize sub-modules
        self.profile_collector = ProfileCollector()
        self.linkedin_verifier = LinkedInVerifier()
        self.github_verifier = GitHubVerifier()
        self.email_verifier = EmailVerifier()
        self.resume_consistency = ResumeConsistencyChecker()
        self.portfolio_verifier = PortfolioVerifier()
        self.social_graph = SocialGraphAnalyzer()
        self.code_authorship = CodeAuthorshipAnalyzer()
        self.behavioral_engine = BehavioralSignalsEngine()
        self.device_fingerprint = DeviceFingerprintAnalyzer()
        self.fraud_detector = ApplicationFraudDetector()
        self.trust_aggregator = TrustScoreAggregator()
        self.report_generator = IdentityTrustReportGenerator()

    async def process(self, input_data: Dict[str, Any]) -> IdentityTrustResult:
        """
        Run the full 14-module identity trust pipeline.

        Input: {
            "resume_data": JSONResume,
            "github_data": Optional[Dict],
            "application_metadata": Optional[Dict],  # For behavioral/device signals
            "ai_probability": Optional[float]      # Pre-calculated probability from app quality
        }
        """
        resume_data: Optional[JSONResume] = input_data.get("resume_data")
        github_data: Optional[Dict[str, Any]] = input_data.get("github_data")
        application_metadata: Optional[Dict[str, Any]] = input_data.get("application_metadata")
        ai_probability: Optional[float] = input_data.get("ai_probability")


        if not resume_data:
            self.log_error("No resume data provided for identity trust analysis")
            return IdentityTrustResult(
                identity_score=0.0,
                fraud_risk_level="UNKNOWN",
                fraud_flags=["Missing resume data"],
            )

        fraud_flags: List[str] = []

        # ── Module 1: ProfileCollector ──
        self.log_info("Module 1/14: ProfileCollector")
        profile = self.profile_collector.collect(resume_data, github_data)

        # ── Module 2: LinkedInVerifier ──
        self.log_info("Module 2/14: LinkedInVerifier")
        linkedin_result = await self.linkedin_verifier.verify(profile)

        # ── Module 3: GitHubVerifier ──
        self.log_info("Module 3/14: GitHubVerifier")
        github_result = self.github_verifier.verify(profile)

        # ── Module 4: EmailVerifier ──
        self.log_info("Module 4/14: EmailVerifier")
        email_result = self.email_verifier.verify(profile)
        if email_result.disposable_email_flag:
            fraud_flags.append("Disposable email detected")

        # ── Module 5: ResumeConsistencyChecker ──
        self.log_info("Module 5/14: ResumeConsistencyChecker")
        consistency_result = await self.resume_consistency.check(profile, github_data)

        # ── Module 6: PortfolioVerifier ──
        self.log_info("Module 6/14: PortfolioVerifier")
        portfolio_result = await self.portfolio_verifier.verify(profile)

        # ── Module 7: SocialGraphAnalyzer ──
        self.log_info("Module 7/14: SocialGraphAnalyzer")
        social_graph_result = self.social_graph.analyze(profile)

        # ── Module 8: CodeAuthorshipAnalyzer ──
        self.log_info("Module 8/14: CodeAuthorshipAnalyzer")
        authorship_result = self.code_authorship.analyze(profile)

        # ── Module 9: AIResumeDetector ──
        self.log_info("Module 9/14: AIResumeDetector")
        if ai_probability is not None:
            self.log_info(f"Using pre-calculated AI probability: {ai_probability:.2f}")
        else:
            self.log_info("Pre-calculated AI probability not provided, defaulting to 0.0")
            ai_probability = 0.0

        # Final safety check for type checker
        ai_probability_val: float = ai_probability if ai_probability is not None else 0.0
        if ai_probability_val > 0.7:
            fraud_flags.append(f"High AI-generated resume probability: {ai_probability_val:.0%}")



        # ── Module 10: BehavioralSignalsEngine ──
        self.log_info("Module 10/14: BehavioralSignalsEngine")
        behavioral_score = self.behavioral_engine.analyze(profile, application_metadata)

        # ── Module 11: DeviceFingerprintAnalyzer ──
        self.log_info("Module 11/14: DeviceFingerprintAnalyzer")
        device_score = self.device_fingerprint.analyze(application_metadata)

        # ── Module 12: ApplicationFraudDetector ──
        self.log_info("Module 12/14: ApplicationFraudDetector")
        app_authenticity = self.fraud_detector.detect(profile, application_metadata)
        if app_authenticity is not None and app_authenticity < 4.0:
            fraud_flags.append("Low application authenticity score")

        # ── Module 13: TrustScoreAggregator ──
        self.log_info("Module 13/14: TrustScoreAggregator")
        trust_result = self.trust_aggregator.aggregate(
            linkedin=linkedin_result,
            github=github_result,
            email=email_result,
            resume_consistency=consistency_result,
            portfolio=portfolio_result,
            code_authorship=authorship_result,
            social_graph=social_graph_result,
            ai_resume_probability=ai_probability,
            behavioral_score=behavioral_score,
            device_score=device_score,
            application_authenticity_score=app_authenticity,
            fraud_flags=fraud_flags,
        )

        # ── Module 14: IdentityTrustReportGenerator ──
        self.log_info("Module 14/14: IdentityTrustReportGenerator")
        report = self.report_generator.generate(trust_result)
        trust_result.trust_report = report

        self.log_info(
            f"Pipeline complete → Score: {trust_result.identity_score:.2f}/10, "
            f"Risk: {trust_result.fraud_risk_level}"
        )
        return trust_result
