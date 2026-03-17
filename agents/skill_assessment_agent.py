import asyncio
import json
from typing import Dict, Any, Optional, List
from agents.base_agent import Agent # type: ignore
from models import AssessmentResult, JSONResume # type: ignore
from llm_utils import initialize_llm_provider, extract_json_from_response, get_model_for_task, ReasoningIntensity # type: ignore
from prompt import DEFAULT_MODEL # type: ignore

class SkillAssessmentAgent(Agent):
    """Agent specialized in validating skills via challenges and tasks."""
    
    def __init__(self):
        super().__init__("SkillAssessmentAgent")
        self.model_name = get_model_for_task(ReasoningIntensity.HIGH)
        self.provider = initialize_llm_provider(self.model_name)

    async def process(self, input_data: Dict[str, Any]) -> AssessmentResult:
        """
        Input: {
            "resume_data": JSONResume,
            "jd_text": Optional[str]
        }
        """
        resume_data: Optional[JSONResume] = input_data.get("resume_data")
        jd_text = input_data.get("jd_text", "Not provided")
        
        if not resume_data:
            self.log_error("No resume data provided for skill assessment")
            return AssessmentResult(
                skill_match_score=0.0,
                suggested_tasks=["Provide resume to generate specific challenges."],
                actual_capability_evidence="Incomplete data."
            )

        self.log_info(f"Generating assessment for {resume_data.basics.name if resume_data.basics else 'Unknown'}")
        
        # Identify core skills and gaps
        skills = [s.name for s in resume_data.skills] if resume_data.skills else []
        
        prompt = f"""
        Based on the candidate's skills and the Job Description, generate a tailored assessment.
        Skills: {', '.join(skills)}
        JD: {jd_text}
        
        Identify:
        1. A skill match score (0-10)
        2. Three specific technical challenges (system design, coding, or micro-tasks) tailored to this candidate.
        3. A summary of 'Real Capability' evidence based on their background.
        
        Return ONLY a JSON object with:
        {{
            "skill_match_score": float,
            "suggested_tasks": list of strings,
            "actual_capability_evidence": string
        }}
        """

        try:
            chat_params = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "options": {"temperature": 0.2}
            }
            response = await asyncio.to_thread(self.provider.chat, **chat_params)
            response_text = extract_json_from_response(response["message"]["content"])
            data = json.loads(response_text, strict=False)
            
            return AssessmentResult(
                skill_match_score=float(data.get("skill_match_score", 7.0)),
                suggested_tasks=list(data.get("suggested_tasks", [])),
                actual_capability_evidence=str(data.get("actual_capability_evidence", "Skill claims match professional profile."))
            )
        except Exception as e:
            self.log_error(f"Error generating assessment: {str(e)}")
            return AssessmentResult(
                skill_match_score=7.0,
                suggested_tasks=["System Design: Scalable Backend architecture", "Python: Design a decorator for rate limiting"],
                actual_capability_evidence="Assessment generation failed, showing defaults."
            )
