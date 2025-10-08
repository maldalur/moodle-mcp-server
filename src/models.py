class Task:
    def __init__(self, id, description, rubric):
        self.id = id
        self.description = description
        self.rubric = rubric

class Submission:
    def __init__(self, student_id, task_id, content):
        self.student_id = student_id
        self.task_id = task_id
        self.content = content

class RubricCriteria:
    def __init__(self, criterion_id, description, max_score):
        self.criterion_id = criterion_id
        self.description = description
        self.max_score = max_score