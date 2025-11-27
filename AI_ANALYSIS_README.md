# Sistema de Análisis y Calificación Automática con IA

Este sistema analiza automáticamente las entregas de estudiantes, genera feedback detallado e identifica estudiantes en riesgo.

## 🌟 Nuevas Funcionalidades

### 1. **Análisis Automático con IA**
- Analiza el contenido de todas las entregas (archivos de texto, código, documentos)
- Extrae y verifica enlaces incluidos en las entregas
- Genera calificación sugerida basada en criterios de evaluación
- Proporciona feedback constructivo personalizado

### 2. **Detección de Estudiantes en Riesgo**
El sistema evalúa automáticamente a cada estudiante y los clasifica en tres niveles:

- **🔴 Alto Riesgo**: Estudiantes que necesitan atención inmediata
  - Sin entregas o muy pocas entregas
  - >50% de entregas tardías
  - >14 días sin actividad
  - Calificaciones promedio < 5

- **🟡 Riesgo Medio**: Estudiantes que requieren seguimiento
  - Pocas entregas (< 3)
  - >50% entregas tardías
  - 7-14 días sin actividad
  - Calificaciones promedio 5-6

- **🟢 Bajo Riesgo**: Estudiantes con buen desempeño
  - Entregas regulares y a tiempo
  - Calificaciones satisfactorias

### 3. **Análisis de Progreso**
- Evalúa tendencias: Mejorando 📈, Declinando 📉, Estable ➡️
- Calcula promedios de calificación
- Identifica patrones de entrega

### 4. **Análisis de Enlaces (URLs)**
- Extrae automáticamente URLs del contenido
- Verifica accesibilidad de cada enlace
- Reporta enlaces rotos o inaccesibles

### 5. **Informes Detallados**
Se generan dos tipos de informes en formato Markdown:

#### Informes Individuales (`reports/student_[ID]_[nombre].md`)
- Nivel de riesgo y razones
- Estadísticas de entregas
- Análisis de progreso
- Feedback detallado de cada tarea
- Calificaciones sugeridas
- Fortalezas y áreas de mejora
- Enlaces encontrados y su estado

#### Informe del Curso (`reports/course_report_[timestamp].md`)
- Resumen general del curso
- Conteo por nivel de riesgo
- Lista de estudiantes en riesgo alto/medio
- Recomendaciones a nivel curso

### 6. **Tracking de Modificaciones**
- Registra cuándo se modificó cada entrega por última vez
- Calcula días desde la última actividad
- Identifica estudiantes inactivos

## 📋 Requisitos

```bash
pip install requests python-dotenv ollama
```

