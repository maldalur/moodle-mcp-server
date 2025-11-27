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
                        "section": section.get("name"),
                        "description": module.get("description", ""),  # Deskribapena
                        "description_clean": self._clean_html(module.get("description", ""))  # HTML gabe
                    })
        return vpl_activities
    
    def get_vpl_info(self, cmid: int) -> dict:
        """
        Lortu VPL zeregin baten informazio osoa mod_vpl_open erabiliz
        
        Args:
            cmid: Course Module ID
        
        Returns:
            Dict VPL informazioarekin (deskribapena, etab.)
        """
        try:
            response = requests.get(
                f"{self.base_url}/webservice/rest/server.php",
                params={
                    "wstoken": self.token,
                    "wsfunction": "mod_vpl_open",
                    "moodlewsrestformat": "json",
                    "id": cmid
                }
            )
            
            data = response.json()
            
            if isinstance(data, dict) and "exception" not in data:
                return {
                    "name": data.get("name", ""),
                    "intro": self._clean_html(data.get("intro", "")),
                    "intro_html": data.get("intro", ""),
                    "shortdescription": data.get("shortdescription", ""),
                    "example": data.get("example", ""),
                    "grade": data.get("grade", 0),
                    "duedate": data.get("duedate", 0),
                    "requirednet": data.get("requirednet", ""),
                    "restrictededitor": data.get("restrictededitor", 0)
                }
            
            return {"intro": "", "error": data.get("message", "No info")}
            
        except Exception as e:
            logger.error(f"Error lortu VPL info cmid={cmid}: {e}")
            return {"intro": "", "error": str(e)}



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

    def get_assignment_details(self, course_id: int, assignment_id: int) -> dict:
        """
        Lortu zeregin baten informazio osoa: deskribapena, rubrika, epeak, etab.
        
        Args:
            course_id: Kurtsoko IDa
            assignment_id: Zereginaren IDa
        
        Returns:
            Dict zehaztasun guztiekin
        """
        try:
            response = requests.get(
                f"{self.base_url}/webservice/rest/server.php",
                params={
                    "wstoken": self.token,
                    "wsfunction": "mod_assign_get_assignments",
                    "moodlewsrestformat": "json",
                    "courseids[0]": course_id,
                    "includenotenrolledcourses": 1
                }
            )
            
            data = response.json()
            
            if "courses" in data and data["courses"]:
                for course in data["courses"]:
                    for assignment in course.get("assignments", []):
                        if assignment.get("id") == assignment_id:
                            return {
                                "id": assignment.get("id"),
                                "name": assignment.get("name", ""),
                                "intro": self._clean_html(assignment.get("intro", "")),
                                "intro_html": assignment.get("intro", ""),
                                "introformat": assignment.get("introformat", 0),
                                "duedate": assignment.get("duedate", 0),
                                "cutoffdate": assignment.get("cutoffdate", 0),
                                "grade": assignment.get("grade", 0),
                                "maxattempts": assignment.get("maxattempts", -1),
                                "configs": self._parse_assignment_configs(assignment.get("configs", [])),
                                "introattachments": assignment.get("introattachments", [])
                            }
            
            return {"error": "Zeregina ez da aurkitu"}
            
        except Exception as e:
            logger.error(f"Error lortu zeregina {assignment_id}: {e}")
            return {"error": str(e)}
    
    def get_grading_definition(self, cmid: int) -> dict:
        """
        Lortu zeregin baten kalifikazio-definizioa (rubrika, guía, etab.)
        
        Args:
            cmid: Course Module ID (ez assignment ID!)
        
        Returns:
            Dict rubrika/guia informazioarekin
        """
        try:
            response = requests.get(
                f"{self.base_url}/webservice/rest/server.php",
                params={
                    "wstoken": self.token,
                    "wsfunction": "core_grading_get_definitions",
                    "moodlewsrestformat": "json",
                    "cmids[0]": cmid,
                    "activeonly": 0
                }
            )
            
            data = response.json()
            
            if "exception" in data:
                logger.warning(f"Ez dago rubrikarik cmid={cmid}: {data.get('message', '')}")
                return {"has_rubric": False, "message": data.get("message", "Sin rubrica")}
            
            if "areas" in data and data["areas"]:
                area = data["areas"][0]
                definitions = area.get("definitions", [])
                
                if definitions:
                    definition = definitions[0]
                    method = definition.get("method", "")
                    
                    result = {
                        "has_rubric": True,
                        "method": method,
                        "name": definition.get("name", ""),
                        "description": definition.get("description", "")
                    }
                    
                    # Rubrika-ren kasuan
                    if method == "rubric" and "rubric" in definition:
                        rubric = definition["rubric"]
                        criteria = []
                        
                        for criterion in rubric.get("rubric_criteria", []):
                            levels = []
                            for level in criterion.get("levels", []):
                                levels.append({
                                    "score": level.get("score", 0),
                                    "definition": self._clean_html(level.get("definition", ""))
                                })
                            
                            criteria.append({
                                "id": criterion.get("id"),
                                "description": self._clean_html(criterion.get("description", "")),
                                "sortorder": criterion.get("sortorder", 0),
                                "levels": sorted(levels, key=lambda x: x["score"])
                            })
                        
                        result["criteria"] = sorted(criteria, key=lambda x: x["sortorder"])
                        result["rubric_text"] = self._format_rubric_as_text(result["criteria"])
                    
                    # Guía de calificación
                    elif method == "guide" and "guide" in definition:
                        guide = definition["guide"]
                        criteria = []
                        
                        for criterion in guide.get("guide_criteria", []):
                            criteria.append({
                                "id": criterion.get("id"),
                                "shortname": criterion.get("shortname", ""),
                                "description": self._clean_html(criterion.get("description", "")),
                                "maxscore": criterion.get("maxscore", 0),
                                "sortorder": criterion.get("sortorder", 0)
                            })
                        
                        result["criteria"] = sorted(criteria, key=lambda x: x["sortorder"])
                        result["guide_text"] = self._format_guide_as_text(result["criteria"])
                    
                    return result
            
            return {"has_rubric": False, "message": "No se encontró definición de calificación"}
            
        except Exception as e:
            logger.error(f"Error lortu rubrika cmid={cmid}: {e}")
            return {"has_rubric": False, "error": str(e)}
    
    def get_assignment_cmid(self, course_id: int, assignment_id: int) -> int:
        """
        Lortu assignment baten Course Module ID (cmid)
        
        Args:
            course_id: Kurtsoko IDa
            assignment_id: Zereginaren instance IDa
        
        Returns:
            cmid edo None
        """
        try:
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
            
            for section in data:
                for module in section.get("modules", []):
                    if module.get("modname") == "assign" and module.get("instance") == assignment_id:
                        return module.get("id")
            
            return None
            
        except Exception as e:
            logger.error(f"Error lortu cmid assignment_id={assignment_id}: {e}")
            return None
    
    def get_full_assignment_info(self, course_id: int, assignment_id: int) -> dict:
        """
        Lortu zeregin baten informazio OSOA: deskribapena + rubrika
        
        Args:
            course_id: Kurtsoko IDa
            assignment_id: Zereginaren IDa
        
        Returns:
            Dict informazio guztiekin
        """
        # Lortu oinarrizko informazioa
        details = self.get_assignment_details(course_id, assignment_id)
        
        if "error" in details:
            return details
        
        # Lortu cmid rubrikarako
        cmid = self.get_assignment_cmid(course_id, assignment_id)
        
        if cmid:
            details["cmid"] = cmid
            grading = self.get_grading_definition(cmid)
            details["grading"] = grading
            
            # Sortu testu osoa AI-rako
            details["full_criteria_text"] = self._build_full_criteria_text(details, grading)
        else:
            details["grading"] = {"has_rubric": False, "message": "CMID ez da aurkitu"}
            details["full_criteria_text"] = details.get("intro", "")
        
        return details
    
    def _clean_html(self, html_text: str) -> str:
        """HTML etiketak kendu eta testu garbia itzuli"""
        import re
        if not html_text:
            return ""
        
        # HTML etiketak kendu
        text = re.sub(r'<[^>]+>', ' ', html_text)
        # Entitate bereziak ordezkatu
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        # Zuriune anitzak kendu
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _parse_assignment_configs(self, configs: list) -> dict:
        """Assignment konfigurazioak parseatu"""
        result = {}
        for config in configs:
            plugin = config.get("plugin", "")
            subtype = config.get("subtype", "")
            name = config.get("name", "")
            value = config.get("value", "")
            
            key = f"{plugin}_{name}" if plugin else name
            result[key] = value
        
        return result
    
    def _format_rubric_as_text(self, criteria: list) -> str:
        """Rubrika testu formatuan"""
        lines = ["RÚBRICA DE EVALUACIÓN:", "=" * 40]
        
        for i, criterion in enumerate(criteria, 1):
            lines.append(f"\n{i}. {criterion['description']}")
            lines.append("-" * 30)
            
            for level in criterion.get("levels", []):
                lines.append(f"   • {level['score']} puntu: {level['definition']}")
        
        return "\n".join(lines)
    
    def _format_guide_as_text(self, criteria: list) -> str:
        """Guía de calificación testu formatuan"""
        lines = ["GUÍA DE CALIFICACIÓN:", "=" * 40]
        
        for i, criterion in enumerate(criteria, 1):
            lines.append(f"\n{i}. {criterion.get('shortname', 'Criterio')} (máx. {criterion.get('maxscore', 0)} puntos)")
            lines.append(f"   {criterion['description']}")
        
        return "\n".join(lines)
    
    def _build_full_criteria_text(self, details: dict, grading: dict) -> str:
        """Sortu testu osoa AI analisirako"""
        parts = []
        
        # Deskribapena
        if details.get("intro"):
            parts.append("DESCRIPCIÓN DE LA TAREA:")
            parts.append("=" * 40)
            parts.append(details["intro"])
            parts.append("")
        
        # Epea
        if details.get("duedate"):
            from datetime import datetime
            due = datetime.fromtimestamp(details["duedate"])
            parts.append(f"FECHA LÍMITE: {due.strftime('%Y-%m-%d %H:%M')}")
            parts.append("")
        
        # Nota máxima
        if details.get("grade"):
            parts.append(f"PUNTUACIÓN MÁXIMA: {details['grade']}")
            parts.append("")
        
        # Rubrika edo guía
        if grading.get("has_rubric"):
            if grading.get("rubric_text"):
                parts.append(grading["rubric_text"])
            elif grading.get("guide_text"):
                parts.append(grading["guide_text"])
        
        return "\n".join(parts)

    # =========================================================================
    # FOROAK - Forums
    # =========================================================================
    
    def get_forums(self, course_id: int) -> list:
        """
        Lortu kurtso bateko foro guztiak
        
        Args:
            course_id: Kurtsoko IDa
        
        Returns:
            Foroen zerrenda: [{"id": 1, "name": "Foro 1", "type": "general", ...}, ...]
        """
        try:
            response = requests.get(
                f"{self.base_url}/webservice/rest/server.php",
                params={
                    "wstoken": self.token,
                    "wsfunction": "mod_forum_get_forums_by_courses",
                    "moodlewsrestformat": "json",
                    "courseids[0]": course_id
                }
            )
            
            if response.status_code != 200:
                raise ConnectionError(f"Error al conectar con Moodle API (status {response.status_code})")
            
            data = response.json()
            
            if isinstance(data, dict) and "exception" in data:
                logger.error(f"Error obteniendo foros: {data.get('message', '')}")
                return []
            
            forums = []
            for forum in data:
                forums.append({
                    "id": forum.get("id"),
                    "course": forum.get("course"),
                    "name": forum.get("name"),
                    "intro": self._clean_html(forum.get("intro", "")),
                    "intro_html": forum.get("intro", ""),
                    "type": forum.get("type"),  # general, news, qanda, social, etc.
                    "cmid": forum.get("cmid"),
                    "numdiscussions": forum.get("numdiscussions", 0),
                    "timemodified": forum.get("timemodified", 0),
                    "is_task": self._is_forum_task(forum)  # Foro-tarea den ala ez
                })
            
            return forums
            
        except Exception as e:
            logger.error(f"Error lortu foroak course_id={course_id}: {e}")
            return []
    
    def _is_forum_task(self, forum: dict) -> bool:
        """
        Foroa tarea modukoa den egiaztatu hainbat irizpideren arabera
        
        Args:
            forum: Foroaren datuak
        
        Returns:
            True foroa tarea bada, False bestela
        """
        # Hitz gakoak tarea identifikatzeko
        task_keywords = [
            'tarea', 'práctica', 'entrega', 'ejercicio', 'actividad',
            'trabajo', 'evaluable', 'obligatorio', 'calificable',
            'task', 'assignment', 'exercise', 'submission',
            'lana', 'ariketa', 'zeregina', 'entrega'  # Euskaraz ere
        ]
        
        # Izenean edo deskribapeanean bilatu
        name = forum.get("name", "").lower()
        intro = forum.get("intro", "").lower()
        
        for keyword in task_keywords:
            if keyword in name or keyword in intro:
                return True
        
        # Q&A motako foroak sarritan tarearentzako dira
        if forum.get("type") == "qanda":
            return True
        
        return False
    
    def get_task_forums(self, course_id: int) -> list:
        """
        Lortu kurtso bateko TAREA moduko foroak bakarrik
        
        Args:
            course_id: Kurtsoko IDa
        
        Returns:
            Foro-tareen zerrenda
        """
        all_forums = self.get_forums(course_id)
        return [f for f in all_forums if f.get('is_task', False)]
    
    def get_forum_with_student_posts(self, forum_id: int) -> dict:
        """
        Lortu foroaren eduki osoa ikasleen mezuekin bilduta
        
        Args:
            forum_id: Foroaren IDa
        
        Returns:
            Dict foroaren informazio osoarekin eta ikasle bakoitzaren mezuekin
        """
        result = {
            'forum_id': forum_id,
            'discussions': [],
            'students': {},  # {user_id: {'info': {...}, 'posts': [...]}}
            'total_posts': 0
        }
        
        discussions_data = self.get_forum_discussions(forum_id)
        
        for disc in discussions_data.get('discussions', []):
            posts_data = self.get_discussion_posts(disc['id'])
            
            disc_info = {
                'id': disc['id'],
                'name': disc['name'],
                'posts': posts_data.get('posts', [])
            }
            result['discussions'].append(disc_info)
            
            # Bildu ikasle bakoitzaren mezuak
            for post in posts_data.get('posts', []):
                author = post.get('author', {})
                user_id = author.get('id')
                
                if user_id:
                    if user_id not in result['students']:
                        result['students'][user_id] = {
                            'info': {
                                'id': user_id,
                                'fullname': author.get('fullname', 'Desconocido')
                            },
                            'posts': []
                        }
                    result['students'][user_id]['posts'].append(post)
                    result['total_posts'] += 1
        
        return result

    def get_forum_discussions(self, forum_id: int, sort_by: str = "timemodified", sort_direction: str = "DESC", page: int = 0, per_page: int = 50) -> dict:
        """
        Lortu foro bateko eztabaida guztiak
        
        Args:
            forum_id: Foroaren IDa
            sort_by: Ordenatzeko eremua (timemodified, created, replies, etc.)
            sort_direction: Ordena norabidea (ASC, DESC)
            page: Orria (0-tik hasita)
            per_page: Eztabaida kopurua orriko
        
        Returns:
            Dict eztabaidekin eta metadatuekin
        """
        try:
            response = requests.get(
                f"{self.base_url}/webservice/rest/server.php",
                params={
                    "wstoken": self.token,
                    "wsfunction": "mod_forum_get_forum_discussions",
                    "moodlewsrestformat": "json",
                    "forumid": forum_id,
                    "sortby": sort_by,
                    "sortdirection": sort_direction,
                    "page": page,
                    "perpage": per_page
                }
            )
            
            if response.status_code != 200:
                raise ConnectionError(f"Error al conectar con Moodle API (status {response.status_code})")
            
            data = response.json()
            
            if isinstance(data, dict) and "exception" in data:
                logger.error(f"Error obteniendo discusiones: {data.get('message', '')}")
                return {"discussions": [], "error": data.get("message", "")}
            
            discussions = []
            for disc in data.get("discussions", []):
                discussions.append({
                    "id": disc.get("id"),
                    "discussion": disc.get("discussion"),
                    "name": disc.get("name"),  # Título
                    "subject": disc.get("subject"),
                    "message": self._clean_html(disc.get("message", "")),
                    "message_html": disc.get("message", ""),
                    "userid": disc.get("userid"),
                    "userfullname": disc.get("userfullname"),
                    "usermodified": disc.get("usermodified"),
                    "usermodifiedfullname": disc.get("usermodifiedfullname"),
                    "created": disc.get("created", 0),
                    "modified": disc.get("modified", 0),
                    "timemodified": disc.get("timemodified", 0),
                    "numreplies": disc.get("numreplies", 0),
                    "pinned": disc.get("pinned", False),
                    "locked": disc.get("locked", False),
                    "starred": disc.get("starred", False),
                    "attachment": disc.get("attachment", False),
                    "attachments": disc.get("attachments", [])
                })
            
            return {
                "forum_id": forum_id,
                "total_discussions": len(discussions),
                "discussions": discussions
            }
            
        except Exception as e:
            logger.error(f"Error lortu eztabaidak forum_id={forum_id}: {e}")
            return {"discussions": [], "error": str(e)}
    
    def get_discussion_posts(self, discussion_id: int) -> dict:
        """
        Lortu eztabaida bateko mezu guztiak (erantzunak barne)
        
        Args:
            discussion_id: Eztabaidaren IDa
        
        Returns:
            Dict mezuekin hierarkian
        """
        try:
            response = requests.get(
                f"{self.base_url}/webservice/rest/server.php",
                params={
                    "wstoken": self.token,
                    "wsfunction": "mod_forum_get_discussion_posts",
                    "moodlewsrestformat": "json",
                    "discussionid": discussion_id,
                    "sortby": "created",
                    "sortdirection": "ASC"
                }
            )
            
            if response.status_code != 200:
                raise ConnectionError(f"Error al conectar con Moodle API (status {response.status_code})")
            
            data = response.json()
            
            if isinstance(data, dict) and "exception" in data:
                logger.error(f"Error obteniendo posts: {data.get('message', '')}")
                return {"posts": [], "error": data.get("message", "")}
            
            posts = []
            for post in data.get("posts", []):
                posts.append({
                    "id": post.get("id"),
                    "discussionid": post.get("discussionid"),
                    "parentid": post.get("parentid"),  # 0 = post originala
                    "subject": post.get("subject"),
                    "message": self._clean_html(post.get("message", "")),
                    "message_html": post.get("message", ""),
                    "author": {
                        "id": post.get("author", {}).get("id"),
                        "fullname": post.get("author", {}).get("fullname"),
                        "profileimageurl": post.get("author", {}).get("profileimageurl")
                    },
                    "timecreated": post.get("timecreated", 0),
                    "timemodified": post.get("timemodified", 0),
                    "hasparent": post.get("hasparent", False),
                    "haschildren": len(post.get("children", [])) > 0,
                    "attachments": post.get("attachments", [])
                })
            
            return {
                "discussion_id": discussion_id,
                "total_posts": len(posts),
                "posts": posts
            }
            
        except Exception as e:
            logger.error(f"Error lortu mezuak discussion_id={discussion_id}: {e}")
            return {"posts": [], "error": str(e)}
    
    def get_unanswered_discussions(self, course_id: int) -> list:
        """
        Lortu irakaslearen erantzunik gabeko eztabaidak
        (Ikasleen galdera edo mezuak)
        
        Args:
            course_id: Kurtsoko IDa
        
        Returns:
            Erantzun gabe dauden eztabaiden zerrenda
        """
        unanswered = []
        
        # Lortu kurtso honetako foro guztiak
        forums = self.get_forums(course_id)
        
        for forum in forums:
            # Lortu eztabaidak
            result = self.get_forum_discussions(forum["id"])
            
            for disc in result.get("discussions", []):
                # Eztabaida ireki eta erantzunik ez badu...
                # edo azken mezua ikasle batena bada
                if disc.get("numreplies", 0) == 0:
                    disc["forum_name"] = forum["name"]
                    disc["forum_id"] = forum["id"]
                    disc["needs_response"] = True
                    unanswered.append(disc)
                else:
                    # Egiaztatu azken mezua nork idatzi duen
                    posts_result = self.get_discussion_posts(disc["id"])
                    posts = posts_result.get("posts", [])
                    
                    if posts:
                        # Azken mezua lortu
                        last_post = max(posts, key=lambda p: p.get("timecreated", 0))
                        
                        # Hemen irakaslea den egiaztatu beharko litzateke
                        # Oraingoz, parentid > 0 badu eta erantzunik ez badu markatu
                        if last_post.get("parentid", 0) == 0:
                            # Post originala da, ez erantzuna
                            pass
                        else:
                            # Erantzun bat da
                            disc["forum_name"] = forum["name"]
                            disc["forum_id"] = forum["id"]
                            disc["last_post"] = last_post
                            disc["needs_response"] = False
        
        return unanswered
    
    def get_all_forum_content(self, course_id: int) -> dict:
        """
        Lortu kurtso bateko foro eduki osoa (foroak, eztabaidak, mezuak)
        
        Args:
            course_id: Kurtsoko IDa
        
        Returns:
            Dict foro informazio guztiekin
        """
        result = {
            "course_id": course_id,
            "forums": [],
            "total_discussions": 0,
            "total_posts": 0,
            "unanswered_count": 0
        }
        
        forums = self.get_forums(course_id)
        
        for forum in forums:
            forum_data = {
                "id": forum["id"],
                "name": forum["name"],
                "type": forum["type"],
                "intro": forum["intro"],
                "discussions": []
            }
            
            discussions_result = self.get_forum_discussions(forum["id"])
            
            for disc in discussions_result.get("discussions", []):
                # Lortu eztabaidako mezu guztiak
                posts_result = self.get_discussion_posts(disc["id"])
                
                disc_data = {
                    "id": disc["id"],
                    "name": disc["name"],
                    "author": disc["userfullname"],
                    "created": disc["created"],
                    "numreplies": disc["numreplies"],
                    "posts": posts_result.get("posts", [])
                }
                
                forum_data["discussions"].append(disc_data)
                result["total_discussions"] += 1
                result["total_posts"] += len(disc_data["posts"])
                
                if disc["numreplies"] == 0:
                    result["unanswered_count"] += 1
            
            result["forums"].append(forum_data)
        
        return result
