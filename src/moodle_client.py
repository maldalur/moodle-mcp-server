import requests
import base64
import os
from logger_config import get_logger

logger = get_logger(__name__)

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
    
    def get_vpl_assignments(self, course_id):
        
        response = requests.get(
            f"{self.base_url}/webservice/rest/server.php",
            params={
                "wstoken": self.token,
                "wsfunction": "core_course_get_contents",
                "moodlewsrestformat": "json",
                "courseid": course_id
            }
        )
        data = response.json()
        
        vpl_activities = []

        for section in data:
            for module in section.get("modules", []):
                if module.get("modname") == "vpl":
                    vpl_activities.append({
                        "name": module.get("name"),
                        "vplid": module.get("instance"),  # ID de la instancia VPL
                        "cmid": module.get("id"),  # ID del módulo de curso (necesario para mod_vpl_open)
                        "section": section.get("name")
                    })
        return vpl_activities



    def get_vpl_submissions(self, vplid, course_id, student_id, cmid=None):
        # Intenta obtener las entregas VPL usando la API de Moodle.
        # El VPL plugin usa principalmente mod_vpl_open para obtener la información de la entrega
        # IMPORTANTE: mod_vpl_open requiere el CMID (course module id), NO el vplid (instance id)
        
        # Si no se proporciona cmid, usar vplid (para retrocompatibilidad, pero probablemente fallará)
        module_id = cmid if cmid is not None else vplid
        response = requests.get(
            self.base_url + "/webservice/rest/server.php",
            params={
                "wstoken": self.token,
                "wsfunction": "mod_vpl_open",
                "moodlewsrestformat": "json",
                "id": module_id,  # Usar CMID, no vplid
                "userid": student_id
            }
        )

        if response.status_code != 200:
            raise ConnectionError(f"Failed to connect to Moodle API (status {response.status_code})")

        data = response.json()


        # Verifica si hay errores en la respuesta
        if isinstance(data, dict) and "exception" in data:
            return "Entrega no encontrada"
        
        # Si la respuesta está vacía o no tiene datos útiles
        if not data or (isinstance(data, dict) and not any(k in data for k in ['files', 'submission', 'compilationfiles', 'executionfiles'])):
            return "Entrega no encontrada"

        # Procesar archivos adjuntos de la entrega
        saved_files = []

        # mod_vpl_open devuelve típicamente un dict con 'files' que contiene los archivos del estudiante
        # Formato típico: {'files': [{'name': 'file.py', 'data': 'contenido_base64', ...}], ...}
        if isinstance(data, dict):
            # Intentar obtener files directamente
            files_data = data.get("files") or data.get("submission") or data.get("submittedfiles")
            
            if files_data:
                if isinstance(files_data, list):
                    for file_item in files_data:
                        self._process_vpl_file_entry(file_item, saved_files, vplid, student_id)
                elif isinstance(files_data, dict):
                    # Puede ser un dict con nombres de archivo como claves
                    for filename, content in files_data.items():
                        file_obj = {"name": filename, "data": content}
                        self._process_vpl_file_entry(file_obj, saved_files, vplid, student_id)
            
            # También procesar compilationfiles y executionfiles si existen
            for file_type in ['compilationfiles', 'executionfiles']:
                if file_type in data and isinstance(data[file_type], list):
                    for file_item in data[file_type]:
                        self._process_vpl_file_entry(file_item, saved_files, vplid, student_id)

        # Si no se encontraron archivos, devolver la entrega cruda
        if not saved_files:
            return data

        return saved_files

    def _process_vpl_file_entry(self, file_entry, saved_files, vplid=None, student_id=None):
        """Procesa una entrada de archivo de VPL y guarda el fichero localmente cuando es posible.
        Añade la ruta al fichero guardado a la lista `saved_files`.
        
        Args:
            file_entry: Diccionario con información del archivo (name, data, filename, content, etc.)
            saved_files: Lista donde se añadirán las rutas de archivos guardados
            vplid: ID del VPL (opcional, para organizar carpetas)
            student_id: ID del estudiante (opcional, para organizar carpetas)
        """
        if not isinstance(file_entry, dict):
            return False

        # En VPL, los archivos suelen venir con 'name' y 'data' (contenido en base64)
        filename = file_entry.get("name") or file_entry.get("filename") or "file.bin"

        # Si viene una URL de archivo, descargarla
        fileurl = file_entry.get("fileurl") or file_entry.get("url")
        if fileurl:
            # Añadir token si no está presente
            if "token=" not in fileurl:
                sep = "&" if "?" in fileurl else "?"
                fileurl_with_token = f"{fileurl}{sep}token={self.token}"
            else:
                fileurl_with_token = fileurl
            try:
                saved = self.download_file(fileurl_with_token, filename)
                saved_files.append(saved)
                return True
            except Exception as e:
                logger.error(f"Error downloading file {filename}: {e}")
                return False

        # Si viene contenido codificado en base64 (formato típico de VPL)
        # VPL usa 'data' para el contenido del archivo
        content_b64 = file_entry.get("data") or file_entry.get("content") or file_entry.get("filecontent") or file_entry.get("contentbase64")
        if content_b64:
            try:
                # Si el contenido ya es texto plano (no base64), intentar guardarlo directamente
                try:
                    decoded = base64.b64decode(content_b64)
                except Exception:
                    # Si falla la decodificación, asumir que es texto plano
                    decoded = content_b64.encode('utf-8') if isinstance(content_b64, str) else content_b64
                
                # Asegurar carpeta (opcionalmente organizada por vplid/student_id)
                if vplid and student_id:
                    dest_dir = os.path.join("downloads", f"vpl_{vplid}", f"student_{student_id}")
                else:
                    dest_dir = "downloads"
                
                os.makedirs(dest_dir, exist_ok=True)
                dest_path = os.path.join(dest_dir, filename)
                
                with open(dest_path, "wb") as fh:
                    fh.write(decoded)
                saved_files.append(dest_path)
                return True
            except Exception as e:
                logger.error(f"Error processing file {filename}: {e}")
                return False

        return False


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
        # Asegura que exista la carpeta downloads
        os.makedirs(os.path.dirname(os.path.join("", f"downloads/{destination_path}")), exist_ok=True)
        destination_path = f"downloads/{destination_path}"

        # Si la URL ya contiene token, no añadir otro
        file_url_with_token = file_url
        if "token=" not in file_url:
            sep = "&" if "?" in file_url else "?"
            file_url_with_token = f"{file_url}{sep}token={self.token}"

        response = requests.get(file_url_with_token, stream=True)
        if response.status_code == 200:
            with open(destination_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    if chunk:
                        f.write(chunk)
            return destination_path
        else:
            raise ConnectionError(f"Failed to download file from Moodle. Status code: {response.status_code}")

    def get_quizzes(self, course_id):
        """
        Obtiene todos los quizzes de un curso usando core_course_get_contents.
        
        Args:
            course_id: ID del curso
        
        Returns:
            Lista de diccionarios con información de los quizzes:
            [{"name": "Quiz 1", "quizid": 123, "cmid": 456, "section": "Tema 1"}, ...]
        """
        response = requests.get(
            f"{self.base_url}/webservice/rest/server.php",
            params={
                "wstoken": self.token,
                "wsfunction": "core_course_get_contents",
                "moodlewsrestformat": "json",
                "courseid": course_id
            }
        )
        
        if response.status_code != 200:
            raise ConnectionError(f"Error al conectar con la API de Moodle (status {response.status_code})")
        
        data = response.json()
        
        if isinstance(data, dict) and "exception" in data:
            logger.error(f"Error obteniendo quizzes: {data.get('message', 'Unknown error')}")
            return []
        
        quizzes = []
        for section in data:
            for module in section.get("modules", []):
                if module.get("modname") == "quiz":
                    quizzes.append({
                        "name": module.get("name"),
                        "quizid": module.get("instance"),  # ID de la instancia del quiz
                        "cmid": module.get("id"),  # ID del módulo de curso
                        "section": section.get("name")
                    })
        
        return quizzes
    
    def get_quiz_attempts(self, quiz_id, student_id=None):
        """
        Obtiene los intentos de un quiz, opcionalmente filtrados por estudiante.
        
        Args:
            quiz_id: ID del quiz (instance id)
            student_id: ID del estudiante (opcional, si no se proporciona obtiene todos)
        
        Returns:
            Lista de intentos con información detallada o dict con error
        """
        params = {
            "wstoken": self.token,
            "wsfunction": "mod_quiz_get_user_attempts",
            "moodlewsrestformat": "json",
            "quizid": quiz_id
        }
        
        if student_id is not None:
            params["userid"] = student_id
        
        response = requests.get(
            f"{self.base_url}/webservice/rest/server.php",
            params=params
        )
        
        if response.status_code != 200:
            raise ConnectionError(f"Error al conectar con la API de Moodle (status {response.status_code})")
        
        data = response.json()
        
        if isinstance(data, dict) and "exception" in data:
            logger.debug(f"Error obteniendo intentos del quiz: {data.get('message', 'Unknown error')}")
            return []
        
        return data.get("attempts", []) if isinstance(data, dict) else data
    
    def get_quiz_grade(self, quiz_id, student_id, course_id):
        """
        Obtiene la calificación final de un estudiante en un quiz.
        Usa mod_quiz_get_user_best_grade que es más permisivo.
        
        Args:
            quiz_id: ID del quiz (instance id)
            student_id: ID del estudiante
            course_id: ID del curso (no usado pero mantenido para compatibilidad)
        
        Returns:
            Dict con información de la calificación o mensaje de error
        """
        # Usar mod_quiz_get_user_best_grade - más permisivo que gradereport
        response = requests.get(
            f"{self.base_url}/webservice/rest/server.php",
            params={
                "wstoken": self.token,
                "wsfunction": "mod_quiz_get_user_best_grade",
                "moodlewsrestformat": "json",
                "quizid": quiz_id,
                "userid": student_id
            }
        )
        
        if response.status_code != 200:
            logger.error(f"Error al obtener calificación del quiz (status {response.status_code})")
            return "Error de conexión"
        
        data = response.json()
        
        # Verificar si hay errores
        if isinstance(data, dict) and "exception" in data:
            error_code = data.get("errorcode", "")
            # Si no tiene permisos o no hay calificación, intentar método fallback
            logger.debug(f"mod_quiz_get_user_best_grade falló: {data.get('message', '')}")
            return self._get_quiz_grade_fallback(quiz_id, student_id)
        
        # Verificar si tiene calificación
        has_grade = data.get("hasgrade", False)
        if not has_grade:
            return "Sin intentos"
        
        # Extraer información
        grade = data.get("grade")
        if grade is None or grade == "":
            return "Sin calificación"
        
        try:
            grade_value = float(grade)
        except (ValueError, TypeError):
            return "Sin calificación"
        
        # En Moodle, la calificación del quiz suele estar sobre 10 por defecto
        # pero puede variar según la configuración
        max_grade = 10.0  # Valor por defecto común en Moodle
        
        # Intentar obtener más información del quiz
        quiz_info = self._get_quiz_info(quiz_id)
        if quiz_info:
            max_grade = float(quiz_info.get("grade", 10.0))
        
        percentage = (grade_value / max_grade) * 100.0 if max_grade > 0 else 0
        
        return {
            "quiz_id": quiz_id,
            "student_id": student_id,
            "grade": round(grade_value, 2),
            "max_grade": round(max_grade, 2),
            "percentage": round(percentage, 1),
            "has_grade": has_grade
        }
    
    def _get_quiz_grade_fallback(self, quiz_id, student_id):
        """
        Método alternativo para obtener calificaciones de quiz cuando gradereport no funciona.
        Intenta usar mod_quiz_get_user_attempts.
        
        Args:
            quiz_id: ID del quiz
            student_id: ID del estudiante
        
        Returns:
            Dict con información o mensaje de error
        """
        attempts = self.get_quiz_attempts(quiz_id, student_id)
        
        if not attempts:
            return "Sin intentos"
        
        # Filtrar intentos finalizados
        finished_attempts = [a for a in attempts if a.get("state") == "finished"]
        
        if not finished_attempts:
            return "Sin calificación (intentos no finalizados)"
        
        # Encontrar el mejor intento
        best_attempt = max(finished_attempts, key=lambda x: float(x.get("sumgrades", 0) or 0))
        
        sumgrades = float(best_attempt.get("sumgrades", 0) or 0)
        
        return {
            "quiz_id": quiz_id,
            "student_id": student_id,
            "grade": round(sumgrades, 2),
            "max_grade": 10.0,  # Valor por defecto
            "percentage": round((sumgrades / 10.0) * 100.0, 1),
            "attempt_number": best_attempt.get("attempt", 1),
            "state": best_attempt.get("state", "finished"),
            "timefinish": best_attempt.get("timefinish", 0),
            "total_attempts": len(attempts),
            "finished_attempts": len(finished_attempts)
        }
    
    def _get_quiz_info(self, quiz_id):
        """
        Obtiene información detallada de un quiz usando mod_quiz_get_quizzes_by_courses.
        Método auxiliar interno.
        
        Args:
            quiz_id: ID del quiz (instance id)
        
        Returns:
            Dict con información del quiz o None si hay error
        """
        try:
            response = requests.get(
                f"{self.base_url}/webservice/rest/server.php",
                params={
                    "wstoken": self.token,
                    "wsfunction": "mod_quiz_get_quizzes_by_courses",
                    "moodlewsrestformat": "json"
                }
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            if isinstance(data, dict) and "exception" in data:
                return None
            
            # Buscar el quiz específico en la lista
            quizzes = data.get("quizzes", [])
            for quiz in quizzes:
                if quiz.get("id") == quiz_id or quiz.get("coursemodule") == quiz_id:
                    return quiz
            
            return None
        except Exception as e:
            logger.debug(f"No se pudo obtener información del quiz {quiz_id}: {e}")
            return None
    
    def get_all_quiz_grades(self, course_id):
        """
        Obtiene todas las calificaciones de todos los quizzes de un curso.
        Útil para obtener un reporte completo del curso.
        
        Args:
            course_id: ID del curso
        
        Returns:
            Dict con estructura: {quiz_id: {student_id: grade_info}}
        """
        quizzes = self.get_quizzes(course_id)
        enrolled_users = self.get_users(course_id)
        
        results = {}
        
        for quiz in quizzes:
            quiz_id = quiz["quizid"]
            results[quiz_id] = {
                "quiz_name": quiz["name"],
                "grades": {}
            }
            
            for user in enrolled_users:
                grade_info = self.get_quiz_grade(quiz_id, user["id"], course_id)
                if grade_info not in ["Sin intentos", "Sin calificación (intentos no finalizados)", "Sin acceso", "Sin calificación", "Sin calificaciones"]:
                    results[quiz_id]["grades"][user["id"]] = grade_info
        
        return results

    