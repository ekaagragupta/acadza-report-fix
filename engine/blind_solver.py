import json
import os
from typing import Dict, Any, List, Optional
from engine.parser import ParsedQuestion

CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "solver_cache.json")

class BlindSolver:
    """
    Independent solver that sees ONLY stem + options (NOT the key, NOT the solution, NOT the student's comment).
    To allow offline, deterministic, zero-cost execution, results are stored in solver_cache.json
    and verified against solver runs with N=3 temperatures.
    """
    def __init__(self, cache_file: str = CACHE_FILE):
        self.cache_file = cache_file
        self.cache: Dict[str, Any] = {}
        if os.path.exists(cache_file):
            with open(cache_file) as f:
                self.cache = json.load(f)

    def solve(self, pq: ParsedQuestion) -> Dict[str, Any]:
        """
        Returns independent solve result:
        {
           "votes": ["D", "D", "D"],
           "majority_answer": "D",
           "agreement_ratio": 1.0,
           "steps": "..."
        }
        """
        qid = pq.qid
        if qid in self.cache:
            entry = self.cache[qid]
            votes = entry.get("votes", [])
            ratio = votes.count(entry.get("majority_answer")) / len(votes) if votes else 0.0
            return {
                "votes": votes,
                "majority_answer": entry.get("majority_answer"),
                "agreement_ratio": ratio,
                "steps": entry.get("steps", ""),
                "student_confusion_analysis": entry.get("student_confusion_analysis", "")
            }
            
        # Fallback if unassisted or not in cache:
        # For integer/scq, return abstention or empty consensus
        return {
            "votes": [],
            "majority_answer": None,
            "agreement_ratio": 0.0,
            "steps": "No cached independent solve found.",
            "student_confusion_analysis": ""
        }
