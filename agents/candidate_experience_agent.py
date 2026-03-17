import asyncio
import json
from typing import Dict, Any, Optional, List
from agents.base_agent import Agent # type: ignore
from models import EvaluationData, JSONResume # type: ignore
from llm_utils import initialize_llm_provider, extract_json_from_response, get_model_for_task, ReasoningIntensity # type: ignore
from prompt import DEFAULT_MODEL # type: ignore

class CandidateExperienceAgent(Agent):
    """Agent specialized in candidate transparency and feedback."""
    
    def __init__(self):
        super().__init__("CandidateExperienceAgent")
        self.model_name = get_model_for_task(ReasoningIntensity.LOW)
        self.provider = initialize_llm_provider(self.model_name)

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Input: {
            "resume_data": JSONResume,
            "blind_evaluation": EvaluationData
        }
        """
        resume_data: Optional[JSONResume] = input_data.get("resume_data")
        evaluation: Optional[EvaluationData] = input_data.get("blind_evaluation")
        
        if not resume_data or not evaluation:
            self.log_error("Missing data for candidate experience insights")
            return {
                "feedback": "Review in progress.",
                "prep_tips": ["Review project core concepts"],
                "match_transparency": 5.0
            }

        self.log_info(f"Generating experience insights for {resume_data.basics.name if resume_data.basics else 'Unknown'}")
        
        prompt = f"""
        Generate a candidate transparency report based on this evaluation:
        Scores: {evaluation.scores if evaluation.scores else 'N/A'}
        Strengths: {', '.join(evaluation.key_strengths) if evaluation.key_strengths else 'None'}
        Improvements: {', '.join(evaluation.areas_for_improvement) if evaluation.areas_for_improvement else 'None'}
        
        Provide:
        1. A friendly explanation of the decision reasoning.
        2. Three specific interview preparation suggestions based on their gaps.
        3. A 'Skill Match' summary for the candidate.
        
        Return ONLY a JSON object with:
        {{
            "feedback_summary": string,
            "interview_prep_tips": list of strings,
            "candidate_transparency_score": float
        }}
        """

        try:
            chat_params = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "options": {"temperature": 0.3}
            }
            response = await asyncio.to_thread(self.provider.chat, **chat_params)
            response_text = extract_json_from_response(response["message"]["content"])
            data = json.loads(response_text, strict=False)
            
            return {
                "feedback": str(data.get("feedback_summary", "Your background is impressive.")),
                "prep_tips": list(data.get("interview_prep_tips", [])),
                "match_transparency": float(data.get("candidate_transparency_score", 8.5))
            }
        except Exception as e:
            self.log_error(f"Error generating feedback: {str(e)}")
            return {
                "feedback": "Thank you for your application. We are currently reviewing your profile.",
                "prep_tips": ["Review common technical interview questions"],
                "match_transparency": 5.0
            }
