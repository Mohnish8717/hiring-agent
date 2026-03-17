"""
LangGraph DAG-based orchestrator for the IKSHA multi-agent ATS pipeline.

Replaces the sequential pipeline with a graph that supports:
  - Parallel execution of independent agents
  - Conditional routing (e.g. skip GitHub if no URL)
  - Dynamic fallbacks and error isolation per node

Graph topology:
  extraction → [quality + verification(conditional)] → [identity_trust + skill_assessment] → bias_audit → [hiring_analytics + candidate_experience] → persist → report
"""

import logging
import asyncio
import sys
import os
import json
import uuid
from typing import Dict, Any, Optional, TypedDict, Annotated
from langgraph.graph import StateGraph, END  # type: ignore

from agents.extraction_agent import ExtractionAgent  # type: ignore
from agents.verification_agent import VerificationAgent  # type: ignore
from agents.bias_audit_agent import BiasAuditAgent  # type: ignore
from agents.identity_trust_agent import IdentityTrustAgent  # type: ignore
from agents.skill_assessment_agent import SkillAssessmentAgent  # type: ignore
from agents.hiring_analytics_agent import HiringAnalyticsAgent  # type: ignore
from agents.application_quality_agent import ApplicationQualityAgent  # type: ignore
from agents.candidate_experience_agent import CandidateExperienceAgent  # type: ignore
from knowledge.graph_engine import SkillsGraphEngine  # type: ignore
from db.vector_store import CandidateVectorStore  # type: ignore
from db.database import async_session_factory
from db.pg_models import Candidate, AuditLog
from utils.storage import upload_file, generate_presigned_url
from models import JSONResume, EvaluationData  # type: ignore


# ---------------------------------------------------------------------------
# Pipeline State
# ---------------------------------------------------------------------------
class PipelineState(TypedDict, total=False):
    """Shared state flowing through all graph nodes."""
    pdf_path: str
    job_description: Optional[str]
    on_log: Any  # callback

    # Outputs populated by nodes
    resume_data: Any
    github_url: Optional[str]
    github_data: Any
    app_quality: Any
    identity_trust: Any
    skill_assessment: Any
    blind_evaluation: Any
    hiring_analytics: Any
    candidate_experience: Any
    contribution_map: Dict[str, Any]
    serializable_results: Dict[str, Any]
    report_url: Optional[str]
    resume_object_key: Optional[str]
    report_object_key: Optional[str]
    request_id: Optional[str]
    tenant_id: Any
    start_time: float


