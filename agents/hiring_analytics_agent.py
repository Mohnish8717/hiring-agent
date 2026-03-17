import asyncio
import json
from typing import Dict, Any, Optional
from agents.base_agent import Agent # type: ignore
from models import AnalyticsResult, JSONResume, EvaluationData # type: ignore
from llm_utils import initialize_llm_provider, extract_json_from_response, get_model_for_task, ReasoningIntensity # type: ignore
from prompt import DEFAULT_MODEL # type: ignore

class HiringAnalyticsAgent(Agent):
    """Agent specialized in predictive hiring analytics and team fit."""
    
    def __init__(self):
        super().__init__("HiringAnalyticsAgent")
        self.model_name = get_model_for_task(ReasoningIntensity.HIGH)
        self.provider = initialize_llm_provider(self.model_name)

    async def process(self, input_data: Dict[str, Any]) -> AnalyticsResult:
        """
        Input: {
            "resume_data": JSONResume,
            "blind_evaluation": EvaluationData
        }
        """
        resume_data: Optional[JSONResume] = input_data.get("resume_data")
        evaluation: Optional[EvaluationData] = input_data.get("blind_evaluation")
        
        if not resume_data or not evaluation:
            self.log_error("Missing resume_data or evaluation for hiring analytics")
            return AnalyticsResult(
                success_probability=0.0,
                team_fit_likelihood=0.0,
                attrition_risk=1.0,
                retention_prediction="Insufficient data to perform analytics.",
                salary_estimate_band="N/A"
            )

        self.log_info(f"Generating analytics for {resume_data.basics.name if resume_data.basics else 'Unknown'}")
        
        # Analyze strengths vs work history for retention prediction
        prompt = f"""
        Predict hiring analytics for the following candidate:
        Strengths: {', '.join(evaluation.key_strengths) if evaluation.key_strengths else 'None'}
        Work History: {len(resume_data.work) if resume_data.work else 0} positions
        
        Provide:
        1. Success probability (0.0-1.0)
        2. Team fit likelihood (0.0-1.0)
        3. Attrition risk (0.0-1.0)
        4. Detailed retention prediction reasoning
        5. Salary band estimate (e.g., "$120k - $150k")
        
        Return ONLY a JSON object with:
        {{
            "success_probability": float,
            "team_fit_likelihood": float,
            "attrition_risk": float,
            "retention_prediction": string,
            "salary_estimate_band": string
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
            
            return AnalyticsResult(
                success_probability=float(data.get("success_probability", 0.8)),
                team_fit_likelihood=float(data.get("team_fit_likelihood", 0.85)),
                attrition_risk=float(data.get("attrition_risk", 0.1)),
                retention_prediction=str(data.get("retention_prediction", "Stable indicator based on history.")),
                salary_estimate_band=str(data.get("salary_estimate_band", "Competitive"))
            )
        except Exception as e:
            self.log_error(f"Error generating analytics: {str(e)}")
            return AnalyticsResult(
                success_probability=0.75,
                team_fit_likelihood=0.8,
                attrition_risk=0.15,
                retention_prediction="Analytics generation failed, showing base projection.",
                salary_estimate_band="TBD"
            )
