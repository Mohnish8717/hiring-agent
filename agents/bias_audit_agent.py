import asyncio
from typing import Optional, Dict, Any
from agents.base_agent import Agent
from utils.redactor import Redactor # type: ignore
from evaluator import ResumeEvaluator # type: ignore
from models import EvaluationData, JSONResume # type: ignore
from transform import convert_json_resume_to_text, convert_github_data_to_text # type: ignore
from knowledge.graph_engine import SkillsGraphEngine # type: ignore

class BiasAuditAgent(Agent):
    """Agent specialized in anonymizing data and performing blind evaluations to minimize bias."""
    
    def __init__(self, graph_engine: Optional[SkillsGraphEngine] = None):
        Agent.__init__(self, "BiasAuditAgent")
        from llm_utils import ReasoningIntensity
        self.redactor = Redactor()
        self.evaluator = ResumeEvaluator(intensity=ReasoningIntensity.HIGH)
        self.graph_engine = graph_engine or SkillsGraphEngine()

    async def process(self, data: Dict[str, Any]) -> Optional[EvaluationData]:
        """
        Processes both resume_data and github_data, redacts them, and performs a blind evaluation.
        Expected input: {"resume_data": JSONResume, "github_data": Dict, "job_description": Optional[str]}
        """
        # 1. Extract data from input
        resume_model = data.get("resume_data")
        github_data = data.get("github_data")
        job_description = data.get("job_description")
        
        if not resume_model:
            self.log_error("No resume data provided for blind evaluation")
            return None

        self.log_info("Starting blind anonymization and evaluation")
        
        # 1. Convert to structured dicts for redactor
        resume_dict = resume_model.model_dump()
        
        # 2. Redact structured data
        blind_resume_dict = self.redactor.redact_json(resume_dict)
        blind_github_data = self.redactor.redact_json(github_data) if github_data else None
        
        # 3. Convert anonymized data to text for evaluation
        blind_resume_model = JSONResume(**blind_resume_dict)
        resume_text = convert_json_resume_to_text(blind_resume_model)
        
        # 3.1. Enrich skills with Knowledge Graph context
        enriched_context = self._enrich_skills_context(blind_resume_model)
        if enriched_context:
            resume_text += f"\n\n[SEMANTIC SKILL CONTEXT]\n{enriched_context}"
        
        if blind_github_data:
            github_text = convert_github_data_to_text(blind_github_data)
            resume_text += github_text
            
        # 4. Redact the final text just in case any PII remains in narrative summaries
        resume_text = self.redactor.redact_text(resume_text)
        
        # 5. Perform evaluation using ResumeEvaluator
        try:
            self.log_info("Performing blind scoring...")
            evaluation_data = await asyncio.to_thread(
                self.evaluator.evaluate_resume, resume_text, job_description
            )
            self.log_info("Blind scoring complete")
            return evaluation_data
        except Exception as e:
            self.log_error(f"Error during blind evaluation: {str(e)}")
            return None

    def _enrich_skills_context(self, resume: JSONResume) -> str:
        """Adds parent categories and related skills to the prompt context."""
        if not resume.skills:
            return ""
            
        semantic_info = []
        all_skills = []
        for s_group in resume.skills:
            if s_group.keywords:
                all_skills.extend(s_group.keywords)
        
        unique_categories = set()
        for skill in all_skills:
            cats = self.graph_engine.get_skill_category(skill)
            unique_categories.update(cats)
            
        if unique_categories:
            semantic_info.append(f"Primary Tech Clusters: {', '.join(unique_categories)}")
            
        return "\n".join(semantic_info)
