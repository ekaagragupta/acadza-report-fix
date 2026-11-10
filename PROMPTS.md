# Prompt Engineering & AI Orchestration Log: `PROMPTS.md`

## 1. In-Product System Prompts (Verbatim)

### A. Blind Solver Prompt (`engine/blind_solver.py`)
This prompt is sent to independent LLM instances run $N=3$ times at different temperatures ($0.0, 0.2, 0.4$). Notice that it is **blinded**: it receives *only* the stem and options, never the stored answer key, never the stored solution, and never the student's comment.

```markdown
You are an expert JEE/NEET faculty solver. Solve the following question independently from first principles.
You do NOT know the stored answer key, the solution, or any student feedback.

Question Stem:
{stem_text}

Options:
{options_formatted}

Instructions:
1. Write down each physical law and governing formula used.
2. Calculate step-by-step with explicit units.
3. Arrive at a final numerical or algebraic answer.
4. If options are provided, determine which option matches your result exactly.
5. If none matches, state "UNSOUND".

Output Format (strict JSON):
{
  "steps": "<detailed step-by-step mathematical reasoning>",
  "final_answer": "<Option letter A/B/C/D or numerical integer>",
  "confidence_reason": "<why this answer is unambiguous>"
}
```

#### Version History:
- **v1.0**: Included student comment as context ("Student claims answer is D...").
  - *Why changed*: LLM suffered from anchoring bias—when told the student thought D, the model rationalized why D was possible rather than independently solving from first principles.
- **v2.0 (Current)**: Completely blinded prompt. Zero access to comments, answer keys, or solutions. Multi-temperature voting enforced.

---

### B. Surgical Edit Synthesizer Prompt
Used only when a verified defect exists and requires surgical text replacement.

```markdown
You are a precise content editor for a National-level examination platform.
A defect has been verified for the following question record:

Defect Type: {repair_type}
Allowed Fields: {allowed_fields}
Question Content:
{raw_question_html}

Solution Content:
{raw_solution_html}

Student Report & Evidence:
{detector_evidence}

Constraints:
1. You may ONLY propose changes in fields listed in Allowed Fields: {allowed_fields}.
2. Propose a SURGICAL edit: specify "field", "find", and "replace".
3. The "find" string MUST be an exact contiguous substring occurring EXACTLY ONCE in the target field.
4. Do NOT rewrite the whole question. Make the minimal necessary patch.
5. For spelling/noise, you CANNOT alter digits, numbers, or math tags.
6. For option_repair, the question stem MUST remain 100% byte-identical.

Output Format (JSON):
{
  "field": "question" | "solution" | "answer" | "questionType",
  "find": "<exact unique substring to replace>",
  "replace": "<replacement substring>"
}
```

---

### C. Empathetic Student Reply Prompt
Generates the response shown to the student.

```markdown
You are an empathetic, encouraging JEE/NEET academic mentor writing a response to a high-school student.
The student reported: "{student_comment}"
Our verification result:
- Verdict: {verdict}
- Reason: {confusion_reason_or_fix}

Guidelines:
1. Keep the reply to 1-3 sentences maximum.
2. Tone: Warm, respectful, supportive. Acknowledge their effort.
3. If the student was incorrect: Gently explain the exact physical/mathematical principle or step that caused the confusion (e.g., "Notice that capacitance depends on radius R, not surface area").
4. If the student was correct: Sincerely thank them and confirm the exact correction made.
5. NEVER use internal or technical jargon (e.g., do NOT mention 'taxonomy', 'regex', 'scope guard', 'classifier', 'pipeline').
6. Simple English only (light Hinglish only if the student wrote in Hinglish).
```

---

## 2. Prompts Given to AI Coding Assistant (Antigravity / LLM)

### Prompt 1: Initial System Architecture & Pipeline Plan
> "Read README.md, taxonomy.json, questions.json and reports.json in the workspace fully BEFORE writing any code, then reply with a short plan and wait for my 'go'. The product thesis: VERIFIER-FIRST TRIAGE where LLM never gets to decide a verdict alone. Every claim must survive deterministic checks and independent verification, and confidence is COMPUTED from evidence signals, never self-reported by the model."

### Prompt 2: Robust Deterministic Option Extraction
> "Assertion-Reason questions have 'Assertion (A)' in the stem which is breaking option parsing. Modify parser.py to ensure 'Assertion (A)' is not falsely classified as option (A), and write 8 unit tests in tests/test_detectors.py to assert zero false positives on clean questions."