**Importante**: Debes tener [Ollama](https://ollama.ai/) instalado y ejecutándose:

```bash
# Instalar modelo
ollama pull llama3.2

# Verificar que está ejecutándose
ollama list
```

## 🚀 Uso

### Ejecución Normal
```bash
python src/main.py
```

El sistema automáticamente:
1. Descarga todas las entregas nuevas o modificadas
2. Analiza cada entrega con IA
3. Genera informes de estudiantes en riesgo
4. Crea un informe general del curso

### Prueba del Analizador de IA
```bash
python src/test_ai_analyzer.py
```

Esto prueba el sistema de análisis sin conectarse a Moodle.

### Prueba de Quizzes
```bash
python src/test_quiz.py
```

## 📊 Salida del Sistema

### Consola
```
============================================================
PRUEBA DE ANÁLISIS CON IA
============================================================
Processing Course: Programación (DAM/DAW) (ID: 130)

------------------------------------------------------------
ASIGNACIÓN: Tarea 1 - Programa Hola Mundo (ID: 123)
------------------------------------------------------------
  ✓ student_123 (ID: 123) - NUEVA o MODIFICADA
      - downloads/assign_123/student_123/hello.py
      Analizando con IA...
      📊 Calificación sugerida: 8.5/10
      💬 URLs encontradas: 2

...

============================================================
GENERANDO INFORMES DE ANÁLISIS
============================================================

Generando informe para: student_123
  🔴 Nivel de riesgo: HIGH
    - Solo 2 entrega(s)
    - 14 días sin entregar
  📄 Informe guardado: reports/student_123_student_123.md

------------------------------------------------------------
Generando informe general del curso...
------------------------------------------------------------

📊 RESUMEN DEL CURSO:
  Total de estudiantes: 118
  🔴 Alto riesgo: 12
  🟡 Riesgo medio: 25
  🟢 Bajo riesgo: 81

💡 RECOMENDACIONES:
  - URGENTE: 12 estudiante(s) en alto riesgo necesitan atención inmediata
  - ATENCIÓN: 25 estudiante(s) en riesgo medio requieren seguimiento

📄 Informe del curso guardado: reports/course_report_20251110_143022.md
```

### Archivos Generados

```
reports/
├── student_123_student_name.md      # Estudiantes en riesgo alto/medio
├── student_456_otro_student.md
├── ...
└── course_report_20251110_143022.md # Informe general del curso
```

## ⚙️ Configuración

### Variables de Entorno (.env)
```env
MOODLE_URL=https://tu-moodle.com
TOKEN_MOODLE=tu_token_aqui
COURSE_LIST=130,131,132
```

### Modelo de IA
Puedes cambiar el modelo en `src/main.py`:
```python
ai_analyzer = AIAnalyzer(model="llama3.2")  # o "llama2", "mistral", etc.
```

## 🎯 Criterios de Evaluación

El sistema considera los criterios de evaluación definidos en cada tarea de Moodle (campo `intro`). Evalúa:

1. **Cumplimiento de requisitos**: Si el trabajo cumple con lo solicitado
2. **Calidad del código**: Si aplica (sintaxis, estructura, buenas prácticas)
3. **Documentación**: Comentarios, explicaciones, claridad
4. **Recursos**: Enlaces a documentación, referencias relevantes
5. **Originalidad**: Detecta si es trabajo original del estudiante

## 🔍 Análisis de Enlaces

Para cada URL encontrada en las entregas, el sistema:
- Verifica si es accesible (HTTP status < 400)
- Identifica el tipo de contenido
- Reporta enlaces rotos
- Evalúa relevancia del recurso

Ejemplo de salida:
```markdown
**Enlaces encontrados:**
- ✅ https://www.python.org/ (accesible)
- ❌ https://ejemplo-roto.com (error: timeout)
```

## 📈 Métricas de Riesgo

El sistema calcula un "puntaje de riesgo" basado en:

| Factor | Puntos | Condición |
|--------|--------|-----------|
| Sin entregas | +10 | 0 entregas |
| Pocas entregas | +5 | < 3 entregas |
| Entregas tardías | +5 | >50% tarde |
| Inactividad crítica | +7 | >14 días |
| Inactividad moderada | +3 | >7 días |
| Calificaciones bajas | +5 | Promedio < 5 |
| Calificaciones medias | +2 | Promedio < 6 |

- **≥10 puntos**: 🔴 Alto riesgo
- **5-9 puntos**: 🟡 Riesgo medio
- **<5 puntos**: 🟢 Bajo riesgo

## 🛠️ Troubleshooting

### Error: "ModuleNotFoundError: No module named 'ollama'"
```bash
pip install ollama
```

### Error: "Ollama not running"
```bash
# Iniciar Ollama
ollama serve

# En otra terminal, verificar
ollama list
```

### Análisis muy lento
- Reduce el número de URLs analizadas (línea 131 en `ai_analyzer.py`)
- Usa un modelo más rápido: `llama3.2` en lugar de modelos más grandes
- Limita el contenido analizado (ya limitado a 4000 caracteres por defecto)

### Sin informes generados
- Verifica que hay entregas nuevas o modificadas
- Los informes solo se generan para estudiantes en riesgo alto/medio
- El informe del curso siempre se genera

## 📝 Notas

- El análisis con IA puede tardar unos segundos por entrega
- Solo se analizan archivos de texto (código, md, txt, etc.)
- Los archivos binarios se registran pero no se analizan
- El sistema respeta el caché: solo analiza entregas nuevas o modificadas
- Los informes se sobrescriben si se regeneran para el mismo estudiante

## 🔮 Futuras Mejoras

- [ ] Análisis de documentos PDF
- [ ] Detección de plagio
- [ ] Recomendaciones personalizadas por estudiante
- [ ] Integración con calendario académico
- [ ] Dashboard web interactivo
- [ ] Notificaciones automáticas por email
- [ ] Análisis de sentimiento en comentarios
- [ ] Predicción de riesgo de abandono
