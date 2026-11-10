import json
import os
from typing import Dict, Any, List
from engine.parser import ParsedQuestion
from engine.detectors.deterministic import DeterministicDetectors

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

def run_bank_sweep():
    with open(os.path.join(DATA_DIR, "questions.json")) as f:
        questions = json.load(f)
    with open(os.path.join(DATA_DIR, "reports.json")) as f:
        reports = json.load(f)

    reported_qids = set(r["questionId"] for r in reports)
    total_bank_estimate = 800_000
    sample_size = len(questions)

    # Track detector frequencies
    detector_counts = {}
    unreported_defects = []
    all_findings = []

    for q in questions:
        pq = ParsedQuestion(q)
        hits = DeterministicDetectors.run_all(pq)
        qid = pq.qid
        is_reported = qid in reported_qids

        for h in hits:
            cls_name = h.defect_class
            detector_counts[cls_name] = detector_counts.get(cls_name, 0) + 1
            finding = {
                "questionId": qid,
                "is_reported": is_reported,
                "defect_class": cls_name,
                "evidence": h.evidence,
                "span": h.span
            }
            all_findings.append(finding)
            if not is_reported:
                unreported_defects.append(finding)

    # Compute statistical extrapolation to ~8 lakh question bank
    extrapolations = {}
    for d_class, count in detector_counts.items():
        sample_rate = count / sample_size
        est_bank_occurrences = int(sample_rate * total_bank_estimate)
        # Margin of error (95% confidence interval for proportion)
        import math
        z = 1.96
        stderr = math.sqrt((sample_rate * (1 - sample_rate)) / sample_size)
        ci_lower = max(0, int((sample_rate - z * stderr) * total_bank_estimate))
        ci_upper = int((sample_rate + z * stderr) * total_bank_estimate)
        extrapolations[d_class] = {
            "sample_occurrences": count,
            "sample_rate_percent": round(sample_rate * 100, 2),
            "estimated_in_8_lakh_bank": est_bank_occurrences,
            "ci_95_percent": [ci_lower, ci_upper]
        }

    sweep_report = {
        "sample_size": sample_size,
        "reported_questions_in_sample": len(reported_qids),
        "unreported_questions_in_sample": sample_size - len(reported_qids),
        "total_detector_hits": len(all_findings),
        "unreported_defects_found": unreported_defects,
        "defect_class_extrapolations": extrapolations
    }

    with open(os.path.join(DATA_DIR, "sweep_results.json"), "w") as f:
        json.dump(sweep_report, f, indent=2)

    return sweep_report

if __name__ == "__main__":
    report = run_bank_sweep()
    print(f"=== DEFECT-CLASS SWEEP COMPLETED ===")
    print(f"Sample: {report['sample_size']} questions | Total Detector Hits: {report['total_detector_hits']}")
    print(f"Unreported defects discovered by sweep: {len(report['unreported_defects_found'])}")
    for d_cls, ext in report['defect_class_extrapolations'].items():
        print(f" -> {d_cls:18}: {ext['sample_occurrences']}/{report['sample_size']} ({ext['sample_rate_percent']}%) ~ {ext['estimated_in_8_lakh_bank']:,} questions in 8-lakh bank [CI: {ext['ci_95_percent'][0]:,} - {ext['ci_95_percent'][1]:,}]")
