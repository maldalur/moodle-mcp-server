"""
Generador de informes en formato Markdown
"""
from datetime import datetime
from typing import List, Dict, Any
import os

class ReportGenerator:
    """Genera informes legibles en formato Markdown"""
    
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_student_report(self, 
                               student_report: Dict[str, Any],
                               submissions_detail: List[Dict[str, Any]]) -> str:
        """
        Genera un informe individual de estudiante
        
        Returns:
            Ruta del archivo generado
        """
        student_name = student_report['student_name']
        student_id = student_report['student_id']
        
        # Crear contenido del informe
        content = f"""# Informe de Estudiante: {student_name}

**ID:** {student_id}  
**Generado:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 Resumen

### Nivel de Riesgo: {self._format_risk_level(student_report['risk_level'])}

"""
        
        # Razones de riesgo
        if student_report.get('risk_reasons'):
            content += "**Razones:**\n"
            for reason in student_report['risk_reasons']:
                content += f"- {reason}\n"
            content += "\n"
        
        # Estadísticas
        stats = student_report.get('statistics', {})
        content += f"""### Estadísticas
- **Total de entregas:** {stats.get('total_submissions', 0)}
- **A tiempo:** {stats.get('on_time', 0)}
- **Tardías:** {stats.get('late', 0)}
- **Días desde última entrega:** {stats.get('days_since_last_submission', 'N/A')}

"""
        
        # Progreso
        progress = student_report.get('progress', {})
        if progress:
            content += f"""### 📈 Progreso
- **Tendencia:** {self._format_trend(progress.get('trend', 'unknown'))}
- **Descripción:** {progress.get('description', 'N/A')}
- **Calificación promedio:** {progress.get('average_grade', 'N/A')}

"""
        
        # Detalle de entregas
        content += """---

## 📝 Detalle de Entregas

"""
        
        for i, submission in enumerate(submissions_detail, 1):
            content += f"""### {i}. {submission.get('assignment_name', 'Sin nombre')}

- **Estado:** {submission.get('status', 'N/A')}
- **Última modificación:** {self._format_date(submission.get('timemodified'))}
"""
            
            # Análisis de IA si existe
            ai_analysis = submission.get('ai_analysis', {})
            if ai_analysis and ai_analysis.get('status') == 'success':
                content += f"""
#### 🤖 Análisis con IA

**Calificación sugerida:** {ai_analysis.get('suggested_grade', 'N/A')}/10

**Feedback:**
{ai_analysis.get('ai_feedback', 'No disponible')}

**Fortalezas:**
"""
                for strength in ai_analysis.get('strengths', []):
                    content += f"- ✅ {strength}\n"
                
                content += "\n**Áreas de mejora:**\n"
                for weakness in ai_analysis.get('weaknesses', []):
                    content += f"- ⚠️ {weakness}\n"
                
                content += "\n**Recomendaciones:**\n"
                for rec in ai_analysis.get('recommendations', []):
                    content += f"- 💡 {rec}\n"
                
                # URLs analizadas
                if ai_analysis.get('url_analysis'):
                    content += "\n**Enlaces encontrados:**\n"
                    for url_data in ai_analysis.get('url_analysis', []):
                        status = "✅" if url_data.get('accessible') else "❌"
                        content += f"- {status} {url_data['url']}\n"
            
            content += "\n---\n\n"
        
        # Guardar archivo
        filename = f"student_{student_id}_{student_name}.md"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath
    
    def generate_course_report(self, course_report: Dict[str, Any], course_name: str) -> str:
        """
        Genera un informe general del curso
        
        Returns:
            Ruta del archivo generado
        """
        content = f"""# Informe del Curso: {course_name}

**Generado:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 Resumen General

"""
        
        summary = course_report.get('course_summary', {})
        content += f"""- **Total de estudiantes:** {summary.get('total_students', 0)}
- **🔴 Alto riesgo:** {summary.get('high_risk_count', 0)}
- **🟡 Riesgo medio:** {summary.get('medium_risk_count', 0)}
- **🟢 Bajo riesgo:** {summary.get('low_risk_count', 0)}

"""
        
        # Recomendaciones
        recommendations = course_report.get('recommendations', [])
        if recommendations:
            content += "## 💡 Recomendaciones\n\n"
            for rec in recommendations:
                content += f"- {rec}\n"
            content += "\n"
        
        # Estudiantes en alto riesgo
        high_risk = course_report.get('students_at_risk', {}).get('high', [])
        if high_risk:
            content += """---

## 🔴 Estudiantes en Alto Riesgo

| Estudiante | ID | Razones |
|------------|-------|---------|
"""
            for student in high_risk:
                reasons = '; '.join(student.get('risk_reasons', []))
                content += f"| {student['student_name']} | {student['student_id']} | {reasons} |\n"
            content += "\n"
        
        # Estudiantes en riesgo medio
        medium_risk = course_report.get('students_at_risk', {}).get('medium', [])
        if medium_risk:
            content += """---

## 🟡 Estudiantes en Riesgo Medio

| Estudiante | ID | Razones |
|------------|-------|---------|
"""
            for student in medium_risk:
                reasons = '; '.join(student.get('risk_reasons', []))
                content += f"| {student['student_name']} | {student['student_id']} | {reasons} |\n"
            content += "\n"
        
        # Guardar archivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"course_report_{timestamp}.md"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath
    
    def _format_risk_level(self, level: str) -> str:
        """Formatea el nivel de riesgo con emoji"""
        levels = {
            'high': '🔴 ALTO',
            'medium': '🟡 MEDIO',
            'low': '🟢 BAJO'
        }
        return levels.get(level, level.upper())
    
    def _format_trend(self, trend: str) -> str:
        """Formatea la tendencia con emoji"""
        trends = {
            'improving': '📈 Mejorando',
            'declining': '📉 Declinando',
            'stable': '➡️ Estable',
            'insufficient_data': '❓ Datos insuficientes',
            'unknown': '❓ Desconocido'
        }
        return trends.get(trend, trend)
    
    def _format_date(self, timestamp: Any) -> str:
        """Formatea una fecha/timestamp"""
        try:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif isinstance(timestamp, (int, float)):
                dt = datetime.fromtimestamp(timestamp)
            else:
                return 'N/A'
            return dt.strftime('%Y-%m-%d %H:%M')
        except:
            return 'N/A'
