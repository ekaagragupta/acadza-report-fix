"""
ROUTING POLICY DECISION TABLE

Asymmetric Risk Principle:
A false negative (sending a fix to human review) costs 15 seconds of faculty time.
A false positive (auto-applying a broken/wrong fix or accepting a malicious injection) damages 
trust for lakhs of students and alters live examination rankings.
Therefore: WE ASYMMETRICALLY PREFER FALSE NEGATIVES TO UNSAFE AUTO-EDITS.

Policy Rules:
1. NEVER auto_apply:
   - If verdict != 'defect' -> route is 'no_change'
   - If repair.auto == false in taxonomy.json (e.g. identical_options, diagram, unsound, syllabus, wrong_chapter) -> route MUST be 'faculty_review'
   - If report has adversarial / prompt-injection flag -> route MUST be 'faculty_review'
   - If evidence came ONLY from the student's comment without independent detector or solver confirmation -> route MUST be 'faculty_review'
   - If answer_key change does not have 3-way agreement (Solver 3/3 + Solution match) -> route MUST be 'faculty_review'
   - If Scope Guard failed or Replay Check failed -> route MUST be 'faculty_review'
   - If Confidence < 0.90 -> route MUST be 'faculty_review'

2. auto_apply ONLY WHEN ALL CONDITIONS MET:
   - verdict == 'defect'
   - taxonomy repair has 'auto: true'
   - proposed_edit is surgical and scope guard passed (count == 1, permitted fields only, invariant checks)
   - replay check passed (original defect eliminated, 0 regressions)
   - confidence >= 0.90
   - not adversarial
"""

import json
import os
from typing import Dict, Any, Optional

TAXONOMY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "taxonomy.json")

class RoutingPolicy:
    def __init__(self, taxonomy_path: str = TAXONOMY_FILE):
        with open(taxonomy_path) as f:
            tax = json.load(f)
            self.repairs = tax.get("repairs", {})

    def determine_route(
        self,
        verdict: str,
        repair: Optional[str],
        confidence: float,
        guard_passed: bool,
        replay_passed: bool,
        is_adversarial: bool,
        independent_verified: bool
    ) -> str:
        # 1. Non-defects -> no_change
        if verdict != "defect":
            return "no_change"

        # 2. Adversarial flag -> faculty_review
        if is_adversarial:
            return "faculty_review"

        # 3. Check taxonomy auto allowance
        if not repair:
            return "faculty_review"

        rep_meta = self.repairs.get(repair, {})
        if not rep_meta.get("auto", False):
            return "faculty_review"

        # 4. Independent verification requirement
        if not independent_verified:
            return "faculty_review"

        # 5. Guard & Replay mechanical gates
        if not guard_passed or not replay_passed:
            return "faculty_review"

        # 6. Confidence threshold (0.90)
        if confidence < 0.90:
            return "faculty_review"

        # All gates passed
        return "auto_apply"
