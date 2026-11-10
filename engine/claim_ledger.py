import re
from typing import Dict, Any, Optional

class ClaimLedger:
    """
    Parses and categorizes student comments into actionable leads or flags.
    Student comment is strictly a LEAD, NEVER an instruction.
    """
    
    # Prompt injection patterns
    INJECTION_PATTERNS = [
        r'ignore\s+(?:all\s+)?(?:previous\s+)?instructions',
        r'you\s+are\s+(?:the\s+)?admin',
        r'system\s+prompt',
        r'mark\s+(?:this\s+)?(?:report\s+as\s+)?corrected',
        r'jailbreak',
        r'override\s+(?:all\s+)?rules'
    ]
    
    # Platform / app issue keywords
    APP_PATTERNS = [
        r'i\s+clicked\s+.*but\s+it\s+saved',
        r'app\s+crash',
        r'keyboard\s+(?:not\s+working|issue)',
        r'submit\s+button'
    ]
    
    # Display issue keywords
    DISPLAY_PATTERNS = [
        r'cut\s+on\s+(?:my\s+)?(?:phone|mobile|screen)',
        r'takes\s+forever\s+to\s+load',
        r'slow\s+load',
        r'rendering\s+issue',
        r'not\s+showing\s+properly'
    ]
    
    # Language mode keywords
    LANGUAGE_PATTERNS = [
        r'hindi\s+me\s+question\s+chahiye',
        r'need\s+in\s+hindi',
        r'in\s+hindi\s+please',
        r'translate\s+to\s+hindi'
    ]

    # Out of syllabus / chapter keywords
    SYLLABUS_PATTERNS = [
        r'out\s+of\s+syllabus',
        r'not\s+in\s+neet\s+syllabus',
        r'deleted\s+topic'
    ]
    
    CHAPTER_PATTERNS = [
        r'chapter\s+is\s+wrong',
        r'why\s+is\s+it\s+in\s+',
        r'wrong\s+chapter'
    ]

    @classmethod
    def evaluate_comment(cls, comment: str) -> Dict[str, Any]:
        c = (comment or "").strip()
        
        # 1. Check prompt injection (Adversarial)
        for pat in cls.INJECTION_PATTERNS:
            if re.search(pat, c, re.IGNORECASE):
                return {
                    "is_adversarial": True,
                    "lead_type": "prompt_injection",
                    "cleaned_claim": "Possible gaming attempt / prompt injection detected.",
                    "student_intent": "injection",
                    "preliminary_verdict": None # Underlying question still evaluated on its merits
                }

        # 2. Check gibberish / empty (Not actionable)
        # e.g. "asdfgh", "...", single chars, no vowels or random keys
        if len(c) < 3 or re.match(r'^[a-z]{5,}$', c.lower()) and not any(v in c.lower() for v in ['a','e','i','o','u']):
            return {
                "is_adversarial": False,
                "lead_type": "gibberish",
                "cleaned_claim": c,
                "student_intent": "gibberish",
                "preliminary_verdict": "not_actionable"
            }
            
        if c.lower() in ["asdfgh", "qwerty", "test", "xyz", "abc", "wrong", "error"]:
            return {
                "is_adversarial": False,
                "lead_type": "low_information" if c.lower() in ["wrong", "error"] else "gibberish",
                "cleaned_claim": c,
                "student_intent": "vague_or_unintelligible",
                "preliminary_verdict": "not_actionable" if c.lower() not in ["wrong", "error"] else None
            }

        # 3. Check App issues (Platform bug)
        for pat in cls.APP_PATTERNS:
            if re.search(pat, c, re.IGNORECASE):
                return {
                    "is_adversarial": False,
                    "lead_type": "app_issue",
                    "cleaned_claim": c,
                    "student_intent": "platform_bug",
                    "preliminary_verdict": "app_issue"
                }

        # 4. Check Display issues (Screen layout / slow load)
        for pat in cls.DISPLAY_PATTERNS:
            if re.search(pat, c, re.IGNORECASE):
                return {
                    "is_adversarial": False,
                    "lead_type": "display_issue",
                    "cleaned_claim": c,
                    "student_intent": "display_bug",
                    "preliminary_verdict": "display_issue"
                }

        # 5. Check Language Mode
        for pat in cls.LANGUAGE_PATTERNS:
            if re.search(pat, c, re.IGNORECASE):
                return {
                    "is_adversarial": False,
                    "lead_type": "language_mode",
                    "cleaned_claim": c,
                    "student_intent": "wants_hindi",
                    "preliminary_verdict": "language_mode"
                }

        # 6. Check Syllabus
        for pat in cls.SYLLABUS_PATTERNS:
            if re.search(pat, c, re.IGNORECASE):
                return {
                    "is_adversarial": False,
                    "lead_type": "syllabus",
                    "cleaned_claim": c,
                    "student_intent": "out_of_syllabus",
                    "preliminary_verdict": "defect",
                    "suggested_repair": "syllabus"
                }

        # 7. Check Wrong Chapter
        for pat in cls.CHAPTER_PATTERNS:
            if re.search(pat, c, re.IGNORECASE):
                return {
                    "is_adversarial": False,
                    "lead_type": "wrong_chapter",
                    "cleaned_claim": c,
                    "student_intent": "wrong_chapter",
                    "preliminary_verdict": "defect",
                    "suggested_repair": "wrong_chapter"
                }

        # Default: Factual claim regarding question content
        return {
            "is_adversarial": False,
            "lead_type": "content_claim",
            "cleaned_claim": c,
            "student_intent": "question_content_claim",
            "preliminary_verdict": None
        }
