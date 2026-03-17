import asyncio
import logging
import os
from agents.orchestrator import ATSOrchestrator

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("run_pipeline_test")

async def main():
    # Ensure cache directory exists for report generation
    os.makedirs("cache/reports", exist_ok=True)
    os.makedirs("cache/uploads", exist_ok=True)

    orchestrator = ATSOrchestrator()
    
    pdf_path = "Mohnish_Resume.pdf"
    job_description = "Senior AI Engineer with focus on Agentic workflows, LangGraph, and RAG architectures."
    
    print("\n🚀 Starting Real-World Pipeline Test for: ", pdf_path)
    print("="*60)

    def on_log(msg):
        print(f"  [LOG] {msg}")

    try:
        results = await orchestrator.run_pipeline(
            pdf_path=pdf_path,
            job_description=job_description,
            on_log=on_log
        )
        
        print("\n" + "="*60)
        print("✅ Pipeline Completed Successfully!")
        
        if "blind_evaluation" in results:
            score = results["blind_evaluation"].get("total_score", "N/A")
            print(f"📊 Final Score: {score}/100")
            print(f"💡 Key Strengths: {results['blind_evaluation'].get('key_strengths', [])}")
            
        print("\n📂 Report Location: ", results.get("report_url", "Local only in cache/reports/"))
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed during testing: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
