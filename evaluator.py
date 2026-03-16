from typing import Dict, List, Optional, Tuple, Any # type: ignore
from pydantic import BaseModel, Field, field_validator # type: ignore
from models import JSONResume, EvaluationData # type: ignore
from llm_utils import initialize_llm_provider, extract_json_from_response # type: ignore
import logging # type: ignore
import json # type: ignore
import re # type: ignore

MAX_BONUS_POINTS = 20
MIN_FINAL_SCORE = -20
MAX_FINAL_SCORE = 120

from prompt import ( # type: ignore
    DEFAULT_MODEL,
    MODEL_PARAMETERS,
    MODEL_PROVIDER_MAPPING,
    GEMINI_API_KEY,
)
from prompts.template_manager import TemplateManager # type: ignore

logger = logging.getLogger(__name__)


class ResumeEvaluator:
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        model_params: Optional[Dict[str, Any]] = None,
    ):
        if not model_name:
            raise ValueError("Model name cannot be empty")

        self.model_name = model_name
        self.model_params = model_params or MODEL_PARAMETERS.get(
            model_name, {"temperature": 0.5, "top_p": 0.9}
        )
        self.template_manager = TemplateManager()
        self.provider: Any = None
        self._last_resume_text: Optional[str] = None
        self._initialize_llm_provider()

    def _initialize_llm_provider(self):
        """Initialize the appropriate LLM provider based on the model."""
        self.provider = initialize_llm_provider(self.model_name)

    def _load_evaluation_prompt(self, resume_text: str, job_description: Optional[str] = None) -> str:
        criteria_template = self.template_manager.render_template(
            "resume_evaluation_criteria", 
            text_content=resume_text,
            job_description=job_description
        )
        if criteria_template is None:
            raise ValueError("Failed to load resume evaluation criteria template")
        return criteria_template

    def evaluate_resume(self, resume_text: str, job_description: Optional[str] = None) -> EvaluationData:
        self._last_resume_text = resume_text
        full_prompt = self._load_evaluation_prompt(resume_text, job_description)
        return self._evaluate_with_model(full_prompt, self.model_name, self.provider)

    def _evaluate_with_model(self, full_prompt: str, model_name: str, provider: Any) -> EvaluationData:
        try:
            system_message = self.template_manager.render_template(
                "resume_evaluation_system_message"
            )
            if system_message is None:
                raise ValueError("Failed to load resume evaluation system message template")

            chat_params = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": full_prompt},
                ],
                "options": {
                    "stream": False,
                    "temperature": self.model_params.get("temperature", 0.5),
                    "top_p": self.model_params.get("top_p", 0.9),
                },
            }

            kwargs = {"format": EvaluationData.model_json_schema()}
            response = provider.chat(**chat_params, **kwargs)

            response_text = response["message"]["content"]
            response_text = extract_json_from_response(response_text)
            
            evaluation_dict = json.loads(response_text)
            return EvaluationData(**evaluation_dict)

        except Exception as e:
            logger.error(f"Error evaluating with model {model_name}: {str(e)}")
            raise

    async def evaluate_resume_ensemble(self, resume_text: str, job_description: Optional[str] = None) -> Tuple[EvaluationData, Dict[str, Any]]:
        """
        Runs an ensemble evaluation using both Gemini and Ollama.
        Returns the primary evaluation and a consensus report.
        """
        full_prompt = self._load_evaluation_prompt(resume_text, job_description)
        
        # 1. Run primary model (e.g. Gemini/DEFAULT_MODEL)
        primary_eval = self._evaluate_with_model(full_prompt, self.model_name, self.provider)
        
        # 2. Run fallback model (e.g. Ollama if primary is Gemini, or vice versa)
        secondary_model = "gemma3:4b" if "gemini" in self.model_name.lower() else "gemini-2.0-flash"
        secondary_provider = initialize_llm_provider(secondary_model)
        
        try:
            secondary_eval = self._evaluate_with_model(full_prompt, secondary_model, secondary_provider)
            
            # Simple consensus check: calculate variance in total scores
            score1 = self._calculate_total_score(primary_eval)
            score2 = self._calculate_total_score(secondary_eval)
            variance = abs(score1 - score2)
            
            consensus_report = {
                "primary_score": score1,
                "secondary_score": score2,
                "variance": variance,
                "consensus": "HIGH" if variance < 10 else "LOW",
                "warning": "High score variance detected between models. Manual review recommended." if variance >= 15 else None
            }
            return primary_eval, consensus_report
        except Exception as e:
            logger.warning(f"Secondary model evaluation failed, falling back to primary: {e}")
            return primary_eval, {"consensus": "SKIPPED", "error": str(e)}

    def _calculate_total_score(self, eval_data: EvaluationData) -> float:
        s = eval_data.scores
        base = s.open_source.score + s.self_projects.score + s.production.score + s.technical_skills.score
        return base + eval_data.bonus_points.total - eval_data.deductions.total
