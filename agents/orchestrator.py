import logging
import asyncio
import sys
import os
import json
from typing import Dict, Any, Optional
from agents.extraction_agent import ExtractionAgent # type: ignore
from agents.verification_agent import VerificationAgent # type: ignore
from agents.bias_audit_agent import BiasAuditAgent # type: ignore
from agents.identity_trust_agent import IdentityTrustAgent # type: ignore
from agents.skill_assessment_agent import SkillAssessmentAgent # type: ignore
from agents.hiring_analytics_agent import HiringAnalyticsAgent # type: ignore
from agents.application_quality_agent import ApplicationQualityAgent # type: ignore
from agents.candidate_experience_agent import CandidateExperienceAgent # type: ignore
from knowledge.graph_engine import SkillsGraphEngine # type: ignore
from db.vector_store import CandidateVectorStore # type: ignore
from models import JSONResume, EvaluationData # type: ignore

class ATSOrchestrator:
    """Central orchestrator managing the multi-agent ATS pipeline."""
    
    def __init__(self):
        self.logger = logging.getLogger("orchestrator")
        self.graph_engine = SkillsGraphEngine()
        self.vector_store = CandidateVectorStore()
        
        self.extraction_agent = ExtractionAgent()
        self.verification_agent = VerificationAgent()
        self.bias_audit_agent = BiasAuditAgent(graph_engine=self.graph_engine)
        self.identity_trust_agent = IdentityTrustAgent()
        self.skill_assessment_agent = SkillAssessmentAgent()
        self.hiring_analytics_agent = HiringAnalyticsAgent()
        self.quality_agent = ApplicationQualityAgent()
        self.experience_agent = CandidateExperienceAgent()

    async def run_pipeline(self, pdf_path: str, job_description: Optional[str] = None, on_log = None) -> Dict[str, Any]:
        """Runs the complete multi-agent pipeline for a single resume."""
        
        async def stream_log(msg: str):
            self.logger.info(msg)
            if on_log:
                if asyncio.iscoroutinefunction(on_log):
                    await on_log(msg)
                else:
                    on_log(msg)

        results: Dict[str, Any] = {
            "pdf_path": pdf_path,
            "job_description": job_description,
            "resume_data": None,
            "github_data": None,
            "blind_evaluation": None,
            "identity_trust": None,
            "portfolio_intelligence": None,
            "skill_assessment": None,
            "hiring_analytics": None,
            "application_quality": None,
            "candidate_experience": None
        }

        # 1. Extraction Phase
        await stream_log("--- Phase 1: Extraction ---")
        resume_data = await self.extraction_agent.process(pdf_path)
        if not resume_data:
            await stream_log("Extraction failed.")
            return results
        results["resume_data"] = resume_data

        # 1.5. Application Quality Detection
        await stream_log("--- Phase 1.5: Application Quality ---")
        # Optimization: Pass only relevant sections for quality detection
        quality_input = resume_data.model_dump(include={
            "basics": {"summary"},
            "work": True,
            "projects": True
        })
        app_quality = await self.quality_agent.process({"resume_text": json.dumps(quality_input)})
        results["application_quality"] = app_quality

        # 2. Verification Phase (GitHub)
        await stream_log("--- Phase 2: Verification ---")
        github_url = self._get_github_url(resume_data)
        github_data = None
        if github_url:
            await stream_log(f"GitHub URL found: {github_url}")
            github_data = await self.verification_agent.process(github_url)
            results["github_data"] = github_data
        else:
            await stream_log("No GitHub URL found, skipping verification")

        # 2.1. Identity Trust Agent
        await stream_log("--- Phase 2.1: Identity Trust ---")
        identity_trust = await self.identity_trust_agent.process({
            "resume_data": resume_data,
            "github_data": github_data,
            "ai_probability": app_quality.ai_generated_probability if app_quality else None
        })
        results["identity_trust"] = identity_trust

        # --- Phase 2.2: Skill Assessment ---
        await stream_log("--- Phase 2.2: Skill Assessment ---")
        # Optimization: Filter for skills, work, and projects
        assessment_resume = JSONResume(**resume_data.model_dump(include={
            "basics": {"name"},
            "skills": True,
            "work": True,
            "projects": True
        }))
        skill_assessment = await self.skill_assessment_agent.process({
            "resume_data": assessment_resume,
            "jd_text": job_description
        })
        results["skill_assessment"] = skill_assessment


        # 3. Bias Audit & Evaluation Phase
        await stream_log("--- Phase 3: Bias Audit & Evaluation ---")
        evaluation_input = {
            "resume_data": resume_data,
            "github_data": github_data,
            "job_description": job_description
        }
        blind_evaluation = await self.bias_audit_agent.process(evaluation_input)
        results["blind_evaluation"] = blind_evaluation
        
        # Merge next-gen signals into evaluation data for dashbaord
        if blind_evaluation:
            blind_evaluation.identity_trust = identity_trust
            blind_evaluation.portfolio_intelligence = identity_trust.portfolio
            blind_evaluation.skill_assessment = skill_assessment
            blind_evaluation.application_quality = app_quality
            
            # 3.5. Hiring Analytics
            await stream_log("--- Phase 3.5: Hiring Analytics ---")
            # Optimization: Filter for work, projects, and education
            analytics_resume = JSONResume(**resume_data.model_dump(include={
                "work": True,
                "projects": True,
                "education": True
            }))
            hiring_analytics = await self.hiring_analytics_agent.process({
                "resume_data": analytics_resume,
                "blind_evaluation": blind_evaluation
            })
            blind_evaluation.hiring_analytics = hiring_analytics
            results["hiring_analytics"] = hiring_analytics

            # 3.6. Candidate Experience
            await stream_log("--- Phase 3.6: Candidate Experience ---")
            # Optimization: Filter for basics, work, and skills
            experience_resume = JSONResume(**resume_data.model_dump(include={
                "basics": {"name"},
                "work": True,
                "skills": True
            }))
            candidate_experience = await self.experience_agent.process({
                "resume_data": experience_resume,
                "blind_evaluation": blind_evaluation
            })
            results["candidate_experience"] = candidate_experience
            
        # 3.1. Generate Contribution Map for XAI
        results["contribution_map"] = {
            "extraction": {
                "agent": "ExtractionAgent",
                "status": "Success",
                "output_size": len(str(resume_data))
            },
            "quality": {
                "ai_probability": app_quality.ai_generated_probability,
                "intent_score": app_quality.application_intent_score
            },
            "trust": {
                "score": identity_trust.identity_score,
                "flags": identity_trust.fraud_flags,
                "linkedin": identity_trust.linkedin.linkedin_profile_score if identity_trust.linkedin else 0,
                "github_auth": identity_trust.github.repo_authenticity_score if identity_trust.github else 0,
                "email": identity_trust.email.email_legitimacy_score if identity_trust.email else 0,
                "social_graph": identity_trust.social_graph_trust_score,
                "ai_resume": identity_trust.ai_resume_probability
            },
            "portfolio": {
                 "depth": identity_trust.portfolio.portfolio_score if identity_trust.portfolio else 0.0,
                 "complexity": identity_trust.portfolio.project_complexity if identity_trust.portfolio else "N/A"
            },
            "skills": {
                "match": skill_assessment.skill_match_score,
                "suggested_tasks": skill_assessment.suggested_tasks
            },
            "verification": {
                "agent": "VerificationAgent",
                "signals": ["GitHub"] if github_data else [],
                "repos_found": len(github_data.get('projects', [])) if github_data else 0
            },
            "evaluation": {
                "agent": "BiasAuditAgent",
                "anonymized": True,
                "semantic_clusters": self.bias_audit_agent._enrich_skills_context(resume_data)
            },
            "analytics": {
                "success_prob": results["hiring_analytics"].success_probability if results.get("hiring_analytics") else 0
            },
            "experience": {
                "feedback": results["candidate_experience"].get("feedback", "") if results.get("candidate_experience") else ""
            }
        }


        # 4. Memory Persistence (Vector Store)
        await stream_log("--- Phase 4: Intelligence Storage ---")
        if blind_evaluation:
            self._persist_candidate(pdf_path, resume_data, blind_evaluation, results.get("contribution_map"))

        await stream_log("Pipeline run complete")
        
        # Ensure everything is a serializable dict for SSE/API
        def serialize(obj):
            if hasattr(obj, "dict"): return obj.dict()
            if hasattr(obj, "model_dump"): return obj.model_dump()
            return obj

        serializable_results = {k: serialize(v) for k, v in results.items()}
        # Explicitly add total_score as it's a property and won't be in model_dump
        if blind_evaluation:
            serializable_results["blind_evaluation"]["total_score"] = blind_evaluation.total_score
            
        return serializable_results

    def _get_github_url(self, resume_data: JSONResume) -> Optional[str]:
        if not resume_data or not resume_data.basics or not resume_data.basics.profiles:
            return None
        for profile in resume_data.basics.profiles:
            if profile.network and profile.network.lower() == "github":
                return profile.url
        return None

    def _persist_candidate(self, path: str, resume: JSONResume, evaluation: EvaluationData, contribution_map: Optional[Dict] = None):
        """Stores the candidate profile and score in the vector database."""
        try:
            candidate_id = resume.basics.email if (resume.basics and resume.basics.email) else path
            # Use centralized total_score calculation
            total_score = evaluation.total_score
            
            # Prepare metadata (redacted)
            metadata = {
                "score": float(total_score),
                "strengths": ", ".join(evaluation.key_strengths[:3]) if evaluation.key_strengths else "",
                "path": path,
                "trust_score": float(evaluation.identity_trust.identity_score) if evaluation.identity_trust else 0.0,
                "portfolio_depth": float(evaluation.portfolio_intelligence.portfolio_score) if evaluation.portfolio_intelligence else 0.0,


                "skill_match": float(evaluation.skill_assessment.skill_match_score) if evaluation.skill_assessment else 0.0,
                "success_prob": float(evaluation.hiring_analytics.success_probability) if evaluation.hiring_analytics else 0.0,
                "ai_prob": float(evaluation.application_quality.ai_generated_probability) if evaluation.application_quality else 0.0,
                "contribution_map": json.dumps(contribution_map) if contribution_map else "{}"
            }
            # Profile text for semantic indexing
            profile_summary = f"Skills: {', '.join([s.name for s in resume.skills]) if resume.skills else ''}. "
            profile_summary += f"Strengths: {metadata['strengths']}"
            
            self.vector_store.add_candidate(candidate_id, profile_summary, metadata)
        except Exception as e:
            self.logger.error(f"Failed to persist candidate: {str(e)}")

async def main():
    if len(sys.argv) < 2:
        print("Usage: python -m agents.orchestrator <pdf_path> [job_description_path or text]")
        return

    pdf_path = sys.argv[1]
    job_description = None
    if len(sys.argv) > 2:
        jd_input = sys.argv[2]
        if os.path.exists(jd_input):
            with open(jd_input, 'r') as f:
                job_description = f.read()
        else:
            job_description = jd_input

    orchestrator = ATSOrchestrator()
    results = await orchestrator.run_pipeline(pdf_path, job_description)
    
    print("\n" + "="*40)
    print("PIPELINE EXECUTION RESULTS")
    print("="*40)
    if results["blind_evaluation"]:
        print(f"Candidate: [REDACTED]")
        scores = results['blind_evaluation'].scores
        total = results['blind_evaluation'].total_score
        print(f"Blind Total Score: {total:.1f}")
        print(f"Evidence: {scores.open_source.evidence[:100]}...")
    else:
        print("Evaluation failed.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    asyncio.run(main())
