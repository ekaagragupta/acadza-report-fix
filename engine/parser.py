import re
import html
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

def clean_html_to_text(html_content: str) -> str:
    """Extract readable text from HTML with mathml awareness and entity unescaping."""
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "html.parser")
    for br in soup.find_all(["br", "p", "h3", "h2", "h1"]):
        br.insert_after(" ")
    text = soup.get_text()
    text = html.unescape(text)
    text = re.sub(r'[ \t\r\f\v]+', ' ', text)
    return text.strip()

class ParsedQuestion:
    def __init__(self, raw_q: Dict[str, Any]):
        self.raw = raw_q
        self.qid: str = raw_q.get("_id", "")
        self.subject: str = raw_q.get("subject", "")
        self.chapter: str = raw_q.get("chapter", "")
        self.question_type: str = raw_q.get("questionType", "")
        
        # Inner type dict
        self.inner_dict: Dict[str, Any] = raw_q.get(self.question_type, {})
        self.raw_question_html: str = self.inner_dict.get("question", "") or ""
        self.raw_solution_html: str = self.inner_dict.get("solution", "") or ""
        self.stored_answer: Any = self.inner_dict.get("answer")
        self.ques_images: List[str] = self.inner_dict.get("quesImages", []) or []
        self.solution_images: List[str] = self.inner_dict.get("solutionImages", []) or []
        
        # Parsed elements
        self.stem_html: str = ""
        self.options_raw: List[Dict[str, str]] = []  # [{'label': 'A', 'raw_marker': '...', 'html': '...', 'text': '...'}]
        self.has_exam_tag: bool = False
        self.exam_tag: Optional[str] = None
        self.solution_final_answer: Optional[str] = None
        
        self._parse()

    def _parse(self):
        # 1. Check exam tag in raw_question_html
        exam_match = re.search(r'\(\s*(JEE(?:\s+Main|\s+Adv|\s+Advanced)?|NEET|AIIMS|CBSE|AIEEE)\s+[0-9]{4}\s*\)', self.raw_question_html, re.IGNORECASE)
        if exam_match:
            self.has_exam_tag = True
            self.exam_tag = exam_match.group(0)

        # 2. Options parsing for SCQ and MCQ
        if self.question_type in ["scq", "mcq"]:
            self._parse_options()
        else:
            self.stem_html = self.raw_question_html

        # 3. Extract final answer from solution
        self.solution_final_answer = self._extract_solution_final_answer()

    def _parse_options(self):
        """Extract options (A), (B), (C), (D) etc from raw_question_html, ignoring Assertion (A)."""
        # Matches (A), (B), (C), (D) or MathML formatted option markers
        # Negative lookbehind for 'Assertion\s*(?:&nbsp;)?'
        marker_regex = re.compile(
            r'(?:'
            r'(?<!Assertion)(?<!Assertion\s)(?<!Assertion&nbsp;)\((?P<lbl1>[A-D])\)|'
            r'(?:<math[^>]*>[^<]*\((?P<lbl2>[A-D])\)[^<]*</math>)'
            r')'
        )
        
        matches = list(marker_regex.finditer(self.raw_question_html))
        
        if len(matches) >= 2:
            first_marker = matches[0]
            self.stem_html = self.raw_question_html[:first_marker.start()].strip()
            
            for i, match in enumerate(matches):
                label = match.group('lbl1') or match.group('lbl2') or chr(ord('A') + i)
                m_text = match.group(0)
                
                start_content = match.end()
                end_content = matches[i + 1].start() if i + 1 < len(matches) else len(self.raw_question_html)
                opt_html = self.raw_question_html[start_content:end_content].strip()
                
                # Strip leading/trailing break lines, tags
                opt_html_clean = re.sub(r'^(?:<br\s*/?>|\s*&nbsp;\s*)+', '', opt_html)
                opt_html_clean = re.sub(r'(?:<br\s*/?>|</h3>|</p>|\s*</mspace>)+$', '', opt_html_clean).strip()
                
                opt_text = clean_html_to_text(opt_html_clean)
                self.options_raw.append({
                    "label": label,
                    "raw_marker": m_text,
                    "html": opt_html_clean,
                    "text": opt_text
                })
        else:
            self.stem_html = self.raw_question_html

    def _extract_solution_final_answer(self) -> Optional[str]:
        if not self.raw_solution_html:
            return None
        sol_text = clean_html_to_text(self.raw_solution_html)
        opt_ref = re.findall(r'(?:option|ans|answer|choice)\s*(?:is|:|=)?\s*\(?([A-D])\)?', sol_text, re.IGNORECASE)
        if opt_ref:
            return opt_ref[-1].upper()
        return sol_text.strip()
