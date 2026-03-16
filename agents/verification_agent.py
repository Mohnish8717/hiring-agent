import asyncio
from typing import Optional, Dict
from agents.base_agent import Agent
from github import fetch_and_display_github_info

class VerificationAgent(Agent):
    """Agent specialized in verifying resume claims against external sources (e.g., GitHub)."""
    
    def __init__(self):
        super().__init__("VerificationAgent")

    async def process(self, github_url: str) -> Optional[Dict]:
        if not github_url:
            self.log_info("No GitHub URL provided for verification")
            return None
            
        self.log_info(f"Verifying GitHub profile: {github_url}")
        try:
            # Running network-bound fetch in a separate thread
            github_data = await asyncio.to_thread(fetch_and_display_github_info, github_url)
            if github_data:
                self.log_info("GitHub verification successful")
                return github_data
            else:
                self.log_error("Failed to fetch GitHub data")
                return None
        except Exception as e:
            self.log_error(f"Error during verification: {str(e)}")
            return None
