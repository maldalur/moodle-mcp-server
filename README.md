# Moodle MCP Server

An MCP (Model Context Protocol) server that enables LLMs to interact with the Moodle platform to manage courses, students, assignments, and quizzes.

## Features

### Course Management
- **`search_courses`** - Search for courses by name
  - Parameters:
    - `courseName` (required): Name or part of the name of the course to search
  - Returns: list of matching courses with ID, full name, short name, category ID, visibility status, and start/end dates
  - Performs case-insensitive search on both full name and short name
  - Useful for finding the course ID needed for other operations

### Student Management
- **`get_students`** - Retrieves the list of students enrolled in the course
  - Returns: student ID, full name, email, and last access timestamp
  - No parameters required (uses configured MOODLE_COURSE_ID)

### Assignment Management
- **`get_assignments`** - Retrieves all available assignments in the course
  - Returns: assignment ID, name, description, due date, cutoff date, and maximum grade
  - No parameters required (uses configured MOODLE_COURSE_ID)

- **`get_submissions`** - Retrieves submissions for assignments
  - Parameters: 
    - `assignmentId` (optional): Specific assignment ID to filter by
    - `studentId` (optional): Specific student ID to filter by
  - Returns: submission status, time submitted, and grading information
  - If no parameters provided, returns all submissions for the course

- **`get_submission_content`** - Retrieves detailed content of a specific submission
  - Parameters:
    - `studentId` (required): Student ID
    - `assignmentId` (required): Assignment ID
  - Returns: submission text, file attachments, and metadata

- **`provide_feedback`** - Provides grades and feedback for a submission
  - Parameters:
    - `studentId` (required): Student ID
    - `assignmentId` (required): Assignment ID
    - `feedback` (required): Feedback text
    - `grade` (optional): Numerical grade to assign
  - Stores the feedback and grade in Moodle

### VPL (Virtual Programming Lab) Support
- **`get_vpl_assignments`** - Retrieves all VPL assignments in the course
  - Returns: VPL ID, name, description, due date, and configuration
  - Specifically targets VPL activities (module name: "vpl")

- **`get_vpl_submission`** - Retrieves a student's VPL submission with code files
  - Parameters:
    - `studentId` (required): Student ID
    - `vplId` (required): VPL assignment ID
  - Returns: submission details, submitted files with content, and grading information
  - Useful for code review and automated analysis

### Quiz Management
- **`get_quizzes`** - Retrieves all available quizzes in the course
  - Returns: quiz ID, name, description, time open/close, time limit, and maximum grade
  - No parameters required (uses configured MOODLE_COURSE_ID)

- **`get_quiz_grade`** - Retrieves a student's grade for a specific quiz
  - Parameters:
    - `studentId` (required): Student ID
    - `quizId` (required): Quiz ID
  - Returns: numerical grade, maximum grade, percentage, and grading status

## Requirements

- Node.js (v14 or higher)
- Moodle API token with appropriate permissions
- Moodle course ID

## Installation

1. Clone this repository:
```bash
git clone https://github.com/your-username/moodle-mcp-server.git
cd moodle-mcp-server
```

2. Install dependencies:
```bash
npm install
```

3. Create a `.env` file with the following configuration:
```
MOODLE_API_URL=https://your-moodle.com/webservice/rest/server.php
MOODLE_API_TOKEN=your_api_token
MOODLE_COURSE_ID=1  # Replace with your course ID
```

4. Build the server:
```bash
npm run build
```

## Usage Examples

### Searching for Courses
```typescript
// Search for courses by name
const courses = await search_courses({ courseName: "Programming" });
// Returns all courses that contain "Programming" in their full name or short name

// Example response:
{
  "searchTerm": "Programming",
  "totalFound": 2,
  "courses": [
    {
      "id": 130,
      "fullname": "Programming 1 - Java",
      "shortname": "PROG1",
      "categoryid": 5,
      "visible": 1,
      "startdate": 1693526400,
      "enddate": 1704067200
    }
  ]
}
```

