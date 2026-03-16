from fastapi import FastAPI, Request, Query # type: ignore
from fastapi.responses import HTMLResponse # type: ignore
from fastapi.templating import Jinja2Templates # type: ignore
from fastapi.staticfiles import StaticFiles # type: ignore
from fastapi.responses import StreamingResponse # type: ignore
import os
import io
import csv
import json
from db.vector_store import CandidateVectorStore
from knowledge.graph_engine import SkillsGraphEngine
from typing import List, Dict, Any

app = FastAPI(title="Hiring Agent Dashboard")
templates = Jinja2Templates(directory="dashboard/templates")

# Initialize modules
vector_store = CandidateVectorStore()
graph_engine = SkillsGraphEngine()

@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/candidates")
async def get_candidates():
    """Fetch all indexed candidates from the vector store."""
    try:
        # ChromaDB doesn't have a direct 'get_all' but we can fetch by querying with empty data or getting all IDs
        # For simplicity, we query with a broad term or get all items if possible
        results = vector_store.collection.get()
        candidates = []
        for i in range(len(results["ids"])):
            candidates.append({
                "id": results["ids"][i],
                "document": results["documents"][i],
                "metadata": results["metadatas"][i]
            })
        return candidates
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/query")
async def query_candidates(q: str = Query(...)):
    """Perform semantic search for candidates."""
    try:
        results = vector_store.query_similar(q, n_results=10)
        candidates = []
        for i in range(len(results["ids"][0])):
            candidates.append({
                "id": results["ids"][0][i],
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i]
            })
        return candidates
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/skills")
async def get_skills_graph():
    """Returns the skills hierarchy for visualization."""
    return graph_engine.categories

@app.get("/api/export/csv")
async def export_csv():
    """Export all candidates to CSV."""
    results = vector_store.collection.get()
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow(["Email", "Name", "Total Score", "Skills", "Production Level", "Summary"])
    
    for meta in results["metadatas"]:
        writer.writerow([
            meta.get("email"),
            meta.get("name"),
            meta.get("total_score"),
            meta.get("tech_clusters"),
            meta.get("production_score"),
            meta.get("summary")
        ])
    
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=candidates.csv"}
    )

@app.get("/api/export/json")
async def export_json():
    """Export all candidates to JSON."""
    results = vector_store.collection.get()
    candidates = []
    for i in range(len(results["ids"])):
        candidates.append({
            "id": results["ids"][i],
            "metadata": results["metadatas"][i]
        })
    
    content = json.dumps(candidates, indent=2)
    return StreamingResponse(
        io.StringIO(content),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=candidates.json"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
