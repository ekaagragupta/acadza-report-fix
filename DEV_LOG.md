# Engineering Dev Log: Acadza "Report -> Fix" Loop

## Session Started: 2026-11-10T14:30:00+05:30

### Phase 1: Parser & Deterministic Detectors
- **Action**: Explored dataset (`questions.json`, `reports.json`, `taxonomy.json`).
- **Discovery**: 43 questions, 44 reports across 39 unique questions. 4 questions completely unreported.
- **Challenge**: Parsing options `(A), (B), (C), (D)` inside unstructured HTML/MathML strings. 
  - *Correction*: In Assertion-Reason questions (e.g. `695ee00b88d7701e561aabc5`), `Assertion (A)` was naive-matched as an option marker `(A)`. Added negative lookbehind for `Assertion` to ensure accurate 4-option parsing.
- **Detector Implementation**: Zero-LLM deterministic detectors implemented for:
  - `detect_missing_or_blank_option` (`option_repair`)
  - `detect_identical_options` (`identical_options`, auto: false)
  - `detect_exam_reference` (`exam_reference`)
  - `detect_markup_leak` (`markup_leak`)
  - `detect_noise` (`noise`)
  - `detect_diagram_missing` (`diagram`, auto: false)
  - `detect_key_solution_mismatch` (`answer_key` / `solution_fix`)
- **Unit Test Suite**: Created `tests/test_detectors.py` with 8 test cases. All 8 tests passing (`Ran 8 tests in 0.020s, OK`).

### Phase 2: Claim Ledger, Scope Guard, Replay Check, Routing Policy & Student Replies
- **Claim Ledger**: Built zero-trust lead parser in `engine/claim_ledger.py`. Detects prompt injection (e.g. R027), gibberish/empty comments (R041), app/display issues (R036, R037, R038), language mode (R039), and chapter/syllabus mismatches (R023, R026, R042).
- **Scope Guard**: Built mechanical safety guard in `engine/scope_guard.py`. Guarantees exact count == 1 for `find` strings, forbids editing fields outside `taxonomy.json`, protects numbers/math nodes during spelling/noise edits, requires option edits to leave stem byte-identical, and enforces additive-only changes for `answer_form`.
- **Replay Check**: Implemented in `engine/replay_check.py`. Verifies proof of fix by applying the edit to a copy and re-running all deterministic detectors to ensure original defect is eliminated and zero new defects are introduced.
- **Routing Policy**: Implemented in `engine/routing_policy.py`. Enforces strict asymmetric risk minimization: false negatives (sending to faculty) over wrong auto-edits. Prevents auto-applying `auto: false` taxonomy items, injection attempts, and single-lead unverified claims.
- **Student Reply Generator**: Built empathetic, jargon-free 1-3 sentence generator in `engine/student_reply.py`.
- **Phase 2 Tests**: Created `tests/test_phase2.py` with 9 unit tests covering injection detection, scope guard invariants, routing policy, and student reply generation. All 17 tests across the project passing (`Ran 17 tests in 0.021s, OK`).

### Phase 3: Results Generation, Bank Defect Sweep & Evaluation Harness
- **results.json**: Generated full output for all 44 reports matching README schema.
  - Verified against closed keys in `taxonomy.json`: 0 errors.
  - Verified route safety: 0 illegal auto-applies on non-defects, 0 auto-applies for `auto: false` taxonomy items.
- **Defect-Class Sweep**:
  - Swept all 43 questions through deterministic detectors.
  - Computed sample defect rates (e.g. 4.65% for missing/blank options, 4.65% for answer key mismatches, 4.65% for markup leaks).
  - Extrapolated to 800,000 question bank with 95% confidence intervals (~37,209 questions each in 8-lakh bank).
- **Evaluation Harness & Red Team Suite**:
  - Built `eval/evaluate.py`, comparing against `eval/gold.json`.
  - Outputted Verdict Confusion Matrix, Route Accuracy, and asserted `unsafe_auto_apply == 0`.
  - Created `eval/red_team.json` with 10 synthetic hostile attacks (prompt injection, authority spoofing, SQL injection payload, math hallucination, emoji spam, field scope break attempt).
  - Red-Team containment score: 10/10 (100% containment).

### Phase 4: Faculty Review Console
- **UX & Visual Identity**: Designed for a fatigued faculty reviewer triaging dozens of cases at 10 PM. Chose an editorial dark palette (`#0c0e12` deep charcoal background, `#14181f` elevated slate surface, `#242b35` borders, sky/emerald accents) and typography pairing (`Inter` UI, `JetBrains Mono` for metadata/equations, and native browser MathML rendering). Avoided generic purple AI gradients.
- **Queue Prioritization**: Grouped 44 reports by question into 39 unique cases. Priority score formula: $Severity \times Exposure (reporters) \times Urgency (needsHuman)$. Hovering reveals the exact calculation.
- **Fast Action & Verification**:
  - Word/span level before/after diff highlights modified sections.
  - 5-chip verification ledger (Detector, Solver 3/3, Solution Match, Scope Guard, Replay).
  - One-click keyboard shortcuts (`J`/`K` navigation, `A` approve, `E` edit reply, `R` reject, `?` help modal).
  - Exportable local audit log preserving timestamp, reviewer, action, and edited replies.
  - Interactive "Bank Sweep" modal demonstrating class-level extrapolation to the 800,000 question bank.
- **Production Build**: Successfully built static single-page app via Vite (`npm run build` completed cleanly, generating standalone static assets in `console/dist/` ready for zero-cost deployment).

### Phase 5: Documentation & Submission Scaffolds
- **PROMPTS.md**: Authored comprehensive prompt orchestration log:
  - In-product system prompts verbatim (Blind Solver, Surgical Edit Synthesizer, Empathetic Student Reply) with version evolution.
  - Verbatim logs of user/assistant prompting during build.
  - Documented "3 moments the AI was wrong and how I caught it" (Assertion-Reason option splitting, ambiguous `<br />` find string, Gauss's law flux misinterpretation in R005).
  - Design decisions matrix (tried, dropped, adopted, and rationale).
- **PRODUCT.md**: Documented product strategy & thesis:
  - Stakeholder risk analysis: why earnest self-studying students in Tier-2/3 towns without coaching lose the most.
  - Strict invariants on what must never be auto-applied under asymmetric risk.
  - Week-1 metric: Faculty Override Rate on Auto-Applied Fixes (< 0.1%).
  - Beyond-the-brief idea: Defect-Class Sweep & Continuous Ingestion Linter for question banks.
- **README.md**: Comprehensive guide with Mermaid pipeline architecture diagram, local run instructions, faculty review console design rationale, evaluation results table, and the 5 weakest points of the build.
- **Final System Check**: Ran complete unit test suite (`17/17 passed in 0.025s`), `eval/evaluate.py` (`44/44 accuracy, 0 unsafe auto-applies, 10/10 red-team containment`), and verified frontend production build in `console/dist`.




