"""
Confidence Engine:
Computes confidence as a deterministic weighted function of observable evidence signals,
never self-reported by an LLM.

Formula:
  Confidence = w_det * I(detector_hit) 
             + w_solver * AgreementRatio(solver_3_votes)
             + w_sol * I(solution_agrees)
             + w_guard * I(scope_guard_passed)
             + w_replay * I(replay_passed)
             + w_corrob * min(1.0, (distinct_reports - 1) * 0.1)

Calibration Note:
- For pure 'no_error' where student is wrong and all solvers agree with key: confidence ~ 0.94 - 0.98
- For verified defects with multi-way agreement + guard + replay: confidence ~ 0.92 - 0.99
- For uncorroborated ambiguous claims: confidence drops < 0.70, forcing human review or abstention.
"""

from typing import Dict, Any, Optional

def compute_confidence(
    detector_hit: bool,
    solver_ratio: float,
    solution_agreement: bool,
    guard_passed: bool,
    replay_passed: bool,
    report_count: int,
    verdict: str,
    repair_type: Optional[str] = None
) -> float:
    # Special cases:
    # 1. Non-content verdicts (app_issue, display_issue, language_mode, not_actionable)
    if verdict in ["app_issue", "display_issue", "language_mode", "not_actionable"]:
        return 0.95

    # 2. Defect with zero edit needed (auto: false like diagram, identical_options, syllabus, wrong_chapter)
    if verdict == "defect" and repair_type in ["diagram", "identical_options", "syllabus", "wrong_chapter", "wrong_question"]:
        base = 0.85
        if detector_hit:
            base += 0.10
        if report_count > 1:
            base += 0.03
        return min(0.98, round(base, 2))

    # 3. no_error (Question is sound, student misread / calculated wrongly)
    if verdict == "no_error":
        base = 0.85
        if solver_ratio >= 0.99:
            base += 0.10
        if solution_agreement:
            base += 0.03
        return min(0.98, round(base, 2))

    # 4. Defect with repair:
    score = 0.0
    # Weights sum to 1.0
    w_det = 0.30
    w_solver = 0.25
    w_sol = 0.15
    w_guard = 0.15
    w_replay = 0.10
    w_corrob = 0.05

    score += w_det if detector_hit else 0.0
    score += w_solver * solver_ratio
    score += w_sol if solution_agreement else 0.0
    score += w_guard if guard_passed else 0.0
    score += w_replay if replay_passed else 0.0
    
    corrob_boost = min(1.0, (report_count - 1) * 0.5) * w_corrob
    score += corrob_boost

    # Base baseline for cleanly analyzed items
    final_conf = max(0.50, min(0.99, score))
    return round(final_conf, 2)
