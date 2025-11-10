# Sistema de Caché de Entregas

## 📋 Descripción

El sistema de caché registra todas las entregas procesadas (VPL y asignaciones normales) y solo reprocesa aquellas que han cambiado desde la última ejecución.

## 🎯 Características

- ✅ **Detección automática de cambios**: Calcula un hash MD5 de cada entrega
- ✅ **Soporte múltiples tipos**: VPL y asignaciones normales (mod_assign)
- ✅ **Registro completo**: Guarda usuario, tarea, estado, timestamps
- ✅ **Estadísticas**: Muestra resumen de entregas procesadas
- ✅ **Utilidades CLI**: Herramientas para gestionar el caché

## 📁 Archivos

```
moodle_feedback/
├── src/
│   ├── submission_cache.py    # Módulo principal del caché
│   ├── main.py                 # Integración del caché
│   └── ...
├── cache_manager.py            # Herramienta CLI de gestión
└── submission_cache.json       # Archivo de caché (generado)
```

## 🚀 Uso Básico

### Primera ejecución
```powershell
python src\main.py
```

Salida esperada:
```
ESTADÍSTICAS DEL CACHÉ
==============================================================
Total de entregas en caché: 0
==============================================================

Processing Course: Mi Curso (ID: 10)

Encontradas 5 tareas de asignación en el curso
------------------------------------------------------------
ASIGNACIÓN: Tarea 1 (ID: 123)
------------------------------------------------------------
  ✓ alumno1 (ID: 456) - NUEVA o MODIFICADA
  ✓ alumno2 (ID: 457) - NUEVA o MODIFICADA
...

RESUMEN DE EJECUCIÓN
==============================================================
Entregas nuevas o modificadas: 25
Entregas sin cambios (omitidas): 0
Total procesadas: 25
==============================================================
```

### Segunda ejecución (sin cambios)
```powershell
python src\main.py
```

Salida esperada:
```
ESTADÍSTICAS DEL CACHÉ
==============================================================
Total de entregas en caché: 25
Por estado: {'processed': 25}
==============================================================

Processing Course: Mi Curso (ID: 10)

Encontradas 5 tareas de asignación en el curso
------------------------------------------------------------
ASIGNACIÓN: Tarea 1 (ID: 123)
------------------------------------------------------------
  ○ alumno1 (ID: 456) - SIN CAMBIOS (omitida)
  ○ alumno2 (ID: 457) - SIN CAMBIOS (omitida)
...

RESUMEN DE EJECUCIÓN
==============================================================
Entregas nuevas o modificadas: 0
Entregas sin cambios (omitidas): 25
Total procesadas: 25
==============================================================
```

### Cuando un estudiante modifica su entrega
```
  ✓ alumno1 (ID: 456) - NUEVA o MODIFICADA  ← Reprocesada
  ○ alumno2 (ID: 457) - SIN CAMBIOS (omitida)
```

## 🛠️ Herramienta CLI de Gestión

### Ver estadísticas
```powershell
python cache_manager.py stats
```

### Listar todas las entregas
```powershell
python cache_manager.py list
```

### Listar entregas de un curso específico
```powershell
python cache_manager.py list 10
```

### Exportar caché a JSON
```powershell
python cache_manager.py export mi_cache.json
```

### Generar reporte de quizzes
```powershell
# Reporte en consola
python quiz_report.py

# Reporte de un curso específico
python quiz_report.py --course 10

# Exportar a CSV
python quiz_report.py --export reporte_quizzes.csv
```

### Limpiar todo el caché
```powershell
python cache_manager.py clear
```

### Eliminar una entrada específica
```powershell
python cache_manager.py remove <course_id> <assignment_id> <student_id> <type>
# Ejemplo:
python cache_manager.py remove 10 123 456 vpl
```

## 📊 Estructura del Caché

El archivo `submission_cache.json` tiene esta estructura:

```json
{
  "vpl_10_123_456": {
    "course_id": 10,
    "assignment_id": 123,
    "student_id": 456,
    "student_username": "alumno1",
    "assignment_name": "Práctica 1",
    "assignment_type": "vpl",
    "hash": "a1b2c3d4e5f6...",
    "status": "processed",
    "last_updated": "2025-11-07T14:30:00",
    "first_seen": "2025-11-01T10:00:00"
  },
  "assign_10_124_456": {
    "course_id": 10,
    "assignment_id": 124,
    "student_id": 456,
    "student_username": "alumno1",
    "assignment_name": "Ensayo Final",
    "assignment_type": "assign",
    "hash": "f6e5d4c3b2a1...",
    "status": "processed",
    "last_updated": "2025-11-07T14:35:00",
    "first_seen": "2025-11-05T09:15:00",
    "files_downloaded": 2
  }
}
```

## 🔍 Cómo Funciona

1. **Cálculo del hash**: Se calcula un MD5 de los datos de la entrega
2. **Comparación**: Se compara con el hash guardado en caché
3. **Detección de cambios**: 
   - Hash diferente → Entrega modificada → Reprocesar
   - Hash igual → Sin cambios → Omitir
   - No existe en caché → Nueva entrega → Procesar

## ⚙️ Configuración Avanzada

### Cambiar ubicación del archivo de caché

En `main.py`:
```python
cache = SubmissionCache("mi_cache_personalizado.json")
```

### Añadir información adicional al caché

```python
cache.update(
    course_id=course_info.course_id,
    assignment_id=assignment["id"],
    student_id=user["id"],
    submission_data=submission,
    assignment_type="vpl",
    student_username=user["username"],
    assignment_name=vpl["name"],
    status="processed",
    additional_info={
        "grade": 8.5,
        "feedback": "Excelente trabajo",
        "files_count": 3
    }
)
```

## 🐛 Solución de Problemas

### El caché no detecta cambios
- Verifica que `submission_data` sea consistente entre ejecuciones
- El orden de los datos no importa (el hash se calcula con claves ordenadas)

### Limpiar caché corrupto
```powershell
del submission_cache.json
python src\main.py
```

### Ver qué hay en el caché
```powershell
python cache_manager.py list
```

## 📝 Notas

- El caché persiste entre ejecuciones
- Los hashes MD5 son suficientemente únicos para detectar cambios
- El archivo JSON es legible y editable manualmente si es necesario
- El sistema es compatible con ambos tipos de tareas (VPL y asignaciones)

## 🎓 Casos de Uso

1. **Corrección incremental**: Solo corregir entregas nuevas o modificadas
2. **Auditoría**: Registro de cuándo se procesó cada entrega
3. **Reporte de progreso**: Ver qué estudiantes han entregado y cuándo
4. **Optimización**: Evitar descargas y procesamiento innecesarios