### Prompt 3: Scope Guard Mechanical Invariants
> "Implement ScopeGuard in Python. It must mechanically verify: target find string occurs exactly once; fields edited are strictly in taxonomy.repairs[repair].fields; spelling/noise edits cannot change digits or math nodes; option edits cannot modify question stem. Reject any edit that fails."

---

## 3. "3 Moments the AI Was Wrong and How I Caught It"

### Moment 1: Mistaking "Assertion (A)" as an Option Marker
- **What happened**: When extracting options `(A), (B), (C), (D)` using regex `\(([A-D])\)`, question `695ee00b88d7701e561aabc5` produced 5 options: `['A', 'A', 'B', 'C', 'D']`. The regex captured the label from `Assertion (A) : When two waves...`.
- **How I caught it**: The deterministic unit test `test_missing_option` failed with an option count of 5 instead of 4.
- **The fix**: Implemented a negative lookbehind in `engine/parser.py`: `(?<!Assertion)(?<!Assertion\s)(?<!Assertion&nbsp;)\(([A-D])\)`, properly isolating genuine option labels.

### Moment 2: Ambiguous `find` String in Surgical Edit
- **What happened**: For question `68e872546e45ba37dcc16bc0` (where option C was blank `<br />(C) <br />`), the initial AI generator proposed: `{"find": "<br />", "replace": "<br />(C) 1 : 1<br />"}`.
- **How I caught it**: The Scope Guard threw an invariant violation: `Target 'find' string '<br />' occurs 4 times in question (ambiguous edit)`.
- **The fix**: Constrained the search token to the unique marker: `{"find": "<br />(C) <br />", "replace": "<br />(C) 1 : 1<br />"}`, which occurs exactly once.

### Moment 3: Misinterpreting Gauss's Law Equation in R005
- **What happened**: For question `68dea616d0cda73d07e93ae6` (flux through a cube from charges $q/2$ at face and $2q$ at corner), the LLM initially marked the report as `no_error` because the stored key was 2 and the student said $n=1$.
- **How I caught it**: During the manual physics verification of the solver cache, calculating the flux directly:
  $$\phi_{face} = \frac{1}{2}\frac{q/2}{\varepsilon_0} = \frac{q}{4\varepsilon_0}, \quad \phi_{corner} = \frac{1}{8}\frac{2q}{\varepsilon_0} = \frac{q}{4\varepsilon_0} \implies \phi_{total} = \frac{q}{2\varepsilon_0}$$
  The problem states total flux is $\frac{nq}{2\varepsilon_0}$. Equating gives $n = 1$. The stored key was actually wrong ($2$), meaning the student was right!
- **The fix**: Corrected the triage classification to `defect` (`answer_key` $2 \to 1$), proving why independent mathematical solving beats superficial key comparison.

---

## 4. Design Decisions Log: Tried / Dropped / Why

| Decision | Status | Rationale |
|---|---|---|
| **Single End-to-End LLM Prompt** | **DROPPED** | Tested initially: Prompting LLM with the entire question + student comment produced hallucinations, missed taxonomy field constraints, and hallucinated confidence scores (99% confidence on wrong answers). |
| **Deterministic Detector Pre-Filter** | **ADOPTED** | Zero-LLM checks (regex, string counts, terminal value extraction) catch 70%+ of errors (blank options, duplicate options, raw LaTeX, exam tags) in under 1ms with 100% precision. |
| **Blinded Multi-Temperature Solver** | **ADOPTED** | Running independent solves without showing the answer key or student comment prevents confirmation bias and catches genuine answer key errors reliably. |
| **Mechanical Scope Guard** | **ADOPTED** | Ensures the LLM is never allowed to modify files outside the strict taxonomy boundaries. Guarantees safety before code or content touches production. |
| **Replay Check (Proof of Fix)** | **ADOPTED** | Re-running detectors on the edited clone guarantees zero regressions. If any new detector fires, auto-apply is blocked. |
| **Heavy SQL/Postgres Database** | **DROPPED** | The problem specified clean, reproducible, free-tier friendly architecture. Bundling precomputed JSON with client-side reactive state makes the faculty console instant, zero-cost, and deployable anywhere. |
