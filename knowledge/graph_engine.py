import json
import os
import logging
from typing import List, Set, Dict, Optional, Any, cast

class SkillsGraphEngine:
    """Engine to traverse and query the technical skills knowledge graph."""
    
    def __init__(self, graph_path: str = "knowledge/skills_graph.json"):
        self.logger = logging.getLogger("graph_engine")
        self.graph_path = graph_path
        self.categories: Dict[str, List[str]] = {}
        self.relationships: Dict[str, Dict] = {}
        self.aliases: Dict[str, str] = {}
        self._load_graph()

    def _load_graph(self):
        try:
            if not os.path.exists(self.graph_path):
                self.logger.warning(f"Graph file not found at {self.graph_path}. Initializing empty.")
                return
            
            with open(self.graph_path, 'r') as f:
                data = json.load(f)
                self.categories = data.get("categories", {})
                self.relationships = data.get("relationships", {})
                self.aliases = data.get("aliases", {})
            self.logger.info(f"Successfully loaded skills graph with {len(self.categories)} categories.")
        except Exception as e:
            self.logger.error(f"Error loading skills graph: {str(e)}")

    def get_skill_category(self, skill_name: str) -> List[str]:
        """Find the categories a skill belongs to."""
        # Check explicit relationships first
        if skill_name in self.relationships:
            return self.relationships[skill_name].get("parents", [])
        
        # Search through categories
        found_categories = []
        for cat, skills in self.categories.items():
            if skill_name.lower() in [s.lower() for s in skills]:
                found_categories.append(cat)
        return found_categories

    def get_related_skills(self, skill_name: str) -> Set[str]:
        """Find skills related to the given skill (siblings or associated)."""
        related = set()
        
        # 1. Check explicit related list
        if skill_name in self.relationships:
            related.update(self.relationships[skill_name].get("related", []))
            
        # 2. Add skills from the same categories (siblings)
        categories = self.get_skill_category(skill_name)
        for cat in categories:
            related.update(self.categories.get(cat, []))
            
        # Remove original skill from result
        if skill_name in related:
            related.remove(skill_name)
            
        return related

    def is_skill_in_category(self, skill_name: str, category: str) -> bool:
        """Check if a skill belongs to a specific category (e.g., 'React' in 'Frontend')."""
        categories = self.get_skill_category(skill_name)
        return category in categories or category.lower() in [c.lower() for c in categories]

    def normalize_skill(self, skill_name: str) -> str:
        """Resolve aliases (e.g., 'ML' -> 'Machine Learning')."""
        return self.aliases.get(skill_name.upper(), skill_name)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = SkillsGraphEngine()
    print(f"Categories for Python: {engine.get_skill_category('Python')}")
    related_skills: List[str] = sorted(list(engine.get_related_skills('React')))
    print(f"Related to React: {cast(List[Any], related_skills)[:5]}...") # type: ignore
    print(f"Is NumPy in Data Science? {engine.is_skill_in_category('NumPy', 'Data Science')}")
