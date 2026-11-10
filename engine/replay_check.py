from typing import Dict, Any, List, Optional
from engine.parser import ParsedQuestion
from engine.detectors.deterministic import DeterministicDetectors
from engine.scope_guard import ScopeGuard

class ReplayCheck:
    """
    Replay Check:
    Applies the candidate edit to a copy of the question and re-runs deterministic detectors.
    Proof of fix is verified when:
    1. The original detector hit is completely eliminated.
    2. Zero new detector hits are introduced (no regression).
    """

    @staticmethod
    def verify_replay(
        raw_question_dict: Dict[str, Any],
        proposed_edit: Optional[Dict[str, Any]],
        expected_repaired_class: Optional[str] = None
    ) -> Dict[str, Any]:
        if not proposed_edit:
            return {
                "replay_passed": True,
                "reason": "No edit proposed; replay trivial pass",
                "original_eliminated": True,
                "regressions": []
            }

        guard = ScopeGuard()
        cloned_q = guard.apply_edit_to_copy(raw_question_dict, proposed_edit)
        pq_after = ParsedQuestion(cloned_q)
        
        hits_after = DeterministicDetectors.run_all(pq_after)
        hit_classes_after = [h.defect_class for h in hits_after]

        # 1. Did original defect disappear?
        original_eliminated = True
        if expected_repaired_class and expected_repaired_class in hit_classes_after:
            original_eliminated = False

        # 2. Are there any other unexpected hits?
        regressions = [h.defect_class for h in hits_after if h.defect_class != expected_repaired_class]

        replay_passed = original_eliminated and len(regressions) == 0

        return {
            "replay_passed": replay_passed,
            "original_eliminated": original_eliminated,
            "regressions": regressions,
            "hits_after": [h.to_dict() for h in hits_after],
            "reason": "Proof of fix verified: original defect eradicated with 0 regressions" if replay_passed else f"Replay check failed: original_eliminated={original_eliminated}, regressions={regressions}"
        }
