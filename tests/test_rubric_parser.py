import unittest
from src.rubric_parser import RubricParser

class TestRubricParser(unittest.TestCase):

    def setUp(self):
        self.parser = RubricParser()

    def test_extract_criteria(self):
        description = "Criteria: 1. Clarity 2. Depth 3. Originality"
        expected_criteria = ["Clarity", "Depth", "Originality"]
        self.assertEqual(self.parser.extract_criteria(description), expected_criteria)

    def test_parse_description(self):
        description = "This is a task description with criteria: 1. Clarity 2. Depth 3. Originality."
        expected_output = {
            "description": "This is a task description with criteria: 1. Clarity 2. Depth 3. Originality.",
            "criteria": ["Clarity", "Depth", "Originality"]
        }
        self.assertEqual(self.parser.parse_description(description), expected_output)

if __name__ == '__main__':
    unittest.main()