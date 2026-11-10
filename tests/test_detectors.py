import unittest
import json
import os
from engine.parser import ParsedQuestion
from engine.detectors.deterministic import DeterministicDetectors

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

class TestDeterministicDetectors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(DATA_DIR, "questions.json")) as f:
            cls.questions = {q["_id"]: q for q in json.load(f)}

    def test_missing_option(self):
        # 622f08d7b70e4b50e4500a1b has only 3 options
        q = self.questions["622f08d7b70e4b50e4500a1b"]
        pq = ParsedQuestion(q)
        res = DeterministicDetectors.detect_missing_or_blank_option(pq)
        self.assertTrue(res.found)
        self.assertEqual(res.defect_class, "option_repair")
        self.assertIn("expected 4 options", res.evidence)

    def test_blank_option(self):
        # 68e872546e45ba37dcc16bc0 has blank option C
        q = self.questions["68e872546e45ba37dcc16bc0"]
        pq = ParsedQuestion(q)
        res = DeterministicDetectors.detect_missing_or_blank_option(pq)
        self.assertTrue(res.found)
        self.assertEqual(res.defect_class, "option_repair")
        self.assertIn("Option C has no text", res.evidence)

    def test_identical_options(self):
        # 6956d79788d7701e5617bc29 has identical options B and C ('0 W')
        q = self.questions["6956d79788d7701e5617bc29"]
        pq = ParsedQuestion(q)
        res = DeterministicDetectors.detect_identical_options(pq)
        self.assertTrue(res.found)
        self.assertEqual(res.defect_class, "identical_options")
        self.assertIn("0 W", res.evidence)

    def test_exam_reference(self):
        # 617fa18efd53ff1629ed890f has '(NEET 2019)'
        q = self.questions["617fa18efd53ff1629ed890f"]
        pq = ParsedQuestion(q)
        res = DeterministicDetectors.detect_exam_reference(pq)
        self.assertTrue(res.found)
        self.assertEqual(res.defect_class, "exam_reference")
        self.assertIn("NEET 2019", res.span)

    def test_markup_leak(self):
        # 63765a28f1d8416ae0408d89 has raw '\\frac'
        q = self.questions["63765a28f1d8416ae0408d89"]
        pq = ParsedQuestion(q)
        res = DeterministicDetectors.detect_markup_leak(pq)
        self.assertTrue(res.found)
        self.assertEqual(res.defect_class, "markup_leak")
        self.assertIn(r"\frac", res.span)

    def test_diagram_missing(self):
        # 622df25ab70e4b50e44ff837 mentions 'shown in figure' but quesImages is empty
        q = self.questions["622df25ab70e4b50e44ff837"]
        pq = ParsedQuestion(q)
        res = DeterministicDetectors.detect_diagram_missing(pq)
        self.assertTrue(res.found)
        self.assertEqual(res.defect_class, "diagram")
        self.assertIn("quesImages array is empty", res.evidence)

    def test_answer_key_mismatch(self):
        # 60f744b3f1b9bc7cc7b4a949 has key C but sol ends with 50 V (Option A)
        q = self.questions["60f744b3f1b9bc7cc7b4a949"]
        pq = ParsedQuestion(q)
        res = DeterministicDetectors.detect_key_solution_mismatch(pq)
        self.assertTrue(res.found)
        self.assertEqual(res.defect_class, "answer_key")
        self.assertIn("Option A", res.evidence)

    def test_clean_question_no_false_positives(self):
        # 695ede2a88d7701e561aa9d9 is a clean question
        q = self.questions["695ede2a88d7701e561aa9d9"]
        pq = ParsedQuestion(q)
        hits = DeterministicDetectors.run_all(pq)
        self.assertEqual(len(hits), 0)

if __name__ == "__main__":
    unittest.main()
