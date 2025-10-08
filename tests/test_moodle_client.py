import unittest
from unittest.mock import patch, MagicMock
from src.moodle_client import MoodleClient

class TestMoodleClient(unittest.TestCase):

    @patch('src.moodle_client.requests.post')
    def test_connect_success(self, mock_post):
        mock_post.return_value.status_code = 200
        client = MoodleClient()
        result = client.connect()
        self.assertTrue(result)

    @patch('src.moodle_client.requests.post')
    def test_connect_failure(self, mock_post):
        mock_post.return_value.status_code = 403
        client = MoodleClient()
        result = client.connect()
        self.assertFalse(result)

    @patch('src.moodle_client.requests.get')
    def test_get_task_description(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'description': 'Task description'}
        client = MoodleClient()
        client.connect()
        description = client.get_task_description()
        self.assertEqual(description, 'Task description')

    @patch('src.moodle_client.requests.get')
    def test_get_student_submissions(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [{'submission': 'Submission 1'}, {'submission': 'Submission 2'}]
        client = MoodleClient()
        client.connect()
        submissions = client.get_student_submissions()
        self.assertEqual(len(submissions), 2)

if __name__ == '__main__':
    unittest.main()