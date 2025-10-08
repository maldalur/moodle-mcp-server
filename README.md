# Moodle AI Grader

## Overview
The Moodle AI Grader is a Python application that connects to the Moodle platform via its REST API to automate the grading process of student submissions based on predefined rubric criteria. The application retrieves task descriptions, student submissions, and utilizes AI algorithms to evaluate the submissions against the rubric.

## Project Structure
```
moodle-ai-grader
├── src
│   ├── main.py               # Entry point of the application
│   ├── moodle_client.py      # Handles connection to Moodle API
│   ├── rubric_parser.py      # Extracts rubric criteria from task descriptions
│   ├── ai_grader.py          # Grades submissions using AI algorithms
│   └── models.py             # Defines data models for tasks and submissions
├── tests
│   ├── test_moodle_client.py # Unit tests for MoodleClient
│   ├── test_rubric_parser.py # Unit tests for RubricParser
│   └── test_ai_grader.py     # Unit tests for AIGrader
├── .env                      # Environment variables for configuration
├── requirements.txt          # Project dependencies
└── README.md                 # Project documentation
```

## Setup Instructions
1. Clone the repository:
   ```
   git clone <repository-url>
   cd moodle-ai-grader
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Configure the environment variables in the `.env` file:
   ```
   MOODLE_API_URL=<your_moodle_api_url>
   MOODLE_API_KEY=<your_moodle_api_key>
   ```

## Usage
To run the application, execute the following command:
```
python src/main.py
```

## Functionality
- **MoodleClient**: Connects to the Moodle REST API and retrieves task descriptions and student submissions.
- **RubricParser**: Extracts grading criteria from task descriptions to facilitate AI grading.
- **AIGrader**: Evaluates student submissions based on the extracted rubric criteria and provides grades.

## Testing
To run the tests, use the following command:
```
pytest tests/
```

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License.