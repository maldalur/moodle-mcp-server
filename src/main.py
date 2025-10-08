from moodle_client import MoodleClient
from rubric_parser import RubricParser
from ai_grader import AIGrader
from dotenv import load_dotenv
import os

class CourseInfo:
    def __init__(self, course_id, fullname, shortname):
        self.course_id = course_id
        self.fullname = fullname
        self.shortname = shortname

    def __repr__(self):
        return f"CourseInfo(id={self.course_id}, fullname='{self.fullname}', shortname='{self.shortname}')"

def main():
    # load environment variables
    load_dotenv()
    MOODLE_URL = os.getenv("MOODLE_URL")
    TOKEN_MOODLE = os.getenv("TOKEN_MOODLE")
    COURSE_LIST = os.getenv("COURSE_LIST").split(",")

    # Initialize Moodle client
    moodle_client = MoodleClient(MOODLE_URL,TOKEN_MOODLE)
    moodle_client.connect()
    for course in COURSE_LIST:
        course_data = moodle_client.get_courses(course)

        course_info = CourseInfo(
            course_data['courses'][0]['id'],
            course_data['courses'][0]['fullname'],
            course_data['courses'][0]['shortname']
        )
        enrolled_users = moodle_client.get_users(course_info.course_id)
        # 
        #     print(user["username"])
        assignments = moodle_client.get_assignmets(course_info.course_id)
        for assignment in assignments["courses"][0]["assignments"]:
            print(assignment["name"], assignment["id"])
            description = assignment["intro"]
            for user in enrolled_users:
                print(user["username"])
                submission = moodle_client.get_student_submissions(course_info.course_id, assignment["id"], user["id"])
                if submission != "Entrega no encontrada":
                    if "fileareas" in submission["plugins"][0].keys():
                        for file in submission["plugins"][0]["fileareas"]:
                            filenames = []
                            for doc in file["files"]:
                                print(doc["filename"], doc["fileurl"])
                                moodle_client.download_file(doc["fileurl"], doc["filename"])
                                filenames.append(doc["filename"])

                                # Here you can integrate the AI grading process
                                # For example:
                                # ai_grader = AIGrader()
                                # Pasar archivos y descripcion a la IA
                                # grade = ai_grader.grade_submission(filenames, description)
                                # print(f"Grade for {user['username']}: {grade}")

                                # Subir el resultado a alguna parte del sistema
                                # moodle_client.upload_grade(user["id"], assignment["id"], grade)

                                # Finalmente, borrar el archivo descargado
                                if os.path.exists(doc["filename"]):
                                    os.remove(doc["filename"])
                            
                        
                    
    # # Extract rubric criteria from the task description
    # rubric_parser = RubricParser()
    # criteria = rubric_parser.extract_criteria(task_description)

    # # Retrieve student submissions
    # student_submissions = moodle_client.get_student_submissions()

    # # Initialize AI Grader
    # ai_grader = AIGrader()

    # # Grade each submission based on the rubric criteria
    # for submission in student_submissions:
    #     grade = ai_grader.grade_submission(submission, criteria)
    #     print(f"Submission ID: {submission.id}, Grade: {grade}")

if __name__ == "__main__":
    main()