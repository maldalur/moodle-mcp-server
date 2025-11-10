#!/usr/bin/env python
"""
Script de utilidad para gestionar el caché de entregas.

Uso:
    python cache_manager.py stats          # Ver estadísticas del caché
    python cache_manager.py list           # Listar todas las entregas
    python cache_manager.py clear          # Limpiar todo el caché
    python cache_manager.py remove <key>   # Eliminar una entrada específica
"""

import sys
import json
from src.submission_cache import SubmissionCache

def print_stats(cache):
    """Muestra estadísticas detalladas del caché."""
    stats = cache.get_stats()
    
    print(f"\n{'='*70}")
    print(f"  ESTADÍSTICAS DEL CACHÉ DE ENTREGAS")
    print(f"{'='*70}")
    print(f"\nTotal de entregas registradas: {stats['total_entries']}")
    
    if stats['by_status']:
        print(f"\n📊 Por estado:")
        for status, count in stats['by_status'].items():
            print(f"   - {status}: {count}")
    
    if stats['by_type']:
        print(f"\n📦 Por tipo de tarea:")
        for atype, count in stats['by_type'].items():
            print(f"   - {atype}: {count}")
    
    if stats['by_course']:
        print(f"\n📚 Por curso (ID):")
        for course_id, count in stats['by_course'].items():
            print(f"   - Curso {course_id}: {count} entregas")
    
    print(f"\n{'='*70}\n")

def list_entries(cache, course_id=None):
    """Lista todas las entregas del caché."""
    entries = cache.get_all_entries(course_id=course_id)
    
    if not entries:
        print("\n❌ No hay entregas en el caché.")
        return
    
    print(f"\n{'='*70}")
    print(f"  ENTREGAS EN CACHÉ ({len(entries)} total)")
    print(f"{'='*70}\n")
    
    # Agrupar por curso
    by_course = {}
    for entry in entries:
        cid = entry.get('course_id', 'unknown')
        if cid not in by_course:
            by_course[cid] = []
        by_course[cid].append(entry)
    
    for course_id, course_entries in by_course.items():
        print(f"\n📚 Curso ID: {course_id}")
        print(f"{'-'*70}")
        
        for entry in sorted(course_entries, key=lambda x: (x.get('assignment_name', ''), x.get('student_username', ''))):
            atype = entry.get('assignment_type', 'unknown')
            aname = entry.get('assignment_name', 'Sin nombre')
            student = entry.get('student_username', f"ID:{entry.get('student_id')}")
            status = entry.get('status', 'unknown')
            updated = entry.get('last_updated', 'N/A')[:19]  # Truncar a fecha/hora
            
            status_icon = "✓" if status == "processed" else "⚠"
            
            print(f"  {status_icon} [{atype:6}] {aname[:30]:30} | {student:15} | {updated}")
    
    print(f"\n{'='*70}\n")

def clear_cache(cache, confirm=True):
    """Limpia todo el caché."""
    if confirm:
        response = input("\n⚠️  ¿Estás seguro de que quieres limpiar TODO el caché? (sí/no): ")
        if response.lower() not in ['sí', 'si', 's', 'yes', 'y']:
            print("❌ Operación cancelada.")
            return
    
    cache.clear_cache()
    print("✅ Caché limpiado completamente.")

def remove_entry(cache, course_id, assignment_id, student_id, assignment_type):
    """Elimina una entrada específica del caché."""
    success = cache.remove_entry(course_id, assignment_id, student_id, assignment_type)
    if success:
        print(f"✅ Entrada eliminada: Curso {course_id}, Tarea {assignment_id}, Estudiante {student_id}, Tipo {assignment_type}")
    else:
        print(f"❌ No se encontró la entrada especificada.")

def export_cache(cache, output_file="cache_export.json"):
    """Exporta el caché completo a un archivo JSON."""
    entries = cache.get_all_entries()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Caché exportado a: {output_file}")
    print(f"   Total de entregas: {len(entries)}")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1].lower()
    cache = SubmissionCache("submission_cache.json")
    
    if command == "stats":
        print_stats(cache)
    
    elif command == "list" or command == "ls":
        course_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
        list_entries(cache, course_id)
    
    elif command == "clear":
        clear_cache(cache)
    
    elif command == "remove" or command == "rm":
        if len(sys.argv) < 6:
            print("❌ Uso: python cache_manager.py remove <course_id> <assignment_id> <student_id> <type>")
            print("   Ejemplo: python cache_manager.py remove 10 123 456 vpl")
            sys.exit(1)
        
        course_id = int(sys.argv[2])
        assignment_id = int(sys.argv[3])
        student_id = int(sys.argv[4])
        assignment_type = sys.argv[5]
        
        remove_entry(cache, course_id, assignment_id, student_id, assignment_type)
    
    elif command == "export":
        output_file = sys.argv[2] if len(sys.argv) > 2 else "cache_export.json"
        export_cache(cache, output_file)
    
    else:
        print(f"❌ Comando desconocido: {command}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()
