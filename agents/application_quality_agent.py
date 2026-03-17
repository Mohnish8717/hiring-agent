import asyncio
import json
from typing import Dict, Any, Optional
from agents.base_agent import Agent # type: ignore
from models import ApplicationQualityResult, JSONResume # type: ignore
from llm_utils import initialize_llm_provider, extract_json_from_response, get_model_for_task, ReasoningIntensity # type: ignore
from prompt import DEFAULT_MODEL # type: ignore

class ApplicationQualityAgent(Agent):
    """Agent specialized in detecting AI-generated spam and application intent."""
    
    def __init__(self):
        super().__init__("ApplicationQualityAgent")
        self.model_name = get_model_for_task(ReasoningIntensity.LOW)
        self.provider = initialize_llm_provider(self.model_name)

    async def process(self, input_data: Dict[str, Any]) -> ApplicationQualityResult:
        """
        Input: {
            "resume_text": str
        }
        """
        resume_text = input_data.get("resume_text", "")
        
        if not resume_text:
            self.log_error("No resume text provided for quality analysis")
            return ApplicationQualityResult(
                ai_generated_probability=0.0,
                application_intent_score=0.0,
                is_spam=True,
                spam_signals=["Missing application content"]
            )

        self.log_info("Analyzing application quality and AI-generation probability")
        
        prompt = f"""
        Analyze the following resume text for AI generation patterns and application quality:
        
        Resume Content:
        {resume_text[:2000]}
        
        Analyze for:
        1. Generic phrasing patterns
        2. Perfect LLM grammar patterns
        3. Low specificity
        4. Repetitive structure
        5. Buzzword density vs substance
        6. Suspicious metrics without context
        7. Lack of technical depth
        
        Metrics:
        1. AI-generated probability (0.0-1.0)
        2. Application intent score (0-10, based on personalization vs generic buzzwords)
        3. Is this application likely spam?
        4. List specific spam signals found.
        
        Return ONLY a JSON object with:
        {{
            "ai_generated_probability": float,
            "application_intent_score": float,
            "is_spam": boolean,
            "spam_signals": list of strings
        }}
        """

        try:
            chat_params = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "options": {"temperature": 0.1}
            }
            response = await asyncio.to_thread(self.provider.chat, **chat_params)
            response_text = extract_json_from_response(response["message"]["content"])
            data = json.loads(response_text, strict=False)
            
            return ApplicationQualityResult(
                ai_generated_probability=float(data.get("ai_generated_probability", 0.1)),
                application_intent_score=float(data.get("application_intent_score", 8.0)),
                is_spam=bool(data.get("is_spam", False)),
                spam_signals=list(data.get("spam_signals", []))
            )
        except Exception as e:
            self.log_error(f"Error analyzing app quality: {str(e)}")
            return ApplicationQualityResult(
                ai_generated_probability=0.0,
                application_intent_score=5.0,
                is_spam=False,
                spam_signals=["Quality analysis failed"]
            )
