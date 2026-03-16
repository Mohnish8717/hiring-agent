import asyncio
from typing import Optional
from agents.base_agent import Agent
from pdf import PDFHandler
from models import JSONResume

class ExtractionAgent(Agent):
    """Agent specialized in extracting structured data from PDF resumes."""
    
    def __init__(self):
        super().__init__("ExtractionAgent")
        self.handler = PDFHandler()

    async def process(self, pdf_path: str) -> Optional[JSONResume]:
        self.log_info(f"Starting extraction for: {pdf_path}")
        try:
            # Running synchronous PDF processing in a separate thread
            resume_data = await asyncio.to_thread(self.handler.extract_json_from_pdf, pdf_path)
            if resume_data:
                self.log_info("Extraction successful")
                return resume_data
            else:
                self.log_error("Extraction failed to produce data")
                return None
        except Exception as e:
            self.log_error(f"Error during extraction: {str(e)}")
            return None
