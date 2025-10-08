import unittest
from src.ai_grader import AIGrader
from src.models import Submission, RubricCriteria

class TestAIGrader(unittest.TestCase):

    def setUp(self):
        self.ai_grader = AIGrader()
        self.criteria = [
            RubricCriteria(name="Content", max_score=10),
            RubricCriteria(name="Clarity", max_score=5),
            RubricCriteria(name="Creativity", max_score=5)
        ]
        self.submission = Submission(content="This is a sample submission.", criteria=self.criteria)

    def test_grade_submission(self):
        score = self.ai_grader.grade_submission(self.submission)
        self.assertIsInstance(score, dict)
        self.assertEqual(len(score), len(self.criteria))

    def test_grade_submission_with_empty_content(self):
        empty_submission = Submission(content="", criteria=self.criteria)
        score = self.ai_grader.grade_submission(empty_submission)
        self.assertEqual(score, {criterion.name: 0 for criterion in self.criteria})

    def test_grade_submission_with_invalid_criteria(self):
        invalid_submission = Submission(content="Valid content.", criteria=[])
        score = self.ai_grader.grade_submission(invalid_submission)
        self.assertEqual(score, {})

if __name__ == '__main__':
    unittest.main()