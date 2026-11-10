# Product Thesis & Strategy: Verifier-First Triage

## 1. Who Loses the Most When a Question is Broken?
The student who loses the most is not the top ranker who spots errors immediately—it is the **earnest, self-studying student working without coaching mentorship in Tier-2/3 towns, practicing days before the exam**.

When an answer key is wrong:
1. **Self-doubt & Panic**: They spend 45 minutes re-deriving the problem, questioning their fundamental grasp of physics or chemistry, believing *they* are wrong.
2. **Reinforcement of False Physics**: If they accept the erroneous key, they internalize an invalid calculation rule (e.g., adding AC voltages linearly instead of vector phasors), which directly costs them 5 marks in the real exam (-1 negative marking + 4 lost marks).
3. **Loss of Trust**: Coaching institutes have physical teachers to clarify doubts immediately; platform students rely entirely on Acadza's integrity. When the system dismisses their correct report with automated apathy, they abandon the app.

Our system is engineered to protect this student: **every report is treated as a serious lead, answer keys are independently re-solved without prejudice, and student replies explicitly pinpoint the exact mathematical step rather than issuing dismissive canned responses.**

---

## 2. What Must NEVER Be Auto-Applied (And Why)
Under our Asymmetric Risk Policy, the following must **never be auto-applied under any circumstances**:

1. **New Authoring Requirements (`auto: false` in taxonomy)**:
   - `identical_options`: Replacing a duplicate option requires authoring a scientifically sound distractor. LLMs hallucinate plausible-sounding but chemically/physically ambiguous distractors that create second correct answers.
   - `diagram`: Missing figures require genuine diagram assets from textbook sources. Synthesizing or guessing coordinate geometries is catastrophic for questions like projectile motion or optics.
   - `unsound` / `wrong_question`: When the problem stem is mathematically contradictory, only experienced subject faculty may decide whether to retire or re-author it.
2. **Answer Key Changes Without 3-Way Independent Agreement**:
   - An answer key change affects every student who attempted or will attempt the question. An automated key shift requires: (a) 3/3 majority agreement across independent blind solves, (b) terminal agreement with step-by-step solution calculation, and (c) mechanical scope guard validation. If any check disagrees, it *must* route to faculty review.
3. **Adversarial / Instruction-Overriding Comments**:
   - Any report containing prompt injection syntax (e.g. `IGNORE ALL PREVIOUS INSTRUCTIONS`) must be hard-flagged and quarantined from the auto-apply pipeline, even if the underlying question is superficially valid.
4. **Single-Lead Unverified Student Claims**:
   - If a student claims an answer is wrong but deterministic detectors and blind solvers find no flaw, the system must never blindly obey the comment.

**The Asymmetry Principle**: A false negative (sending a correct fix to a faculty member) costs 15 seconds of human review. A false positive (auto-applying a corrupt answer or broken distractor) corrupts the grades of 10,000 students. We strictly prefer false negatives.

---

## 3. Week-1 Metric to Watch
**"Faculty Override Rate on Auto-Applied Fixes" (Target: < 0.1%)**
- While traditional teams track "Triage Latency" or "Total Reports Closed", the single most critical safety metric is whether human faculty ever have to roll back an automated repair.
- If faculty override an auto-applied fix during post-deployment sampling, it indicates a hole in the Scope Guard or Replay Check invariants.
- Secondary metric: **"Student Re-Report Rate"** on closed questions (should drop to 0 after surgical repair).

---

## 4. The Beyond-the-Brief Idea: "Defect-Class Sweep & Reusable Rule Export"
Treating student reports as one-off ticket resolution is an operational failure. **A student report is a symptom of a systemic authoring or conversion bug.**

### The Proposal:
1. **Automated Blast-Radius Extrapolation**:
   - When report R011 identified an empty option `(C) <br />`, our deterministic parser detected that this was caused by an HTML cleanup script stripping out `1 : 1` during MathML conversion.
   - By running our unit-tested detectors over the entire 800,000 question bank ("Defect-Class Sweep"), we extrapolate that ~37,200 questions across the bank suffer from blank options, unrendered `\frac` markup, or missing units.
2. **Proactive Bank Cleansing**:
   - Every deterministic detector built for student reports is immediately compiled into a **Continuous Ingestion Linter (CI/CD for Question Banks)**.
   - New questions uploaded by content vendors must pass these deterministic guards before entering the live database.
   - One student report doesn't just fix 1 question—it prevents 10,000 future defects before a student ever encounters them.
