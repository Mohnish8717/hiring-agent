from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging

class Agent(ABC):
    """Abstract base class for all agents in the ATS system."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")
        self.context: Dict[str, Any] = {}

    @abstractmethod
    async def process(self, input_data: Any) -> Any:
        """Core processing logic for the agent."""
        pass

    def update_context(self, data: Dict[str, Any]):
        """Update the agent's internal context."""
        self.context.update(data)

    def log_info(self, message: str):
        self.logger.info(f"[{self.name}] {message}")

    def log_error(self, message: str):
        self.logger.error(f"[{self.name}] {message}")
