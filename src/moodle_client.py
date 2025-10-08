import requests

class MoodleClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.token = token

    def connect(self):
        response = requests.get(
            f"{self.base_url}/webservice/rest/server.php",
            params={
            "wstoken": self.token,
            "wsfunction": "core_user_get_users",
            "moodlewsrestformat": "json"
            }
        )
        if response.status_code != 200:
            raise ConnectionError("Failed to connect to Moodle API")
        return response.json()


    def get_task_description(self, course_id, task_id):
        response = requests.get(
            f"{self.base_url}/webservice/rest/server.php",
            params={
                "wstoken": self.token,
                "wsfunction": "mod_assign_get_assignments",
                "moodlewsrestformat": "json",
                "courseids[0]": course_id,
                "assignmentids[0]": task_id
            }
        )
        return response.json()

    def get_student_submissions(self, course_id, task_id, student_id):
        
        response = requests.get(
            f"{self.base_url}/webservice/rest/server.php",
            params={
                "wstoken": self.token,
                "wsfunction": "mod_assign_get_submissions",
                "moodlewsrestformat": "json",
                "assignmentids[0]": task_id
            }
        )
        data = response.json()

        # Verifica si hay errores en la respuesta
        if "exception" in data:
            return f"Error: {data['message']}"

        # Buscar la entrega del estudiante
        for submission in data.get("assignments", [])[0].get("submissions", []):
            if submission["userid"] == student_id:
                return submission



        return "Entrega no encontrada"

    def get_courses(self, course_name):
        response = requests.get(
            self.base_url + "/webservice/rest/server.php",
            params={
                "wstoken": self.token,
                "wsfunction": "core_course_search_courses",
                "moodlewsrestformat": "json",
                "criterianame": "search",
                "criteriavalue": course_name
            }
        )

        if response.status_code != 200:
            raise ConnectionError("Error al conectar con la API de Moodle")
        return response.json()
    
    def get_users(self, course_id):
        response = requests.get(
            self.base_url + "/webservice/rest/server.php",
            params={
                "wstoken": self.token,
                "wsfunction": "core_enrol_get_enrolled_users",
                "moodlewsrestformat": "json",
                "courseid": course_id
            }
        )

        if response.status_code != 200:
            raise ConnectionError("Error al conectar con la API de Moodle")

        return response.json()
    
    def get_assignmets(self, course_id):
        response = requests.get(
            self.base_url + "/webservice/rest/server.php",
            params={
                "wstoken": self.token,
                "wsfunction": "mod_assign_get_assignments",
                "moodlewsrestformat": "json",
                "courseids[0]": course_id
            }
        )

        if response.status_code != 200:
            raise ConnectionError("Error al conectar con la API de Moodle")
        return response.json()
    
    
    def download_file(self, file_url, destination_path):
        # Añadir el token como parámetro en la URL
        file_url_with_token = f"{file_url}?token={self.token}"

        response = requests.get(file_url_with_token, stream=True)
        if response.status_code == 200:
            with open(destination_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return destination_path
        else:
            raise ConnectionError(f"Failed to download file from Moodle. Status code: {response.status_code}")


    