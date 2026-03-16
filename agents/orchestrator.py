import logging
import asyncio
import sys
import os
from typing import Dict, Any, Optional
from agents.extraction_agent import ExtractionAgent # type: ignore
from agents.verification_agent import VerificationAgent # type: ignore
from agents.bias_audit_agent import BiasAuditAgent # type: ignore
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

    async def run_pipeline(self, pdf_path: str, job_description: Optional[str] = None) -> Dict[str, Any]:
        """Runs the complete multi-agent pipeline for a single resume."""
        results: Dict[str, Any] = {
            "pdf_path": pdf_path,
            "job_description": job_description,
            "resume_data": None,
            "github_data": None,
            "blind_evaluation": None
        }

        # 1. Extraction Phase
        self.logger.info("--- Phase 1: Extraction ---")
        resume_data = await self.extraction_agent.process(pdf_path)
        if not resume_data:
            self.logger.error("Pipeline failed at extraction phase")
            return results
        results["resume_data"] = resume_data

        # 2. Verification Phase (GitHub)
        self.logger.info("--- Phase 2: Verification ---")
        github_url = self._get_github_url(resume_data)
        github_data = None
        if github_url:
            github_data = await self.verification_agent.process(github_url)
            results["github_data"] = github_data
        else:
            self.logger.info("No GitHub URL found, skipping verification")

        # 3. Bias Audit & Evaluation Phase
        self.logger.info("--- Phase 3: Bias Audit & Evaluation ---")
        evaluation_input = {
            "resume_data": resume_data,
            "github_data": github_data,
            "job_description": job_description
        }
        blind_evaluation = await self.bias_audit_agent.process(evaluation_input)
        results["blind_evaluation"] = blind_evaluation

        # 3.1. Generate Contribution Map for XAI
        results["contribution_map"] = {
            "extraction": {
                "agent": "ExtractionAgent",
                "status": "Success",
                "output_size": len(str(resume_data))
            },
            "verification": {
                "agent": "VerificationAgent",
                "signals": ["GitHub"] if github_data else [],
                "repos_found": len(github_data.repositories) if (github_data and hasattr(github_data, 'repositories')) else 0
            },
            "evaluation": {
                "agent": "BiasAuditAgent",
                "anonymized": True,
                "semantic_clusters": self.bias_audit_agent._enrich_skills_context(resume_data)
            }
        }

        # 4. Memory Persistence (Vector Store)
        self.logger.info("--- Phase 4: Intelligence Storage ---")
        if blind_evaluation:
            self._persist_candidate(pdf_path, resume_data, blind_evaluation)

        self.logger.info("Pipeline run complete")
        return results

    def _get_github_url(self, resume_data: JSONResume) -> Optional[str]:
        if not resume_data or not resume_data.basics or not resume_data.basics.profiles:
            return None
        for profile in resume_data.basics.profiles:
            if profile.network and profile.network.lower() == "github":
                return profile.url
        return None

    def _persist_candidate(self, path: str, resume: JSONResume, evaluation: EvaluationData):
        """Stores the candidate profile and score in the vector database."""
        try:
            candidate_id = resume.basics.email if (resume.basics and resume.basics.email) else path
            # Prepare metadata (redacted)
            metadata = {
                "score": float(evaluation.score) if hasattr(evaluation, 'score') else 0.0,
                "strengths": ", ".join(evaluation.key_strengths[:3]) if evaluation.key_strengths else "",
                "path": path
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
        total = scores.open_source.score + scores.self_projects.score + scores.production.score + scores.technical_skills.score
        print(f"Blind Total Score: {total:.1f}")
        print(f"Evidence: {scores.open_source.evidence[:100]}...")
    else:
        print("Evaluation failed.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    asyncio.run(main())
