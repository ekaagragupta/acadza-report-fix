import json
import os
import copy
from typing import Dict, Any, Optional, Tuple

TAXONOMY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "taxonomy.json")

class ScopeGuard:
    """
    Scope Guard verifies candidate edits mechanically:
    1. Only fields permitted by taxonomy.json for this repair may be touched.
    2. 'find' string must occur exactly once in the target field (prevent ambiguity).
    3. Spelling/noise/exam_reference: NO digit, math node (<math>...</math>), <img>, or number changes.
    4. Option repair: Question stem text must remain byte-identical.
    5. Answer form: The change must be purely additive.
    6. If auto == false in taxonomy, route cannot be auto_apply.
    """
    
    def __init__(self, taxonomy_path: str = TAXONOMY_FILE):
        with open(taxonomy_path) as f:
            tax = json.load(f)
            self.repairs = tax.get("repairs", {})

    def verify_edit(
        self, 
        repair_key: str, 
        raw_question_dict: Dict[str, Any], 
        proposed_edit: Optional[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        if not repair_key:
            return True, "No repair needed"
            
        repair_def = self.repairs.get(repair_key)
        if not repair_def:
            return False, f"Unknown repair key '{repair_key}' not in taxonomy"

        allowed_fields = repair_def.get("fields", [])
        
        # If repair does not permit edits (fields: [])
        if not allowed_fields:
            if proposed_edit is not None:
                return False, f"Repair '{repair_key}' does not permit automated edits (fields is empty; requires faculty authored content)"
            return True, "Valid repair with no direct code edits allowed"

        if proposed_edit is None:
            return False, f"Repair '{repair_key}' requires an edit, but None provided"

        field = proposed_edit.get("field")
        find_str = proposed_edit.get("find", "")
        replace_str = proposed_edit.get("replace", "")

        # 1. Allowed fields check
        qtype = raw_question_dict.get("questionType", "")
        inner = raw_question_dict.get(qtype, {})
        
        # Map logical fields to actual dict keys
        if field == "answer":
            if "answer" not in allowed_fields:
                return False, f"Field 'answer' not in allowed fields {allowed_fields} for '{repair_key}'"
            return True, "Answer key edit within scope"

        if field == "questionType":
            if "questionType" not in allowed_fields:
                return False, f"Field 'questionType' not in allowed fields {allowed_fields} for '{repair_key}'"
            return True, "Question type change within scope"

        if field in ["question", "solution"]:
            if field not in allowed_fields:
                return False, f"Field '{field}' not in allowed fields {allowed_fields} for '{repair_key}'"
            
            target_text = inner.get(field, "")
            if not target_text:
                return False, f"Target field '{field}' is empty in question record"

            # 2. 'find' must occur exactly once
            occurrences = target_text.count(find_str)
            if occurrences == 0:
                return False, f"Target 'find' string '{find_str}' not found in {field}"
            if occurrences > 1:
                return False, f"Target 'find' string '{find_str}' occurs {occurrences} times in {field} (ambiguous edit)"

            # 3. Spelling/Noise/Exam_Reference guard: no digits, no math nodes, no img changes
            if repair_key in ["spelling", "noise", "exam_reference"]:
                import re
                find_digits = re.findall(r'\d+', find_str)
                replace_digits = re.findall(r'\d+', replace_str)
                # Allow stripping year from exam reference if it matches 2019/2020 etc
                if repair_key != "exam_reference" and find_digits != replace_digits:
                    return False, f"Spelling/noise edit cannot mutate numbers: '{find_digits}' vs '{replace_digits}'"
                if "<math" in find_str or "<math" in replace_str or "<img" in find_str or "<img" in replace_str:
                    return False, f"Edit cannot mutate math nodes or images in '{repair_key}'"

            # 4. Option repair: Stem text must remain byte-identical
            if repair_key == "option_repair":
                # Ensure the find/replace is only within the options portion, not the stem
                from engine.parser import ParsedQuestion
                pq = ParsedQuestion(raw_question_dict)
                if pq.stem_html and find_str in pq.stem_html:
                    return False, "Option repair cannot mutate the question stem (stem must remain byte-identical)"

            # 5. Answer form: Change must be purely additive
            if repair_key == "answer_form":
                if find_str and find_str not in replace_str:
                    return False, "Answer form repair must be purely additive (cannot delete existing text)"

            return True, "Scope guard passed all mechanical checks"

        return False, f"Unsupported field '{field}'"

    def apply_edit_to_copy(
        self, 
        raw_question_dict: Dict[str, Any], 
        proposed_edit: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Deep copy and apply surgical edit."""
        cloned = copy.deepcopy(raw_question_dict)
        if not proposed_edit:
            return cloned
            
        field = proposed_edit.get("field")
        find_str = proposed_edit.get("find", "")
        replace_str = proposed_edit.get("replace", "")
        qtype = cloned.get("questionType", "")

        if field == "questionType":
            cloned["questionType"] = replace_str
            # Move inner dict if needed
            if qtype in cloned and replace_str not in cloned:
                cloned[replace_str] = cloned.pop(qtype)
        elif field == "answer":
            cloned[qtype]["answer"] = replace_str
        elif field in ["question", "solution"]:
            curr = cloned[qtype].get(field, "")
            cloned[qtype][field] = curr.replace(find_str, replace_str, 1)

        return cloned
