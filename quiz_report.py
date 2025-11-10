#!/usr/bin/env python
"""
Script para generar reportes de calificaciones de quizzes desde el caché.

Uso:
    python quiz_report.py                    # Reporte completo
    python quiz_report.py --course 10        # Reporte de un curso específico
    python quiz_report.py --export report.csv # Exportar a CSV
"""

import sys
import json
import csv
from datetime import datetime
from src.submission_cache import SubmissionCache

def generate_quiz_report(cache, course_id=None, format='console'):
    """
    Genera un reporte de las calificaciones de quizzes.
    
    Args:
        cache: Instancia de SubmissionCache
        course_id: ID del curso (opcional, None para todos)
        format: 'console' o 'csv'
    """
    # Obtener todas las entradas de tipo quiz
    all_entries = cache.get_all_entries(course_id=course_id)
    quiz_entries = [e for e in all_entries if e.get('assignment_type') == 'quiz']
    
    if not quiz_entries:
        print("\n❌ No se encontraron calificaciones de quizzes en el caché.")
        return
    
    # Organizar por curso y quiz
    by_course_quiz = {}
    for entry in quiz_entries:
        cid = entry.get('course_id')
        qid = entry.get('assignment_id')
        
        if cid not in by_course_quiz:
            by_course_quiz[cid] = {}
        
        if qid not in by_course_quiz[cid]:
            by_course_quiz[cid][qid] = {
                'name': entry.get('assignment_name', 'Quiz desconocido'),
                'students': []
            }
        
        by_course_quiz[cid][qid]['students'].append(entry)
    
    if format == 'console':
        _print_console_report(by_course_quiz)
    elif format == 'csv':
        return _generate_csv_data(by_course_quiz)

def _print_console_report(by_course_quiz):
    """Imprime el reporte en consola."""
    print(f"\n{'='*80}")
    print(f"  REPORTE DE CALIFICACIONES DE QUIZZES")
    print(f"{'='*80}\n")
    
    for course_id, quizzes in by_course_quiz.items():
        print(f"\n📚 Curso ID: {course_id}")
        print(f"{'='*80}")
        
        for quiz_id, quiz_data in quizzes.items():
            print(f"\n📝 {quiz_data['name']} (ID: {quiz_id})")
            print(f"{'-'*80}")
            
            students = sorted(quiz_data['students'], 
                            key=lambda x: x.get('student_username', ''))
            
            # Calcular estadísticas
            grades = []
            for student in students:
                grade = student.get('grade')
                max_grade = student.get('max_grade', 100)
                if grade is not None and max_grade:
                    percentage = (grade / max_grade) * 100
                    grades.append(percentage)
            
            # Mostrar estudiantes
            for student in students:
                username = student.get('student_username', f"ID:{student.get('student_id')}")
                grade = student.get('grade')
                max_grade = student.get('max_grade', 100)
                attempts = student.get('attempts', 0)
                
                if grade is not None:
                    percentage = (grade / max_grade) * 100 if max_grade > 0 else 0
                    status = "✅" if percentage >= 50 else "❌"
                    print(f"  {status} {username:20} | {grade:5.1f}/{max_grade:5.1f} ({percentage:5.1f}%) | {attempts} intento(s)")
            
            # Estadísticas del quiz
            if grades:
                avg_grade = sum(grades) / len(grades)
                max_g = max(grades)
                min_g = min(grades)
                passed = sum(1 for g in grades if g >= 50)
                
                print(f"\n  📊 Estadísticas:")
                print(f"     Promedio: {avg_grade:.1f}%")
                print(f"     Máxima: {max_g:.1f}%")
                print(f"     Mínima: {min_g:.1f}%")
                print(f"     Aprobados: {passed}/{len(grades)} ({(passed/len(grades)*100):.1f}%)")
            
            print()
    
    print(f"{'='*80}\n")

def _generate_csv_data(by_course_quiz):
    """Genera datos para exportar a CSV."""
    rows = []
    
    # Encabezados
    rows.append([
        'Curso ID', 'Quiz ID', 'Quiz Nombre', 'Estudiante ID', 
        'Estudiante Username', 'Calificación', 'Calificación Máxima', 
        'Porcentaje', 'Intentos', 'Estado', 'Última Actualización'
    ])
    
    for course_id, quizzes in by_course_quiz.items():
        for quiz_id, quiz_data in quizzes.items():
            for student in quiz_data['students']:
                grade = student.get('grade')
                max_grade = student.get('max_grade', 100)
                percentage = (grade / max_grade) * 100 if grade is not None and max_grade > 0 else 0
                status = "Aprobado" if percentage >= 50 else "Reprobado"
                
                rows.append([
                    course_id,
                    quiz_id,
                    quiz_data['name'],
                    student.get('student_id'),
                    student.get('student_username', ''),
                    grade if grade is not None else '',
                    max_grade,
                    f"{percentage:.2f}",
                    student.get('attempts', 0),
                    status,
                    student.get('last_updated', '')
                ])
    
    return rows

def export_to_csv(rows, filename):
    """Exporta los datos a un archivo CSV."""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    
    print(f"✅ Reporte exportado a: {filename}")
    print(f"   Total de filas: {len(rows) - 1}")  # -1 por el encabezado

def main():
    cache = SubmissionCache("submission_cache.json")
    
    # Parsear argumentos simples
    course_id = None
    export_file = None
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ['--course', '-c'] and i + 1 < len(sys.argv):
            course_id = int(sys.argv[i + 1])
            i += 2
        elif arg in ['--export', '-e'] and i + 1 < len(sys.argv):
            export_file = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    if export_file:
        csv_data = generate_quiz_report(cache, course_id, format='csv')
        if csv_data:
            export_to_csv(csv_data, export_file)
    else:
        generate_quiz_report(cache, course_id, format='console')

if __name__ == "__main__":
    main()