### Getting Student Information
```typescript
// Get all students in the course
const students = await get_students();
```

### Working with Assignments
```typescript
// Get all assignments
const assignments = await get_assignments();

// Get all submissions for a specific assignment
const submissions = await get_submissions({ assignmentId: 123 });

// Get detailed content of a specific submission
const content = await get_submission_content({ 
  studentId: 456, 
  assignmentId: 123 
});

// Provide feedback and grade
await provide_feedback({
  studentId: 456,
  assignmentId: 123,
  feedback: "Great work! Well structured code.",
  grade: 8.5
});
```

### Working with VPL Assignments
```typescript
// Get all VPL assignments
const vplAssignments = await get_vpl_assignments();

// Get a student's VPL submission with code files
const vplSubmission = await get_vpl_submission({
  studentId: 456,
  vplId: 789
});
// Returns: submission details, array of files with names and content
```

### Working with Quizzes
```typescript
// Get all quizzes
const quizzes = await get_quizzes();

// Get a student's grade for a specific quiz
const grade = await get_quiz_grade({
  studentId: 456,
  quizId: 321
});
```

## Usage with Claude

To use with Claude Desktop, add the server configuration:

On MacOS: `~/Library/Application Support/Claude/claude_desktop_config.json`  
On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "moodle-mcp-server": {
      "command": "/path/to/node",
      "args": [
        "/path/to/moodle-mcp-server/build/index.js"
      ],
      "env": {
        "MOODLE_API_URL": "https://your-moodle.com/webservice/rest/server.php",
        "MOODLE_API_TOKEN": "your_moodle_api_token",
        "MOODLE_COURSE_ID": "your_course_id"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

For Windows users, the paths would use backslashes:

```json
{
  "mcpServers": {
    "moodle-mcp-server": {
      "command": "C:\\path\\to\\node.exe",
      "args": [
        "C:\\path\\to\\moodle-mcp-server\\build\\index.js"
      ],
      "env": {
        "MOODLE_API_URL": "https://your-moodle.com/webservice/rest/server.php",
        "MOODLE_API_TOKEN": "your_moodle_api_token",
        "MOODLE_COURSE_ID": "your_course_id"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

Once configured, Claude will be able to interact with your Moodle course to:
- View enrolled students and their information
- Manage assignments and retrieve submissions
- Access VPL (Virtual Programming Lab) assignments and submitted code
- Provide grades and feedback for student work
- Retrieve quiz information and student grades
- Download and analyze submission content including files

## Integration with AI Analysis System

This MCP server is designed to work alongside a Python-based AI analysis system located in the parent directory. The Python system provides:

- **AI-powered submission analysis** using Ollama/LLMs
- **Automated feedback generation** based on submission content
- **Risk assessment** for students (high/medium/low risk levels)
- **URL extraction and verification** from submissions
- **Progress tracking** and trend analysis
- **Markdown report generation** for students and courses

### Workflow

1. **MCP Server**: Provides API access to Moodle data (students, assignments, VPL, quizzes)
2. **Python System** (`src/main.py`): 
   - Retrieves data using Moodle Web Services directly
   - Downloads submission files
   - Performs AI analysis using Ollama
   - Generates comprehensive reports
3. **Integration**: Both systems can work independently or in tandem for complete course management

For AI analysis features, refer to `AI_ANALYSIS_README.md` in the parent directory.

## Development

For development with auto-rebuild:
```bash
npm run watch
```

### Debugging

MCP servers communicate through stdio, which can make debugging challenging. We recommend using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector):

```bash
npm run inspector
```

The Inspector will provide a URL to access debugging tools in your browser.

## Obtaining a Moodle API Token

1. Log in to your Moodle site as an administrator
2. Go to Site Administration > Plugins > Web Services > Manage tokens
3. Create a new token with the necessary permissions to manage courses
4. Copy the generated token and add it to your `.env` file

## Security

- Never share your `.env` file or Moodle API token
- Ensure the MCP server only has access to the courses it needs to manage
- Use a token with the minimum necessary permissions

## License

[MIT](LICENSE)
