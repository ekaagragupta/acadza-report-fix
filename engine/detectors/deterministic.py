import re
from typing import Dict, Any, List, Optional
from engine.parser import ParsedQuestion, clean_html_to_text

class DetectorResult:
    def __init__(self, found: bool, defect_class: str, span: Optional[str] = None, evidence: str = "", confidence_boost: float = 0.0):
        self.found = found
        self.defect_class = defect_class
        self.span = span
        self.evidence = evidence
        self.confidence_boost = confidence_boost

    def to_dict(self) -> Dict[str, Any]:
        return {
            "found": self.found,
            "defect_class": self.defect_class,
            "span": self.span,
            "evidence": self.evidence,
            "confidence_boost": self.confidence_boost
        }

class DeterministicDetectors:
    """Zero-LLM deterministic defect detectors."""

    @staticmethod
    def detect_missing_or_blank_option(pq: ParsedQuestion) -> DetectorResult:
        """Detect missing option (e.g. only 3 options) or blank/whitespace-only option."""
        if pq.question_type in ["scq", "mcq"]:
            if len(pq.options_raw) < 4:
                return DetectorResult(
                    found=True,
                    defect_class="option_repair",
                    span=f"Only {len(pq.options_raw)} options found",
                    evidence=f"Question has only {len(pq.options_raw)} options (labels: {[o['label'] for o in pq.options_raw]}); expected 4 options.",
                    confidence_boost=0.95
                )
            for opt in pq.options_raw:
                if not opt["text"] or opt["text"].strip() == "":
                    return DetectorResult(
                        found=True,
                        defect_class="option_repair",
                        span=f"Option {opt['label']} is blank",
                        evidence=f"Option {opt['label']} has no text or content (blank option).",
                        confidence_boost=0.95
                    )
        return DetectorResult(found=False, defect_class="option_repair")

    @staticmethod
    def detect_identical_options(pq: ParsedQuestion) -> DetectorResult:
        """Detect duplicate / identical options (requires faculty authored distractors, auto: false)."""
        if pq.question_type in ["scq", "mcq"] and len(pq.options_raw) >= 2:
            seen = {}
            for opt in pq.options_raw:
                t = opt["text"].strip()
                if not t:
                    continue
                if t in seen:
                    return DetectorResult(
                        found=True,
                        defect_class="identical_options",
                        span=f"Option {seen[t]} and Option {opt['label']}",
                        evidence=f"Options {seen[t]} and {opt['label']} have identical content: '{t}'. Requires faculty authored distractor.",
                        confidence_boost=0.98
                    )
                seen[t] = opt["label"]
        return DetectorResult(found=False, defect_class="identical_options")

    @staticmethod
    def detect_exam_reference(pq: ParsedQuestion) -> DetectorResult:
        """Detect exam reference tags like (NEET 2019), (JEE Main 2020) leaking in question stem."""
        if pq.has_exam_tag and pq.exam_tag:
            return DetectorResult(
                found=True,
                defect_class="exam_reference",
                span=pq.exam_tag,
                evidence=f"Exam reference tag '{pq.exam_tag}' found inside question text; should be stripped.",
                confidence_boost=0.98
            )
        return DetectorResult(found=False, defect_class="exam_reference")

    @staticmethod
    def detect_markup_leak(pq: ParsedQuestion) -> DetectorResult:
        """Detect unrendered raw LaTeX markup (e.g. \\frac, \\sqrt, \\text, \\AA) in HTML."""
        # Check in stem text or solution text outside math tags
        # Acadza uses MathML; raw TeX commands leaking outside or as plain text indicate markup leak
        latex_keywords = [r'\\frac', r'\\sqrt', r'\\text', r'\\AA', r'\\cdot', r'\\times']
        combined = pq.raw_question_html + " " + pq.raw_solution_html
        for kw in latex_keywords:
            match = re.search(kw, combined)
            if match:
                # check where it is
                target = "question" if re.search(kw, pq.raw_question_html) else "solution"
                span = match.group(0)
                return DetectorResult(
                    found=True,
                    defect_class="markup_leak",
                    span=span,
                    evidence=f"Raw LaTeX markup '{span}' leaking unrendered in {target}.",
                    confidence_boost=0.95
                )
        return DetectorResult(found=False, defect_class="markup_leak")

    @staticmethod
    def detect_noise(pq: ParsedQuestion) -> DetectorResult:
        """Detect noise like 'Space for rough work', stray question numbers, or source labels."""
        noise_patterns = [
            r'Space for rough work',
            r'Rough work',
            r'Question\s*No\.?\s*[0-9]+',
            r'Q\.[0-9]+'
        ]
        for pat in noise_patterns:
            m = re.search(pat, pq.raw_question_html, re.IGNORECASE)
            if m:
                return DetectorResult(
                    found=True,
                    defect_class="noise",
                    span=m.group(0),
                    evidence=f"Stray noise text '{m.group(0)}' found in question text.",
                    confidence_boost=0.95
                )
        return DetectorResult(found=False, defect_class="noise")

    @staticmethod
    def detect_diagram_missing(pq: ParsedQuestion) -> DetectorResult:
        """Detect when question refers to a figure/diagram ('as shown in figure', 'in the given diagram') but quesImages is empty."""
        stem_text = clean_html_to_text(pq.stem_html).lower()
        fig_refs = [
            "given figure", "shown in figure", "in the figure", "in the diagram", 
            "given diagram", "as shown below", "following figure", "in figure"
        ]
        for ref in fig_refs:
            if ref in stem_text and len(pq.ques_images) == 0:
                return DetectorResult(
                    found=True,
                    defect_class="diagram",
                    span=ref,
                    evidence=f"Stem mentions '{ref}', but quesImages array is empty (no image attached).",
                    confidence_boost=0.95
                )
        return DetectorResult(found=False, defect_class="diagram")

    @staticmethod
    def detect_key_solution_mismatch(pq: ParsedQuestion) -> DetectorResult:
        """Detect when the solution's clear terminal calculation disagrees with the stored answer key."""
        sol_text = clean_html_to_text(pq.raw_solution_html)
        if not sol_text:
            return DetectorResult(found=False, defect_class="answer_key")

        if pq.question_type == "scq":
            stored_key = str(pq.stored_answer).strip().upper()
            
            # Check terminal equality vs option values
            # e.g. Solution ends with "50 V", Option A is 50 V, but stored key is C (130 V)
            # Or solution ends with "4800 N/m^2", Option D is 4800, but stored key is A (4556)
            for opt in pq.options_raw:
                opt_lbl = opt["label"]
                opt_txt = opt["text"].strip()
                if not opt_txt or opt_lbl == stored_key:
                    continue
                
                # Check if opt_txt is at the very end of solution text or equals terminal expression
                # Normalize spaces and units
                norm_opt = re.sub(r'\s+', '', opt_txt)
                norm_sol = re.sub(r'\s+', '', sol_text)
                
                # Check if sol ends with opt_txt or = opt_txt
                if norm_opt and (norm_sol.endswith(norm_opt) or f"={norm_opt}" in norm_sol or f"is{norm_opt}" in norm_sol):
                    # verify stored_key doesn't match
                    stored_opt = next((o for o in pq.options_raw if o["label"] == stored_key), None)
                    stored_opt_txt = re.sub(r'\s+', '', stored_opt["text"]) if stored_opt else ""
                    if stored_opt_txt and stored_opt_txt not in norm_sol[-len(stored_opt_txt)*2:]:
                        return DetectorResult(
                            found=True,
                            defect_class="answer_key",
                            span=f"Key: {stored_key} vs Solution: {opt_lbl} ({opt_txt})",
                            evidence=f"Solution terminal result matches Option {opt_lbl} ('{opt_txt}'), but stored answer key is {stored_key}.",
                            confidence_boost=0.96
                        )

        elif pq.question_type == "integerQuestion":
            stored_key = str(pq.stored_answer).strip()
            # Check if solution explicitly calculates something else at terminal
            # e.g. "a = 40 cm" vs key "20"
            m = re.search(r'=\s*([0-9]+(?:\.[0-9]+)?)\s*(?:cm|m|V|N|kg|s|sec)?\s*$', sol_text)
            if m:
                sol_val = m.group(1).rstrip('.0') if '.' in m.group(1) else m.group(1)
                if sol_val != stored_key and float(sol_val) != float(stored_key):
                    return DetectorResult(
                        found=True,
                        defect_class="solution_fix", # or answer_key
                        span=f"Key: {stored_key} vs Solution: {sol_val}",
                        evidence=f"Solution ends with {sol_val}, but stored answer key is {stored_key}.",
                        confidence_boost=0.90
                    )

        return DetectorResult(found=False, defect_class="answer_key")

    @classmethod
    def run_all(cls, pq: ParsedQuestion) -> List[DetectorResult]:
        """Run all deterministic detectors on a question."""
        detectors = [
            cls.detect_missing_or_blank_option,
            cls.detect_identical_options,
            cls.detect_exam_reference,
            cls.detect_markup_leak,
            cls.detect_noise,
            cls.detect_diagram_missing,
            cls.detect_key_solution_mismatch,
        ]
        results = []
        for det in detectors:
            res = det(pq)
            if res.found:
                results.append(res)
        return results