# ---------------------------------------------------------------------------
# Orchestrator Class
# ---------------------------------------------------------------------------
class ATSOrchestrator:
    """Central orchestrator managing the multi-agent ATS pipeline via LangGraph."""

    def __init__(self):
        self.logger = logging.getLogger("orchestrator")
        self.graph_engine = SkillsGraphEngine()
        
        try:
            self.vector_store = CandidateVectorStore()
        except Exception as e:
            self.logger.warning(f"Vector store (Qdrant) initialization failed: {e}. Vector search features will be disabled.")
            self.vector_store = None

        # Initialize agents once
        self.extraction_agent = ExtractionAgent()
        self.verification_agent = VerificationAgent()
        self.bias_audit_agent = BiasAuditAgent(graph_engine=self.graph_engine)
        self.identity_trust_agent = IdentityTrustAgent()
        self.skill_assessment_agent = SkillAssessmentAgent()
        self.hiring_analytics_agent = HiringAnalyticsAgent()
        self.quality_agent = ApplicationQualityAgent()
        self.experience_agent = CandidateExperienceAgent()

        # Build the DAG
        self._graph = self._build_graph()

    # ------------------------------------------------------------------
    # Helper: unified logger
    # ------------------------------------------------------------------
    async def _log(self, state: PipelineState, msg: str):
        self.logger.info(msg)
        on_log = state.get("on_log")
        if on_log:
            if asyncio.iscoroutinefunction(on_log):
                await on_log(msg)
            else:
                on_log(msg)

    async def _add_audit_log(self, state: PipelineState, action: str, details: Optional[Dict] = None):
        """Helper to persist audit logs to PostgreSQL with fail-safe."""
        if os.getenv("DB_ENABLED", "true").lower() == "false":
            return
        try:
            async with async_session_factory() as session:
                audit = AuditLog(
                    tenant_id=state.get("tenant_id", uuid.UUID("00000000-0000-0000-0000-000000000000")),
                    request_id=state.get("request_id", "system"),
                    action=action,
                    details=details or {}
                )
                session.add(audit)
                await session.commit()
        except Exception as e:
            self.logger.warning(f"Audit log skipped (DB unreachable): {e}")

    # ------------------------------------------------------------------
    # Graph node definitions
    # ------------------------------------------------------------------
    async def _node_extraction(self, state: PipelineState) -> dict:
        await self._log(state, "--- Phase 1: Extraction ---")
        
        # Upload raw resume to MinIO (enterprise audit trail)
        pdf_path = state["pdf_path"]
        object_key = f"resumes/{os.path.basename(pdf_path)}"
        try:
            upload_file(pdf_path, object_key)
            await self._log(state, f"Uploaded raw resume to MinIO: {object_key}")
        except Exception as e:
            self.logger.error(f"Failed to upload resume to MinIO: {e}")

        resume_data = await self.extraction_agent.process(pdf_path)
        
        await self._add_audit_log(state, "REUME_EXTRACTION", {
            "status": "success" if resume_data else "failed",
            "pdf_path": pdf_path
        })

        if not resume_data:
            await self._log(state, "Extraction failed.")
            return {"resume_data": None}

        github_url = self._get_github_url(resume_data)
        return {"resume_data": resume_data, "github_url": github_url, "resume_object_key": object_key}

    async def _node_quality(self, state: PipelineState) -> dict:
        await self._log(state, "--- Phase 1.5: Application Quality ---")
        resume_data = state.get("resume_data")
        if not resume_data:
            return {"app_quality": None}
        quality_input = resume_data.model_dump(include={
            "basics": {"summary"}, "work": True, "projects": True
        })
        app_quality = await self.quality_agent.process({"resume_text": json.dumps(quality_input)})
        
        await self._add_audit_log(state, "QUALITY_CHECK", {
            "ai_prob": app_quality.ai_generated_probability if app_quality else 0
        })

        return {"app_quality": app_quality}

    async def _node_verification(self, state: PipelineState) -> dict:
        await self._log(state, "--- Phase 2: Verification ---")
        github_url = state.get("github_url")
        if not github_url:
            await self._log(state, "No GitHub URL found, skipping verification")
            await self._add_audit_log(state, "GITHUB_VERIFICATION", {"status": "skipped"})
            return {"github_data": None}
        await self._log(state, f"GitHub URL found: {github_url}")
        github_data = await self.verification_agent.process(github_url)
        
        await self._add_audit_log(state, "GITHUB_VERIFICATION", {
            "status": "success" if github_data else "failed",
            "url": github_url
        })

        return {"github_data": github_data}

    async def _node_identity_trust(self, state: PipelineState) -> dict:
        await self._log(state, "--- Phase 2.1: Identity Trust ---")
        resume_data = state.get("resume_data")
        github_data = state.get("github_data")
        app_quality = state.get("app_quality")
        identity_trust = await self.identity_trust_agent.process({
            "resume_data": resume_data,
            "github_data": github_data,
            "ai_probability": app_quality.ai_generated_probability if app_quality else None,
        })
        
        await self._add_audit_log(state, "IDENTITY_TRUST_SCORING", {
            "score": identity_trust.identity_score if identity_trust else 0
        })

        return {"identity_trust": identity_trust}

    async def _node_skill_assessment(self, state: PipelineState) -> dict:
        await self._log(state, "--- Phase 2.2: Skill Assessment ---")
        resume_data = state.get("resume_data")
        if not resume_data:
            return {"skill_assessment": None}
        assessment_resume = JSONResume(**resume_data.model_dump(include={
            "basics": {"name"}, "skills": True, "work": True, "projects": True
        }))
        skill_assessment = await self.skill_assessment_agent.process({
            "resume_data": assessment_resume,
            "jd_text": state.get("job_description"),
        })
        
        await self._add_audit_log(state, "SKILL_ASSESSMENT", {
            "match_score": skill_assessment.skill_match_score if skill_assessment else 0
        })

        return {"skill_assessment": skill_assessment}

    async def _node_bias_audit(self, state: PipelineState) -> dict:
        await self._log(state, "--- Phase 3: Bias Audit & Evaluation ---")
        resume_data = state.get("resume_data")
        evaluation_input = {
            "resume_data": resume_data,
            "github_data": state.get("github_data"),
            "job_description": state.get("job_description"),
        }
        blind_evaluation = await self.bias_audit_agent.process(evaluation_input)

        # Merge next-gen signals
        if blind_evaluation:
            blind_evaluation.identity_trust = state.get("identity_trust")
            blind_evaluation.portfolio_intelligence = (
                state["identity_trust"].portfolio if state.get("identity_trust") else None
            )
            blind_evaluation.skill_assessment = state.get("skill_assessment")
            blind_evaluation.application_quality = state.get("app_quality")
            
        await self._add_audit_log(state, "BIAS_AUDIT_EVALUATION", {
            "status": "success" if blind_evaluation else "failed"
        })

        return {"blind_evaluation": blind_evaluation}

    async def _node_hiring_analytics(self, state: PipelineState) -> dict:
        await self._log(state, "--- Phase 3.5: Hiring Analytics ---")
        blind_evaluation = state.get("blind_evaluation")
        resume_data = state.get("resume_data")
        if not blind_evaluation or not resume_data:
            return {"hiring_analytics": None}
        analytics_resume = JSONResume(**resume_data.model_dump(include={
            "work": True, "projects": True, "education": True
        }))
        hiring_analytics = await self.hiring_analytics_agent.process({
            "resume_data": analytics_resume,
            "blind_evaluation": blind_evaluation,
        })
        if blind_evaluation:
            blind_evaluation.hiring_analytics = hiring_analytics
            
        await self._add_audit_log(state, "HIRING_ANALYTICS", {
            "success_prob": hiring_analytics.success_probability if hiring_analytics else 0
        })

        return {"hiring_analytics": hiring_analytics}

    async def _node_candidate_experience(self, state: PipelineState) -> dict:
        await self._log(state, "--- Phase 3.6: Candidate Experience ---")
        blind_evaluation = state.get("blind_evaluation")
        resume_data = state.get("resume_data")
        if not blind_evaluation or not resume_data:
            return {"candidate_experience": None}
        experience_resume = JSONResume(**resume_data.model_dump(include={
            "basics": {"name"}, "work": True, "skills": True
        }))
        candidate_experience = await self.experience_agent.process({
            "resume_data": experience_resume,
            "blind_evaluation": blind_evaluation,
        })
        
        await self._add_audit_log(state, "CANDIDATE_EXPERIENCE_FEEDBACK", {
            "feedback_length": len(candidate_experience.get("feedback", "")) if candidate_experience else 0
        })

        return {"candidate_experience": candidate_experience}

    async def _node_persist_and_report(self, state: PipelineState) -> dict:
        await self._log(state, "--- Phase 4: Intelligence Storage & Report ---")
        resume_data = state.get("resume_data")
        blind_evaluation = state.get("blind_evaluation")
        identity_trust = state.get("identity_trust")
        app_quality = state.get("app_quality")
        skill_assessment = state.get("skill_assessment")
        github_data = state.get("github_data")
        hiring_analytics = state.get("hiring_analytics")
        candidate_experience = state.get("candidate_experience")

        # Build contribution map
        contribution_map: Dict[str, Any] = {}
        try:
            contribution_map = {
                "extraction": {
                    "agent": "ExtractionAgent",
                    "status": "Success",
                    "output_size": len(str(resume_data)),
                },
                "quality": {
                    "ai_probability": app_quality.ai_generated_probability if app_quality else 0,
                    "intent_score": app_quality.application_intent_score if app_quality else 0,
                },
                "trust": {
                    "score": identity_trust.identity_score if identity_trust else 0,
                    "flags": identity_trust.fraud_flags if identity_trust else [],
                    "linkedin": identity_trust.linkedin.linkedin_profile_score if (identity_trust and identity_trust.linkedin) else 0,
                    "github_auth": identity_trust.github.repo_authenticity_score if (identity_trust and identity_trust.github) else 0,
                    "email": identity_trust.email.email_legitimacy_score if (identity_trust and identity_trust.email) else 0,
                    "social_graph": identity_trust.social_graph_trust_score if identity_trust else 0,
                    "ai_resume": identity_trust.ai_resume_probability if identity_trust else 0,
                },
                "portfolio": {
                    "depth": identity_trust.portfolio.portfolio_score if (identity_trust and identity_trust.portfolio) else 0.0,
                    "complexity": identity_trust.portfolio.project_complexity if (identity_trust and identity_trust.portfolio) else "N/A",
                },
                "skills": {
                    "match": skill_assessment.skill_match_score if skill_assessment else 0,
                    "suggested_tasks": skill_assessment.suggested_tasks if skill_assessment else [],
                },
                "verification": {
                    "agent": "VerificationAgent",
                    "signals": ["GitHub"] if github_data else [],
                    "repos_found": len(github_data.get("projects", [])) if github_data else 0,
                },
                "evaluation": {
                    "agent": "BiasAuditAgent",
                    "anonymized": True,
                    "semantic_clusters": self.bias_audit_agent._enrich_skills_context(resume_data) if resume_data else [],
                },
                "analytics": {
                    "success_prob": hiring_analytics.success_probability if hiring_analytics else 0,
                },
                "experience": {
                    "feedback": candidate_experience.get("feedback", "") if (candidate_experience and isinstance(candidate_experience, dict)) else "",
                },
            }
        except Exception as e:
            self.logger.error(f"Error building contribution map: {e}")

        # Persist to vector store
        if blind_evaluation and resume_data:
            self._persist_candidate(
                state["pdf_path"], resume_data, blind_evaluation, contribution_map
            )

        # Serialize everything
        results: Dict[str, Any] = {
            "pdf_path": state.get("pdf_path"),
            "job_description": state.get("job_description"),
            "resume_data": resume_data,
            "github_data": github_data,
            "blind_evaluation": blind_evaluation,
            "identity_trust": identity_trust,
            "portfolio_intelligence": identity_trust.portfolio if identity_trust else None,
            "skill_assessment": skill_assessment,
            "hiring_analytics": hiring_analytics,
            "application_quality": app_quality,
            "candidate_experience": candidate_experience,
            "contribution_map": contribution_map,
        }

        def serialize(obj: Any) -> Any:
            if hasattr(obj, "dict"):
                return obj.dict()
            if hasattr(obj, "model_dump"):
                return obj.model_dump()
            return obj

        serializable_results = {k: serialize(v) for k, v in results.items()}

        # Report generation
        report_url = None
        if blind_evaluation:
            try:
                report_dir = "cache/reports"
                codebase_report_dir = "reports"
                os.makedirs(report_dir, exist_ok=True)
                os.makedirs(codebase_report_dir, exist_ok=True)

                report_filename = f"report_{os.path.basename(state['pdf_path'])}_{id(results)}.pdf"
                report_path = os.path.join(report_dir, report_filename)
                codebase_report_path = os.path.join(codebase_report_dir, report_filename)

                self.extraction_agent.handler.generate_evaluation_report(
                    serializable_results["blind_evaluation"], report_path
                )

                # Upload report to MinIO (fail-safe)
                report_object_key = f"reports/{report_filename}"
                try:
                    upload_file(report_path, report_object_key)
                    await self._log(state, f"Uploaded report to MinIO: {report_object_key}")
                    report_url = generate_presigned_url(report_object_key)
                except Exception as e:
                    self.logger.warning(f"Report upload skipped (MinIO unreachable): {e}")
                    report_url = None

                import shutil
                shutil.copy2(report_path, codebase_report_path)

                serializable_results["report_url"] = report_url or f"/reports/{report_filename}"
                await self._log(state, "Report generated.")
            except Exception as e:
                report_object_key = None
                self.logger.error(f"Failed to generate report: {e}")
                await self._log(state, f"Error generating report: {str(e)}")

        # Persist to PostgreSQL (Fail-safe)
        try:
            async with async_session_factory() as session:
                candidate = Candidate(
                    request_id=state.get("request_id", str(uuid.uuid4())),
                    tenant_id=state.get("tenant_id", uuid.UUID("00000000-0000-0000-0000-000000000000")), 
                    total_score=float(serializable_results["blind_evaluation"]["total_score"]) if blind_evaluation else 0.0,
                    status="complete" if blind_evaluation else "error",
                    result_data=serializable_results,
                    resume_object_key=state.get("resume_object_key"),
                    report_object_key=report_object_key
                )
                session.add(candidate)
                await session.commit()
                await self._log(state, "Persisted candidate record to PostgreSQL.")
        except Exception as e:
            self.logger.warning(f"Persistence skipped (DB unreachable): {e}")

        # Vector Store Persistence (Fail-safe)
        try:
            if blind_evaluation and resume_data:
                vector_store = CandidateVectorStore()
                await vector_store.add_candidate(
                    candidate_id=state.get("request_id", str(uuid.uuid4())),
                    resume_data=resume_data.model_dump(),
                    score=float(serializable_results["blind_evaluation"]["total_score"]),
                    tenant_id=state.get("tenant_id")
                )
                await self._log(state, "Added candidate to vector store.")
        except Exception as e:
            self.logger.warning(f"Vector search persistence skipped (Qdrant unreachable): {e}")

        # Normalize score
        if blind_evaluation:
            raw_score = blind_evaluation.total_score
            normalized_score = min(100, max(0, round((raw_score / 60) * 100)))
            serializable_results["blind_evaluation"]["total_score"] = normalized_score

        await self._log(state, "Pipeline run complete")
        return {
            "serializable_results": serializable_results, 
            "report_url": report_url,
            "report_object_key": report_object_key
        }

    # ------------------------------------------------------------------
    # Conditional edges
    # ------------------------------------------------------------------
    def _should_continue_after_extraction(self, state: PipelineState) -> str:
        """If extraction failed, go straight to END."""
        if state.get("resume_data") is None:
            return "end"
        return "continue"

    # ------------------------------------------------------------------
    # Build the LangGraph
    # ------------------------------------------------------------------
    def _build_graph(self) -> Any:
        """
        Build the DAG:
            extraction
                ↓ (conditional: fail → end)
            quality  ‖  verification    (parallel)
                ↓
            identity_trust  ‖  skill_assessment    (parallel)
                ↓
            bias_audit
                ↓
            hiring_analytics  ‖  candidate_experience    (parallel)
                ↓
            persist_and_report
                ↓
              END
        """
        graph = StateGraph(PipelineState)

        # Add nodes
        graph.add_node("extraction", self._node_extraction)
        graph.add_node("quality", self._node_quality)
        graph.add_node("verification", self._node_verification)
        graph.add_node("identity_trust", self._node_identity_trust)
        graph.add_node("skill_assessment", self._node_skill_assessment)
        graph.add_node("bias_audit", self._node_bias_audit)
        graph.add_node("hiring_analytics", self._node_hiring_analytics)
        graph.add_node("candidate_experience", self._node_candidate_experience)
        graph.add_node("persist_and_report", self._node_persist_and_report)

        # Entry point
        graph.set_entry_point("extraction")

        # After extraction: conditional continue or end
        graph.add_conditional_edges(
            "extraction",
            self._should_continue_after_extraction,
            {"continue": "quality", "end": END},
        )

        # quality → verification (parallel fan-out, both converge to identity_trust)
        graph.add_edge("quality", "verification")

        # After verification, fan out to identity_trust + skill_assessment in parallel
        graph.add_edge("verification", "identity_trust")
        graph.add_edge("verification", "skill_assessment")

        # Both converge into bias_audit
        graph.add_edge("identity_trust", "bias_audit")
        graph.add_edge("skill_assessment", "bias_audit")

        # After bias_audit, fan out to hiring_analytics + candidate_experience in parallel
        graph.add_edge("bias_audit", "hiring_analytics")
        graph.add_edge("bias_audit", "candidate_experience")

        # Both converge into persist_and_report
        graph.add_edge("hiring_analytics", "persist_and_report")
        graph.add_edge("candidate_experience", "persist_and_report")

        # Final
        graph.add_edge("persist_and_report", END)

        return graph.compile()

    # ------------------------------------------------------------------
    # Public API (backwards compatible)
    # ------------------------------------------------------------------
    async def run_pipeline(
        self,
        pdf_path: str,
        job_description: Optional[str] = None,
        on_log: Any = None,
        request_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Runs the complete multi-agent pipeline for a single resume."""
        initial_state: PipelineState = {
            "pdf_path": pdf_path,
            "job_description": job_description,
            "on_log": on_log,
            "request_id": request_id or str(uuid.uuid4()),
            "tenant_id": uuid.UUID(tenant_id) if tenant_id else uuid.UUID("00000000-0000-0000-0000-000000000000"),
            "start_time": asyncio.get_event_loop().time()
        }

        # Execute the graph
        final_state = await self._graph.ainvoke(initial_state)

        return final_state.get("serializable_results", {})

    # ------------------------------------------------------------------
    # Helpers (unchanged)
    # ------------------------------------------------------------------
    def _get_github_url(self, resume_data: JSONResume) -> Optional[str]:
        if not resume_data or not resume_data.basics or not resume_data.basics.profiles:
            return None
        for profile in resume_data.basics.profiles:
            if profile.network and profile.network.lower() == "github":
                return profile.url
        return None

    def _persist_candidate(
        self,
        path: str,
        resume: JSONResume,
        evaluation: EvaluationData,
        contribution_map: Optional[Dict] = None,
    ):
        """Stores the candidate profile and score in the vector database."""
        try:
            candidate_id = (
                resume.basics.email if (resume.basics and resume.basics.email) else path
            )
            total_score = evaluation.total_score

            metadata = {
                "score": float(total_score),
                "strengths": ", ".join(evaluation.key_strengths[:3]) if evaluation.key_strengths else "",
                "path": path,
                "trust_score": float(evaluation.identity_trust.identity_score) if evaluation.identity_trust else 0.0,
                "portfolio_depth": float(evaluation.portfolio_intelligence.portfolio_score) if evaluation.portfolio_intelligence else 0.0,
                "skill_match": float(evaluation.skill_assessment.skill_match_score) if evaluation.skill_assessment else 0.0,
                "success_prob": float(evaluation.hiring_analytics.success_probability) if evaluation.hiring_analytics else 0.0,
                "ai_prob": float(evaluation.application_quality.ai_generated_probability) if evaluation.application_quality else 0.0,
                "contribution_map": json.dumps(contribution_map) if contribution_map else "{}",
            }

            profile_summary = f"Skills: {', '.join([s.name for s in resume.skills]) if resume.skills else ''}. "
            profile_summary += f"Strengths: {metadata['strengths']}"

            self.vector_store.add_candidate(candidate_id, profile_summary, metadata)
        except Exception as e:
            self.logger.error(f"Failed to persist candidate: {str(e)}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
async def main():
    if len(sys.argv) < 2:
        print("Usage: python -m agents.orchestrator <pdf_path> [job_description_path or text]")
        return

    pdf_path = sys.argv[1]
    job_description = None
    if len(sys.argv) > 2:
        jd_input = sys.argv[2]
        if os.path.exists(jd_input):
            with open(jd_input, "r") as f:
                job_description = f.read()
        else:
            job_description = jd_input

    orchestrator = ATSOrchestrator()
    results = await orchestrator.run_pipeline(pdf_path, job_description)

    print("\n" + "=" * 40)
    print("PIPELINE EXECUTION RESULTS")
    print("=" * 40)
    if results.get("blind_evaluation"):
        print("Candidate: [REDACTED]")
        total = results["blind_evaluation"].get("total_score", 0)
        print(f"Blind Total Score: {total}")
    else:
        print("Evaluation failed.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    asyncio.run(main())
