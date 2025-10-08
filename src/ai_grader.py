import ollama

class AIGrader:
    def __init__(self, rubric_criteria, model="llama3"):
        self.rubric_criteria = rubric_criteria
        self.model = model

    def grade_submission(self, filenames, description):
        # Read the submission files
        submission_content = ""
        for filename in filenames:
            with open(filename, "r", encoding="utf-8") as f:
                submission_content += f"\n--- {filename} ---\n"
                submission_content += f.read()

        scores = {}
        for criterion in self.rubric_criteria:
            score = self.evaluate_criterion(submission_content, description, criterion)
            scores[criterion] = score
        return scores
    
    def evaluate_criterion(self, submission_content, description, criterion):
        prompt = f"""
        You are an expert grader. Given the following task description and student submission, evaluate the submission based on the criterion: "{criterion}".

        Task Description:
        {description}

        Student Submission:
        {submission_content}

        Provide a score from 0 to 10 for the criterion "{criterion}" and a brief justification.
        """
        response = ollama.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
        return response['choices'][0]['message']['content']
    