from moodle_client import MoodleClient
from rubric_parser import RubricParser
from ai_grader import AIGrader
from submission_cache import SubmissionCache
from logger_config import get_main_logger
from dotenv import load_dotenv
import os
import logging
from dataclasses import dataclass
from typing import List

logger = get_main_logger()

@dataclass
class SubmissionInfo:
    course_id: int
    course_name: str
    assignment_id: int
    assignment_name: str
    student_id: int
    student_username: str
    filenames: List[str]

@dataclass
class CourseInfo:
    course_id: int
    fullname: str
    shortname: str


def main():
    # load environment variables
    load_dotenv()
    MOODLE_URL = os.getenv("MOODLE_URL")
    TOKEN_MOODLE = os.getenv("TOKEN_MOODLE")
    COURSE_LIST = os.getenv("COURSE_LIST").split(",")

    # Initialize Moodle client and cache system
    moodle_client = MoodleClient(MOODLE_URL,TOKEN_MOODLE)
    moodle_client.connect()
    cache = SubmissionCache("submission_cache.json")
    
    # Mostrar estadísticas del caché al inicio
    stats = cache.get_stats()
    logger.info("="*60)
    logger.info("ESTADÍSTICAS DEL CACHÉ")
    logger.info("="*60)
    logger.info(f"Total de entregas en caché: {stats['total_entries']}")
    if stats['by_status']:
        logger.info(f"Por estado: {stats['by_status']}")
    logger.info("="*60 + "\n")
    
    submissions_info = []
    new_submissions = 0
    unchanged_submissions = 0

    for course in COURSE_LIST:
        course_data = moodle_client.get_courses(course)
        course_info = CourseInfo(
            course_data['courses'][0]['id'],
            course_data['courses'][0]['fullname'],
            course_data['courses'][0]['shortname']
        )
        logger.info(f"Processing Course: {course_info.fullname} (ID: {course_info.course_id})")
        # Get enrolled users and assignments for the course
        enrolled_users = moodle_client.get_users(course_info.course_id)
        assignments = moodle_client.get_assignmets(course_info.course_id)

        # Process each assignment and its submissions for each user download files
        logger.info(f"\nEncontradas {len(assignments.get('courses', [{}])[0].get('assignments', []))} tareas de asignación en el curso")
        
        for assignment in assignments["courses"][0]["assignments"]:
            logger.info(f"\n{'-'*60}")
            logger.info(f"ASIGNACIÓN: {assignment['name']} (ID: {assignment['id']})")
            logger.info(f"{'-'*60}")
            
            for user in enrolled_users:
                filenames = []
                submission = moodle_client.get_student_submissions(course_info.course_id, assignment["id"], user["id"])

                if submission == "Entrega no encontrada":
                    # No actualizar caché si no hay entrega
                    continue
                
                # Verificar si la entrega ha cambiado
                has_changed = cache.has_changed(
                    course_id=course_info.course_id,
                    assignment_id=assignment["id"],
                    student_id=user["id"],
                    submission_data=submission,
                    assignment_type="assign"
                )
                
                if has_changed:
                    logger.info(f"  ✓ {user['username']} (ID: {user['id']}) - NUEVA o MODIFICADA")
                    new_submissions += 1
                    
                    # Descargar archivos si existen
                    for plugin in submission.get("plugins", []):
                        if "fileareas" in plugin:
                            for filearea in plugin["fileareas"]:
                                for doc in filearea.get("files", []):
                                    filename = doc["filename"]
                                    file_url = doc['fileurl']
                                    try:
                                        downloaded_path = moodle_client.download_file(file_url, filename)
                                        filenames.append(downloaded_path)
                                        logger.info(f"      - {downloaded_path}")
                                    except Exception as e:
                                        logger.error(f"      Error descargando {filename}: {e}")

                    # Guardar la entrega en la lista
                    submissions_info.append(SubmissionInfo(
                        course_id=course_info.course_id,
                        course_name=course_info.fullname,
                        assignment_id=assignment["id"],
                        assignment_name=assignment["name"],
                        student_id=user["id"],
                        student_username=user["username"],
                        filenames=filenames
                    ))
                    
                    # Actualizar el caché
                    cache.update(
                        course_id=course_info.course_id,
                        assignment_id=assignment["id"],
                        student_id=user["id"],
                        submission_data=submission,
                        assignment_type="assign",
                        student_username=user["username"],
                        assignment_name=assignment["name"],
                        status="processed",
                        additional_info={"files_downloaded": len(filenames)}
                    )
                else:
                    logger.debug(f"  ○ {user['username']} (ID: {user['id']}) - SIN CAMBIOS (omitida)")
                    unchanged_submissions += 1
        
        vpl_assignments = moodle_client.get_vpl_assignments(course_info.course_id)
        logger.info(f"\nEncontradas {len(vpl_assignments)} tareas VPL en el curso")
        
        for vpl in vpl_assignments:
            logger.info(f"\n{'-'*60}")
            logger.info(f"VPL: {vpl['name']} (ID: {vpl['vplid']}, CMID: {vpl['cmid']})")
            logger.info(f"{'-'*60}")
            
            for user in enrolled_users:
                # Obtener la entrega del estudiante
                submission = moodle_client.get_vpl_submissions(
                    vpl['vplid'], 
                    course_info.course_id, 
                    user["id"], 
                    cmid=vpl['cmid']
                )
                
                # Verificar si es una entrega válida
                if submission == "Entrega no encontrada":
                    # No actualizar caché si no hay entrega
                    continue
                
                # Verificar si la entrega ha cambiado
                has_changed = cache.has_changed(
                    course_id=course_info.course_id,
                    assignment_id=vpl['vplid'],
                    student_id=user["id"],
                    submission_data=submission,
                    assignment_type="vpl"
                )
                
                if has_changed:
                    logger.info(f"  ✓ {user['username']} (ID: {user['id']}) - NUEVA o MODIFICADA")
                    new_submissions += 1
                    
                    # Procesar la entrega (aquí iría tu lógica de procesamiento/calificación)
                    # Por ahora solo mostramos la info
                    if isinstance(submission, list):
                        logger.info(f"    Archivos descargados: {len(submission)}")
                        for file_path in submission:
                            logger.info(f"      - {file_path}")
                    else:
                        logger.debug(f"    Datos: {str(submission)[:100]}...")
                    
                    # Actualizar el caché
                    cache.update(
                        course_id=course_info.course_id,
                        assignment_id=vpl['vplid'],
                        student_id=user["id"],
                        submission_data=submission,
                        assignment_type="vpl",
                        student_username=user["username"],
                        assignment_name=vpl["name"],
                        status="processed"
                    )
                else:
                    logger.debug(f"  ○ {user['username']} (ID: {user['id']}) - SIN CAMBIOS (omitida)")
                    unchanged_submissions += 1
        
        # Obtener y procesar quizzes del curso
        try:
            quizzes = moodle_client.get_quizzes(course_info.course_id)
            logger.info(f"\nEncontrados {len(quizzes)} quizzes en el curso")
        except Exception as e:
            logger.error(f"Error al obtener quizzes del curso {course_info.course_id}: {e}")
            quizzes = []
        
        for quiz in quizzes:
            logger.info(f"\n{'-'*60}")
            logger.info(f"QUIZ: {quiz.get('name', 'Sin nombre')} (ID: {quiz.get('quizid', 'N/A')}, CMID: {quiz.get('cmid', 'N/A')})")
            logger.info(f"{'-'*60}")
            
            # Validar que el quiz tiene los campos necesarios
            if 'quizid' not in quiz:
                logger.warning(f"Quiz sin ID válido, omitiendo")
                continue
            
            for user in enrolled_users:
                try:
                    # Obtener la calificación del estudiante en el quiz
                    grade_info = moodle_client.get_quiz_grade(quiz['quizid'], user["id"], course_info.course_id)
                    
                    # Si no tiene intentos o calificación, omitir
                    if isinstance(grade_info, str):
                        # No mostrar usuarios sin intentos para mantener el output limpio
                        continue
                    
                    # Validar que grade_info tiene los campos necesarios
                    required_fields = ['grade', 'max_grade', 'percentage']
                    if not all(field in grade_info for field in required_fields):
                        logger.warning(f"  ⚠ {user['username']} (ID: {user['id']}) - Datos incompletos del quiz")
                        continue
                    
                    # Verificar si la calificación ha cambiado
                    has_changed = cache.has_changed(
                        course_id=course_info.course_id,
                        assignment_id=quiz['quizid'],
                        student_id=user["id"],
                        submission_data=grade_info,
                        assignment_type="quiz"
                    )
                    
                    if has_changed:
                        logger.info(f"  ✓ {user['username']} (ID: {user['id']}) - NUEVA o MODIFICADA")
                        new_submissions += 1
                        
                        # Mostrar información de la calificación con manejo seguro de valores None
                        grade = grade_info.get('grade', 0)
                        max_grade = grade_info.get('max_grade', 0)
                        percentage = grade_info.get('percentage', 0)
                        has_grade = grade_info.get('has_grade', False)
                        
                        logger.info(f"    Calificación: {grade:.2f}/{max_grade:.2f} ({percentage:.1f}%)")
                        if has_grade:
                            logger.info(f"    Estado: Calificado")
                        
                        # Actualizar el caché
                        cache.update(
                            course_id=course_info.course_id,
                            assignment_id=quiz['quizid'],
                            student_id=user["id"],
                            submission_data=grade_info,
                            assignment_type="quiz",
                            student_username=user["username"],
                            assignment_name=quiz.get("name", "Quiz sin nombre"),
                            status="processed",
                            additional_info={
                                "grade": grade,
                                "max_grade": max_grade,
                                "percentage": percentage,
                                "has_grade": has_grade
                            }
                        )
                    else:
                        grade = grade_info.get('grade', 0)
                        max_grade = grade_info.get('max_grade', 0)
                        logger.debug(f"  ○ {user['username']} (ID: {user['id']}) - SIN CAMBIOS ({grade:.1f}/{max_grade:.1f})")
                        unchanged_submissions += 1
                        
                except Exception as e:
                    logger.error(f"  ✗ Error procesando quiz para {user['username']} (ID: {user['id']}): {e}")
                    continue
    
    # Resumen final
    logger.info(f"\n{'='*60}")
    logger.info("RESUMEN DE EJECUCIÓN")
    logger.info("="*60)
    logger.info(f"Entregas nuevas o modificadas: {new_submissions}")
    logger.info(f"Entregas sin cambios (omitidas): {unchanged_submissions}")
    logger.info(f"Total procesadas: {new_submissions + unchanged_submissions}")
    logger.info("="*60 + "\n")
                        
                    



    # # Initialize AI Grader
    # ai_grader = AIGrader()

    # # Grade each submission based on the rubric criteria
    # for submission in student_submissions:
    #     grade = ai_grader.grade_submission(submission, criteria)
    #     print(f"Submission ID: {submission.id}, Grade: {grade}")

if __name__ == "__main__":
    main()