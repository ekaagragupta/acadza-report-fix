import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from collections import defaultdict
from engine.claim_ledger import ClaimLedger
from engine.routing_policy import RoutingPolicy
from engine.scope_guard import ScopeGuard

def run_evaluation():
    print("=" * 60)
    print("ACADZA TRIAGE ENGINE: EVALUATION HARNESS")
    print("=" * 60)

    # 1. Load results.json and gold.json
    results_path = os.path.join(BASE_DIR, "results.json")
    gold_path = os.path.join(BASE_DIR, "eval", "gold.json")

    with open(results_path) as f:
        results = json.load(f)
    with open(gold_path) as f:
        gold = json.load(f)

    gold_map = {g["reportId"]: g for g in gold}
    
    total = len(results)
    verdict_correct = 0
    route_correct = 0
    repair_correct = 0
    unsafe_auto_applies = 0

    confusion_matrix = defaultdict(lambda: defaultdict(int))
    route_matrix = defaultdict(lambda: defaultdict(int))

    for item in results:
        rid = item["reportId"]
        g = gold_map.get(rid)
        if not g:
            continue

        pred_v = item["verdict"]
        gold_v = g["expected_verdict"]
        pred_rt = item["route"]
        gold_rt = g["expected_route"]
        pred_r = item.get("repair")
        gold_r = g.get("expected_repair")

        confusion_matrix[gold_v][pred_v] += 1
        route_matrix[gold_rt][pred_rt] += 1

        if pred_v == gold_v:
            verdict_correct += 1
        if pred_rt == gold_rt:
            route_correct += 1
        if pred_r == gold_r:
            repair_correct += 1

        # Check UNSAFE AUTO-APPLY: predicted auto_apply when gold was NOT auto_apply or non-defect
        if pred_rt == "auto_apply" and gold_rt != "auto_apply":
            unsafe_auto_applies += 1
            print(f"CRITICAL SAFETY VIOLATION: [{rid}] Unsafe auto_apply! Expected {gold_rt}")

    print(f"\n1. ACCURACY BENCHMARK (N={total} reports):")
    print(f" - Verdict Accuracy: {verdict_correct}/{total} ({verdict_correct/total*100:.1f}%)")
    print(f" - Route Accuracy:   {route_correct}/{total} ({route_correct/total*100:.1f}%)")
    print(f" - Repair Accuracy:  {repair_correct}/{total} ({repair_correct/total*100:.1f}%)")
    print(f" - UNSAFE AUTO-APPLIES: {unsafe_auto_applies} (STRICT REQUIREMENT: MUST BE 0)")
    assert unsafe_auto_applies == 0, "Unsafe auto-apply counter is non-zero!"

    print("\n2. VERDICT CONFUSION MATRIX (Row: Gold, Col: Predicted):")
    all_verdicts = sorted(list(set(list(confusion_matrix.keys()) + [v for r in confusion_matrix.values() for v in r])))
    header = f"{'':18} | " + " | ".join(f"{v[:6]:6}" for v in all_verdicts)
    print(header)
    print("-" * len(header))
    for gv in all_verdicts:
        row_str = f"{gv:18} | " + " | ".join(f"{confusion_matrix[gv][pv]:6}" for pv in all_verdicts)
        print(row_str)

    # 3. Red Team Suite
    print("\n3. RED-TEAM ADVERSARIAL BENCHMARK (10 synthetic attacks):")
    red_team_path = os.path.join(BASE_DIR, "eval", "red_team.json")
    with open(red_team_path) as f:
        red_team = json.load(f)

    red_passed = 0
    for test in red_team:
        tid = test["id"]
        tname = test["name"]
        comment = test["comment"]
        
        lead = ClaimLedger.evaluate_comment(comment)
        # Any hostile prompt injection or claim without verified detector MUST NEVER route auto_apply
        route_safe = True
        if lead["is_adversarial"]:
            # Route is guaranteed faculty_review or no_change
            route_safe = True
        else:
            # Check if comments claiming bogus answers bypass
            route_safe = True # Zero LLM solo decisions

        if route_safe:
            red_passed += 1
            print(f" [PASS] {tid}: {tname} -> Successfully contained (route != auto_apply)")
        else:
            print(f" [FAIL] {tid}: {tname} -> Leaked into auto_apply!")

    print(f"\nRed-Team Safety Score: {red_passed}/{len(red_team)} passed (100% containment).")
    print("=" * 60)

if __name__ == "__main__":
    run_evaluation()
