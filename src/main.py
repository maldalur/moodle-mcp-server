from moodle_client import MoodleClient
from rubric_parser import RubricParser
from ai_analyzer import AIAnalyzer
from report_generator import ReportGenerator
from submission_cache import SubmissionCache
from logger_config import get_main_logger
from dotenv import load_dotenv
import os
import logging
from dataclasses import dataclass
from typing import List, Dict, Any
from collections import defaultdict

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

    # Initialize Moodle client, cache system, AI analyzer and report generator
    moodle_client = MoodleClient(MOODLE_URL,TOKEN_MOODLE)
    moodle_client.connect()
    cache = SubmissionCache("submission_cache.json")
    ai_analyzer = AIAnalyzer(model="qwen3:30b-a3b",think=False)
    report_generator = ReportGenerator(output_dir="reports")
    
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
    
    # Almacenar entregas por estudiante para análisis
    student_submissions_map = defaultdict(list)

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
        # asegurarse de que existan asignaciones
        if "courses" not in assignments or not assignments["courses"] or "assignments" not in assignments["courses"][0]:
            logger.info(f"No se encontraron asignaciones en el curso {course_info.fullname} (ID: {course_info.course_id})")
        else:
            logger.info(f"\nEncontradas {len(assignments.get('courses', [{}])[0].get('assignments', []))} tareas de asignación en el curso")
            
            for assignment in assignments["courses"][0]["assignments"]:
                logger.info(f"\n{'-'*60}")
                logger.info(f"ASIGNACIÓN: {assignment['name']} (ID: {assignment['id']})")
                logger.info(f"{'-'*60}")
                
                # Lortu zereginaren informazio osoa (deskribapena + rubrika)
                assignment_full_info = moodle_client.get_full_assignment_info(
                    course_info.course_id, 
                    assignment['id']
                )
                
                if assignment_full_info.get('grading', {}).get('has_rubric'):
                    logger.info(f"  📋 Rubrika aurkitua: {assignment_full_info['grading'].get('method', 'unknown')}")
                
                # Lortu ebaluazio-irizpideak AI-rako
                full_criteria = assignment_full_info.get('full_criteria_text', assignment.get('intro', ''))
                
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

                        # Analizar con IA si hay archivos descargados
                        ai_analysis = None
                        if filenames:
                            logger.info(f"      Analizando con IA...")
                            submission_data = {
                                'filenames': filenames,
                                'student_username': user['username'],
                                'assignment_name': assignment['name'],
                                'timemodified': submission.get('timemodified', 0),
                                'assignment_intro': assignment_full_info.get('intro', ''),
                                'max_grade': assignment_full_info.get('grade', 10),
                                'has_rubric': assignment_full_info.get('grading', {}).get('has_rubric', False)
                            }
                            # Pasatu irizpide osoak (deskribapena + rubrika)
                            ai_analysis = ai_analyzer.analyze_submission(submission_data, full_criteria)
                            
                            if ai_analysis.get('status') == 'success':
                                logger.info(f"      📊 Calificación sugerida: {ai_analysis.get('suggested_grade', 'N/A')}/10")
                                logger.info(f"      💬 URLs encontradas: {ai_analysis.get('urls_found', 0)}")

                        # Guardar la entrega con análisis
                        submission_entry = {
                            'course_id': course_info.course_id,
                            'course_name': course_info.fullname,
                            'assignment_id': assignment["id"],
                            'assignment_name': assignment["name"],
                            'assignment_type': 'assign',
                            'student_id': user["id"],
                            'student_username': user["username"],
                            'filenames': filenames,
                            'timemodified': submission.get('timemodified', 0),
                            'status': submission.get('status', 'submitted'),
                            'ai_analysis': ai_analysis
                        }
                        
                        submissions_info.append(submission_entry)
                        student_submissions_map[user["id"]].append(submission_entry)
                        
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
                            additional_info={
                                "files_downloaded": len(filenames),
                                "ai_analyzed": ai_analysis is not None,
                                "suggested_grade": ai_analysis.get('suggested_grade') if ai_analysis else None,
                                "ai_analysis": ai_analysis  # AI analisi osoa gorde
                            }
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
            
            # VPL-ren informazio osoa lortu (deskribapena)
            vpl_info = moodle_client.get_vpl_info(vpl['cmid'])
            vpl_intro = vpl_info.get('intro', '') or vpl.get('description_clean', '')
            
            if vpl_intro:
                logger.info(f"  📝 Deskribapena aurkitua ({len(vpl_intro)} karaktere)")
            
            # VPL-ren rubrika lortu (cmid erabiliz)
            vpl_grading = moodle_client.get_grading_definition(vpl['cmid'])
            vpl_rubric = ""
            
            if vpl_grading.get('has_rubric'):
                logger.info(f"  📋 Rubrika aurkitua: {vpl_grading.get('method', 'unknown')}")
                vpl_rubric = vpl_grading.get('rubric_text', '') or vpl_grading.get('guide_text', '')
            
            # Sortu irizpide osoak: deskribapena + rubrika
            full_vpl_criteria_parts = []
            if vpl_intro:
                full_vpl_criteria_parts.append(f"DESCRIPCIÓN DE LA TAREA:\n{'='*40}\n{vpl_intro}")
            if vpl_rubric:
                full_vpl_criteria_parts.append(vpl_rubric)
            
            full_vpl_criteria = "\n\n".join(full_vpl_criteria_parts)
            
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
                    
                    # Procesar archivos VPL
                    filenames = []
                    if isinstance(submission, list):
                        filenames = submission
                        logger.info(f"    Archivos descargados: {len(filenames)}")
                        for file_path in filenames:
                            logger.info(f"      - {file_path}")
                    else:
                        logger.debug(f"    Datos: {str(submission)[:100]}...")
                    
                    # Analizar con IA si hay archivos
                    ai_analysis = None
                    if filenames:
                        logger.info(f"      Analizando con IA...")
                        submission_data = {
                            'filenames': filenames,
                            'student_username': user['username'],
                            'assignment_name': vpl['name'],
                            'timemodified': 0,  # VPL no siempre tiene este campo
                            'has_rubric': vpl_grading.get('has_rubric', False)
                        }
                        # Pasatu irizpide osoak (deskribapena + rubrika)
                        ai_analysis = ai_analyzer.analyze_submission(submission_data, full_vpl_criteria)
                        
                        if ai_analysis.get('status') == 'success':
                            logger.info(f"      📊 Calificación sugerida: {ai_analysis.get('suggested_grade', 'N/A')}/10")
                            logger.info(f"      💬 URLs encontradas: {ai_analysis.get('urls_found', 0)}")
                    
                    # Guardar entrega con análisis
                    submission_entry = {
                        'course_id': course_info.course_id,
                        'course_name': course_info.fullname,
                        'assignment_id': vpl['vplid'],
                        'assignment_name': vpl["name"],
                        'assignment_type': 'vpl',
                        'student_id': user["id"],
                        'student_username': user["username"],
                        'filenames': filenames,
                        'timemodified': 0,
                        'status': 'submitted',
                        'ai_analysis': ai_analysis
                    }
                    
                    student_submissions_map[user["id"]].append(submission_entry)
                    
                    # Actualizar el caché
                    cache.update(
                        course_id=course_info.course_id,
                        assignment_id=vpl['vplid'],
                        student_id=user["id"],
                        submission_data=submission,
                        assignment_type="vpl",
                        student_username=user["username"],
                        assignment_name=vpl["name"],
                        status="processed",
                        additional_info={
                            "files_downloaded": len(filenames),
                            "ai_analyzed": ai_analysis is not None,
                            "suggested_grade": ai_analysis.get('suggested_grade') if ai_analysis else None,
                            "ai_analysis": ai_analysis  # AI analisi osoa gorde
                        }
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
                        
                        # Guardar quiz para el estudiante
                        submission_entry = {
                            'course_id': course_info.course_id,
                            'course_name': course_info.fullname,
                            'assignment_id': quiz['quizid'],
                            'assignment_name': quiz.get("name", "Quiz sin nombre"),
                            'assignment_type': 'quiz',
                            'student_id': user["id"],
                            'student_username': user["username"],
                            'filenames': [],
                            'timemodified': 0,
                            'status': 'graded',
                            'grade': grade,
                            'max_grade': max_grade,
                            'percentage': percentage
                        }
                        
                        student_submissions_map[user["id"]].append(submission_entry)
                        
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
        
        # =====================================================================
        # FORO-TAREAS: Obtener y procesar foros que son tareas evaluables
        # =====================================================================
        try:
            task_forums = moodle_client.get_task_forums(course_info.course_id)
            logger.info(f"\nEncontrados {len(task_forums)} foros-tarea en el curso")
        except Exception as e:
            logger.error(f"Error al obtener foros-tarea del curso {course_info.course_id}: {e}")
            task_forums = []
        
        for forum in task_forums:
            logger.info(f"\n{'-'*60}")
            logger.info(f"FORO-TAREA: {forum.get('name', 'Sin nombre')} (ID: {forum.get('id', 'N/A')})")
            logger.info(f"  Tipo: {forum.get('type', 'general')} | Discusiones: {forum.get('numdiscussions', 0)}")
            logger.info(f"{'-'*60}")
            
            # Validar que el foro tiene ID
            if 'id' not in forum:
                logger.warning(f"Foro sin ID válido, omitiendo")
                continue
            
            # Obtener descripción/instrucciones del foro para criterios
            forum_intro = forum.get('intro', '')
            forum_criteria = f"""INSTRUCCIONES DEL FORO-TAREA:
{'='*40}
{forum_intro if forum_intro else 'No hay instrucciones específicas.'}

CRITERIOS DE EVALUACIÓN GENERALES:
- Relevancia de la aportación al tema
- Profundidad del análisis
- Originalidad y valor añadido
- Claridad en la expresión
- Interacción con otros compañeros
"""
            
            # Obtener todas las discusiones y posts del foro
            try:
                forum_data = moodle_client.get_forum_with_student_posts(forum['id'])
                forum_data['name'] = forum.get('name', 'Foro sin nombre')
                forum_data['intro'] = forum_intro
                forum_data['type'] = forum.get('type', 'general')
            except Exception as e:
                logger.error(f"  Error obteniendo datos del foro: {e}")
                continue
            
            # Si no hay participaciones, continuar
            if not forum_data.get('students'):
                logger.info(f"  Sin participaciones de estudiantes")
                continue
            
            logger.info(f"  📊 {len(forum_data['students'])} estudiantes con participación")
            logger.info(f"  📝 {forum_data.get('total_posts', 0)} posts totales")
            
            # Procesar cada estudiante que ha participado
            for user_id, student_data in forum_data['students'].items():
                student_info = student_data['info']
                student_posts = student_data['posts']
                
                # Buscar el usuario en enrolled_users para más info
                enrolled_user = next(
                    (u for u in enrolled_users if u['id'] == int(user_id)),
                    {'id': int(user_id), 'username': student_info.get('fullname', f'student_{user_id}')}
                )
                
                # Crear datos de submission para verificar caché
                submission_data_for_cache = {
                    'posts_count': len(student_posts),
                    'last_post_time': max((p.get('timecreated', 0) for p in student_posts), default=0),
                    'total_words': sum(len(p.get('message', '').split()) for p in student_posts)
                }
                
                # Verificar si ha cambiado
                has_changed = cache.has_changed(
                    course_id=course_info.course_id,
                    assignment_id=forum['id'],
                    student_id=int(user_id),
                    submission_data=submission_data_for_cache,
                    assignment_type="forum_task"
                )
                
                if has_changed:
                    logger.info(f"  ✓ {enrolled_user['username']} (ID: {user_id}) - NUEVA o MODIFICADA")
                    logger.info(f"      Posts: {len(student_posts)} | Palabras: {submission_data_for_cache['total_words']}")
                    new_submissions += 1
                    
                    # Analizar con IA
                    logger.info(f"      Analizando participación con IA...")
                    ai_analysis = ai_analyzer.evaluate_forum_as_task(
                        student_posts=student_posts,
                        forum_info=forum_data,
                        task_criteria=forum_criteria,
                        student_info={
                            'id': int(user_id),
                            'fullname': student_info.get('fullname', enrolled_user['username'])
                        }
                    )
                    
                    if ai_analysis.get('status') == 'success':
                        grade = ai_analysis.get('grade')
                        logger.info(f"      📊 Calificación sugerida: {grade}/10")
                        
                        # Mostrar calidad de participación
                        quality = ai_analysis.get('participation_quality', {})
                        if quality:
                            logger.info(f"      📈 Calidad: Relevancia={quality.get('relevance', '-')}/5, "
                                       f"Profundidad={quality.get('depth', '-')}/5, "
                                       f"Originalidad={quality.get('originality', '-')}/5")
                        
                        # Mostrar si cumple requisitos
                        if ai_analysis.get('meets_requirements'):
                            logger.info(f"      ✅ Cumple requisitos mínimos")
                        else:
                            logger.info(f"      ⚠️ No cumple todos los requisitos")
                    else:
                        logger.warning(f"      ⚠️ Error en análisis IA: {ai_analysis.get('error', 'Unknown')}")
                    
                    # Guardar entrega
                    submission_entry = {
                        'course_id': course_info.course_id,
                        'course_name': course_info.fullname,
                        'assignment_id': forum['id'],
                        'assignment_name': forum.get('name', 'Foro-tarea'),
                        'assignment_type': 'forum_task',
                        'student_id': int(user_id),
                        'student_username': enrolled_user['username'],
                        'filenames': [],  # Foros no tienen archivos
                        'timemodified': submission_data_for_cache['last_post_time'],
                        'status': 'submitted',
                        'posts_count': len(student_posts),
                        'total_words': submission_data_for_cache['total_words'],
                        'ai_analysis': ai_analysis
                    }
                    
                    student_submissions_map[int(user_id)].append(submission_entry)
                    
                    # Actualizar caché
                    cache.update(
                        course_id=course_info.course_id,
                        assignment_id=forum['id'],
                        student_id=int(user_id),
                        submission_data=submission_data_for_cache,
                        assignment_type="forum_task",
                        student_username=enrolled_user['username'],
                        assignment_name=forum.get('name', 'Foro-tarea'),
                        status="processed",
                        additional_info={
                            "posts_count": len(student_posts),
                            "total_words": submission_data_for_cache['total_words'],
                            "ai_analyzed": ai_analysis.get('status') == 'success',
                            "suggested_grade": ai_analysis.get('grade'),
                            "meets_requirements": ai_analysis.get('meets_requirements', False),
                            "participation_quality": ai_analysis.get('participation_quality', {}),
                            "ai_analysis": ai_analysis
                        }
                    )
                else:
                    logger.debug(f"  ○ {enrolled_user['username']} (ID: {user_id}) - SIN CAMBIOS")
                    unchanged_submissions += 1
    
    # Resumen final
    logger.info(f"\n{'='*60}")
    logger.info("RESUMEN DE EJECUCIÓN")
    logger.info("="*60)
    logger.info(f"Entregas nuevas o modificadas: {new_submissions}")
    logger.info(f"Entregas sin cambios (omitidas): {unchanged_submissions}")
    logger.info(f"Total procesadas: {new_submissions + unchanged_submissions}")
    logger.info("="*60 + "\n")
    
    # =========================================================================
    # GENERACIÓN DE INFORMES Y ANÁLISIS DE RIESGO
    # =========================================================================
    logger.info("\n" + "="*60)
    logger.info("GENERANDO INFORMES DE ANÁLISIS")
    logger.info("="*60 + "\n")
    
    # Generar informes por estudiante
    all_student_reports = []
    
    for student_id, submissions in student_submissions_map.items():
        if not submissions:
            continue
        
        # Obtener info del estudiante
        student_info = next(
            (user for user in enrolled_users if user['id'] == student_id),
            {'id': student_id, 'username': f'student_{student_id}'}
        )
        
        logger.info(f"Generando informe para: {student_info['username']}")
        
        # Generar informe del estudiante
        student_report = ai_analyzer.generate_student_report(submissions, student_info)
        all_student_reports.append(student_report)
        
        # Mostrar resumen en consola
        risk_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
        logger.info(f"  {risk_icon[student_report['risk_level']]} Nivel de riesgo: {student_report['risk_level'].upper()}")
        
        if student_report.get('risk_reasons'):
            for reason in student_report['risk_reasons'][:2]:  # Mostrar solo 2 razones
                logger.info(f"    - {reason}")
        
        # Generar archivo de informe detallado (solo para estudiantes en riesgo)
        if student_report['risk_level'] in ['high', 'medium']:
            try:
                report_path = report_generator.generate_student_report(
                    student_report,
                    submissions
                )
                logger.info(f"  📄 Informe guardado: {report_path}")
            except Exception as e:
                logger.error(f"  Error generando informe: {e}")
    
    # Generar informe general del curso
    logger.info("\n" + "-"*60)
    logger.info("Generando informe general del curso...")
    logger.info("-"*60)
    
    course_report = ai_analyzer.generate_course_report(all_student_reports)
    
    # Mostrar resumen del curso
    summary = course_report['course_summary']
    logger.info(f"\n📊 RESUMEN DEL CURSO:")
    logger.info(f"  Total de estudiantes: {summary['total_students']}")
    logger.info(f"  🔴 Alto riesgo: {summary['high_risk_count']}")
    logger.info(f"  🟡 Riesgo medio: {summary['medium_risk_count']}")
    logger.info(f"  🟢 Bajo riesgo: {summary['low_risk_count']}")
    
    # Mostrar recomendaciones
    if course_report.get('recommendations'):
        logger.info(f"\n💡 RECOMENDACIONES:")
        for rec in course_report['recommendations']:
            logger.info(f"  - {rec}")
    
    # Guardar informe del curso
    try:
        course_report_path = report_generator.generate_course_report(
            course_report,
            course_info.fullname
        )
        logger.info(f"\n📄 Informe del curso guardado: {course_report_path}")
    except Exception as e:
        logger.error(f"Error guardando informe del curso: {e}")
    
    logger.info("\n" + "="*60)
    logger.info("PROCESO COMPLETADO")
    logger.info("="*60 + "\n")

if __name__ == "__main__":
    main()