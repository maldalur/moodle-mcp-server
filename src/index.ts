#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} from '@modelcontextprotocol/sdk/types.js';
import axios from 'axios';

// Configuración de variables de entorno
const MOODLE_API_URL = process.env.MOODLE_API_URL;
const MOODLE_API_TOKEN = process.env.MOODLE_API_TOKEN;
const MOODLE_COURSE_ID = process.env.MOODLE_COURSE_ID;

// Verificar que las variables de entorno estén definidas
if (!MOODLE_API_URL) {
  throw new Error('MOODLE_API_URL environment variable is required');
}

if (!MOODLE_API_TOKEN) {
  throw new Error('MOODLE_API_TOKEN environment variable is required');
}

// MOODLE_COURSE_ID es opcional ahora - algunas herramientas lo requieren como parámetro
// if (!MOODLE_COURSE_ID) {
//   throw new Error('MOODLE_COURSE_ID environment variable is required');
// }

// Interfaces para los tipos de datos
interface Student {
  id: number;
  username: string;
  firstname: string;
  lastname: string;
  email: string;
}

interface Assignment {
  id: number;
  name: string;
  duedate: number;
  allowsubmissionsfromdate: number;
  grade: number;
  timemodified: number;
  cutoffdate: number;
}

interface Quiz {
  id: number;
  name: string;
  timeopen: number;
  timeclose: number;
  grade: number;
  timemodified: number;
}

interface Submission {
  id: number;
  userid: number;
  status: string;
  timemodified: number;
  gradingstatus: string;
  gradefordisplay?: string;
}

interface SubmissionContent {
  assignment: number;
  userid: number;
  status: string;
  submissiontext?: string;
  plugins?: Array<{
    type: string;
    content?: string;
    files?: Array<{
      filename: string;
      fileurl: string;
      filesize: number;
      filetype: string;
    }>;
  }>;
  timemodified: number;
}

interface QuizGradeResponse {
  hasgrade: boolean;
  grade?: string;  // Este campo solo está presente si hasgrade es true
}

class MoodleMcpServer {
  private server: Server;
  private axiosInstance;

  constructor() {
    this.server = new Server(
      {
        name: 'moodle-mcp-server',
        version: '0.1.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.axiosInstance = axios.create({
      baseURL: MOODLE_API_URL,
      params: {
        wstoken: MOODLE_API_TOKEN,
        moodlewsrestformat: 'json',
      },
    });

    this.setupToolHandlers();
    
    // Error handling
    this.server.onerror = (error) => console.error('[MCP Error]', error);
    process.on('SIGINT', async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  private setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'search_courses',
          description: 'Busca cursos por nombre. Permite al LLM encontrar el ID del curso que necesita buscar',
          inputSchema: {
            type: 'object',
            properties: {
              courseName: {
                type: 'string',
                description: 'Nombre o parte del nombre del curso a buscar',
              },
            },
            required: ['courseName'],
          },
        },
        {
          name: 'get_students',
          description: 'Obtiene la lista de estudiantes inscritos en un curso. Puedes proporcionar el nombre del curso o su ID',
          inputSchema: {
            type: 'object',
            properties: {
              courseId: {
                type: 'number',
                description: 'ID del curso. Si no se proporciona, se usa MOODLE_COURSE_ID del entorno',
              },
              courseName: {
                type: 'string',
                description: 'Nombre del curso. Si se proporciona, se buscará automáticamente el ID del curso',
              },
            },
            required: [],
          },
        },
        {
          name: 'get_assignments',
          description: 'Obtiene la lista de tareas asignadas en un curso. Puedes proporcionar el nombre del curso o su ID',
          inputSchema: {
            type: 'object',
            properties: {
              courseId: {
                type: 'number',
                description: 'ID del curso. Si no se proporciona, se usa MOODLE_COURSE_ID del entorno',
              },
              courseName: {
                type: 'string',
                description: 'Nombre del curso. Si se proporciona, se buscará automáticamente el ID del curso',
              },
            },
            required: [],
          },
        },
        {
          name: 'get_quizzes',
          description: 'Obtiene la lista de quizzes en un curso. Puedes proporcionar el nombre del curso o su ID',
          inputSchema: {
            type: 'object',
            properties: {
              courseId: {
                type: 'number',
                description: 'ID del curso. Si no se proporciona, se usa MOODLE_COURSE_ID del entorno',
              },
              courseName: {
                type: 'string',
                description: 'Nombre del curso. Si se proporciona, se buscará automáticamente el ID del curso',
              },
            },
            required: [],
          },
        },
        {
          name: 'get_vpl_assignments',
          description: 'Obtiene la lista de tareas VPL (Virtual Programming Lab) en un curso. Puedes proporcionar el nombre del curso o su ID',
          inputSchema: {
            type: 'object',
            properties: {
              courseId: {
                type: 'number',
                description: 'ID del curso. Si no se proporciona, se usa MOODLE_COURSE_ID del entorno',
              },
              courseName: {
                type: 'string',
                description: 'Nombre del curso. Si se proporciona, se buscará automáticamente el ID del curso',
              },
            },
            required: [],
          },
        },
        {
          name: 'get_submissions',
          description: 'Obtiene las entregas de tareas en el curso configurado',
          inputSchema: {
            type: 'object',
            properties: {
              studentId: {
                type: 'number',
                description: 'ID opcional del estudiante. Si no se proporciona, se devolverán entregas de todos los estudiantes',
              },
              assignmentId: {
                type: 'number',
                description: 'ID opcional de la tarea. Si no se proporciona, se devolverán todas las entregas',
              },
            },
            required: [],
          },
        },
        {
          name: 'get_vpl_submission',
          description: 'Obtiene la entrega de un estudiante en una tarea VPL específica',
          inputSchema: {
            type: 'object',
            properties: {
              vplId: {
                type: 'number',
                description: 'ID de la tarea VPL',
              },
              studentId: {
                type: 'number',
                description: 'ID del estudiante',
              },
              cmId: {
                type: 'number',
                description: 'ID del módulo del curso (opcional, pero recomendado)',
              },
            },
            required: ['vplId', 'studentId'],
          },
        },
        {
          name: 'provide_feedback',
          description: 'Proporciona feedback sobre una tarea entregada por un estudiante',
          inputSchema: {
            type: 'object',
            properties: {
              studentId: {
                type: 'number',
                description: 'ID del estudiante',
              },
              assignmentId: {
                type: 'number',
                description: 'ID de la tarea',
              },
              grade: {
                type: 'number',
                description: 'Calificación numérica a asignar',
              },
              feedback: {
                type: 'string',
                description: 'Texto del feedback a proporcionar',
              },
            },
            required: ['studentId', 'assignmentId', 'feedback'],
          },
        },
        {
          name: 'get_submission_content',
          description: 'Obtiene el contenido detallado de una entrega específica, incluyendo texto y archivos adjuntos',
          inputSchema: {
            type: 'object',
            properties: {
              studentId: {
                type: 'number',
                description: 'ID del estudiante',
              },
              assignmentId: {
                type: 'number',
                description: 'ID de la tarea',
              },
            },
            required: ['studentId', 'assignmentId'],
          },
        },
        {
          name: 'get_quiz_grade',
          description: 'Obtiene la calificación de un estudiante en un quiz específico',
          inputSchema: {
            type: 'object',
            properties: {
              studentId: {
                type: 'number',
                description: 'ID del estudiante',
              },
              quizId: {
                type: 'number',
                description: 'ID del quiz',
              },
            },
            required: ['studentId', 'quizId'],
          },
        },
        {
          name: 'get_forums',
          description: 'Obtiene la lista de foros en un curso. Puedes proporcionar el nombre del curso o su ID',
          inputSchema: {
            type: 'object',
            properties: {
              courseId: {
                type: 'number',
                description: 'ID del curso. Si no se proporciona, se usa MOODLE_COURSE_ID del entorno',
              },
              courseName: {
                type: 'string',
                description: 'Nombre del curso. Si se proporciona, se buscará automáticamente el ID del curso',
              },
            },
            required: [],
          },
        },
        {
          name: 'get_forum_discussions',
          description: 'Obtiene las discusiones de un foro específico',
          inputSchema: {
            type: 'object',
            properties: {
              forumId: {
                type: 'number',
                description: 'ID del foro',
              },
            },
            required: ['forumId'],
          },
        },
      ],
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      console.error(`[Tool] Executing tool: ${request.params.name}`);

      try {
        switch (request.params.name) {
          case 'search_courses':
            return await this.searchCourses(request.params.arguments);
          case 'get_students':
            return await this.getStudents(request.params.arguments);
          case 'get_assignments':
            return await this.getAssignments(request.params.arguments);
          case 'get_quizzes':
            return await this.getQuizzes(request.params.arguments);
          case 'get_vpl_assignments':
            return await this.getVplAssignments(request.params.arguments);
          case 'get_submissions':
            return await this.getSubmissions(request.params.arguments);
          case 'get_vpl_submission':
            return await this.getVplSubmission(request.params.arguments);
          case 'provide_feedback':
            return await this.provideFeedback(request.params.arguments);
          case 'get_submission_content':
            return await this.getSubmissionContent(request.params.arguments);
          case 'get_quiz_grade':
            return await this.getQuizGrade(request.params.arguments);
          case 'get_forums':
            return await this.getForums(request.params.arguments);
          case 'get_forum_discussions':
            return await this.getForumDiscussions(request.params.arguments);
          default:
            throw new McpError(
              ErrorCode.MethodNotFound,
              `Unknown tool: ${request.params.name}`
            );
        }
      } catch (error) {
        console.error('[Error]', error);
        if (axios.isAxiosError(error)) {
          return {
            content: [
              {
                type: 'text',
                text: `Moodle API error: ${
                  error.response?.data?.message || error.message
                }`,
              },
            ],
            isError: true,
          };
        }
        throw error;
      }
    });
  }

  // Función auxiliar para normalizar texto (quitar acentos)
  private normalizeText(text: string): string {
    return text
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '');
  }

  // Función auxiliar para resolver el courseId a partir del nombre o ID
  private async resolveCourseId(args: any): Promise<number> {
    // Si ya tenemos courseId, lo retornamos
    if (args?.courseId) {
      return args.courseId;
    }

    // Si tenemos courseName, buscamos el curso
    if (args?.courseName) {
      console.error(`[Helper] Resolving courseId from courseName: ${args.courseName}`);
      
      try {
        // Reutilizamos la lógica de searchCourses
        const response = await this.axiosInstance.get('', {
          params: {
            wsfunction: 'core_course_search_courses',
            criterianame: 'search',
            criteriavalue: args.courseName,
          },
        });

        let courses = response.data.courses || [];
        
        // Si no hay resultados, intentar búsqueda flexible
        if (courses.length === 0) {
          console.error(`[Helper] No exact match, trying flexible search...`);
          const allCoursesResponse = await this.axiosInstance.get('', {
            params: {
              wsfunction: 'core_course_get_courses',
            },
          });
          
          const allCourses = allCoursesResponse.data;
          const normalizedSearchTerm = this.normalizeText(args.courseName);
          
          courses = allCourses.filter((course: any) => {
            const normalizedFullname = this.normalizeText(course.fullname || '');
            const normalizedShortname = this.normalizeText(course.shortname || '');
            return normalizedFullname.includes(normalizedSearchTerm) ||
                   normalizedShortname.includes(normalizedSearchTerm);
          });
        }
        
        if (courses.length === 0) {
          throw new McpError(
            ErrorCode.InvalidParams,
            `No se encontró ningún curso con el nombre: ${args.courseName}`
          );
        }
        
        if (courses.length > 1) {
          console.error(`[Helper] Multiple courses found (${courses.length}), using first one: ${courses[0].fullname}`);
        }
        
        const resolvedId = courses[0].id;
        console.error(`[Helper] Resolved courseId: ${resolvedId} (${courses[0].fullname})`);
        return resolvedId;
      } catch (error) {
        console.error('[Helper] Error resolving courseId:', error);
        throw error;
      }
    }

    // Si no tenemos ni courseId ni courseName, usamos el de entorno
    if (MOODLE_COURSE_ID) {
      return parseInt(MOODLE_COURSE_ID);
    }

    throw new McpError(
      ErrorCode.InvalidParams,
      'Se requiere courseId, courseName, o MOODLE_COURSE_ID en el entorno'
    );
  }

  private async searchCourses(args: any) {
    const courseName = args?.courseName;
    
    if (!courseName) {
      throw new McpError(
        ErrorCode.InvalidParams,
        'courseName is required'
      );
    }
    
    console.error(`[API] Searching courses with name: ${courseName}`);
    
    try {
      // Primero intentar búsqueda exacta con la API de Moodle
      const response = await this.axiosInstance.get('', {
        params: {
          wsfunction: 'core_course_search_courses',
          criterianame: 'search',
          criteriavalue: courseName,
        },
      });

      const searchResults = response.data;
      let courses = searchResults.courses || [];
      
      // Si no hay resultados y el nombre tiene caracteres especiales,
      // intentar búsqueda flexible obteniendo todos los cursos y filtrando
      if (courses.length === 0) {
        console.error(`[API] No results found, trying flexible search...`);
        const allCoursesResponse = await this.axiosInstance.get('', {
          params: {
            wsfunction: 'core_course_get_courses',
          },
        });
        
        const allCourses = allCoursesResponse.data;
        const normalizedSearchTerm = this.normalizeText(courseName);
        
        // Filtrar cursos por similitud (sin acentos)
        courses = allCourses.filter((course: any) => {
          const normalizedFullname = this.normalizeText(course.fullname || '');
          const normalizedShortname = this.normalizeText(course.shortname || '');
          return normalizedFullname.includes(normalizedSearchTerm) ||
                 normalizedShortname.includes(normalizedSearchTerm);
        });
        
        console.error(`[API] Flexible search found ${courses.length} courses`);
      }
      
      // Mapear a formato simplificado con ID y nombre
      const matchingCourses = courses.map((course: any) => ({
        id: course.id,
        fullname: course.fullname,
        shortname: course.shortname,
        categoryid: course.categoryid,
        categoryname: course.categoryname,
        visible: course.visible,
        startdate: course.startdate,
        enddate: course.enddate,
      }));

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              searchTerm: courseName,
              totalFound: matchingCourses.length,
              courses: matchingCourses,
            }, null, 2),
          },
        ],
      };
    } catch (error) {
      console.error('[Error] Failed to search courses:', error);
      throw error;
    }
  }

  private async getStudents(args?: any) {
    // Resolver courseId automáticamente desde courseName si es necesario
    const courseId = await this.resolveCourseId(args);
    
    console.error(`[API] Requesting enrolled users for course: ${courseId}`);
    
    const response = await this.axiosInstance.get('', {
      params: {
        wsfunction: 'core_enrol_get_enrolled_users',
        courseid: courseId,
      },
    });

    const students = response.data
      .filter((user: any) => user.roles.some((role: any) => role.shortname === 'student'))
      .map((student: any) => ({
        id: student.id,
        username: student.username,
        firstname: student.firstname,
        lastname: student.lastname,
        email: student.email,
      }));

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(students, null, 2),
        },
      ],
    };
  }

  private async getAssignments(args?: any) {
    // Resolver courseId automáticamente desde courseName si es necesario
    const courseId = await this.resolveCourseId(args);
    
    console.error(`[API] Requesting assignments for course: ${courseId}`);
    
    const response = await this.axiosInstance.get('', {
      params: {
        wsfunction: 'mod_assign_get_assignments',
        courseids: [courseId],
      },
    });

    const assignments = response.data.courses[0]?.assignments || [];
    
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(assignments, null, 2),
        },
      ],
    };
  }

  private async getQuizzes(args?: any) {
    // Resolver courseId automáticamente desde courseName si es necesario
    const courseId = await this.resolveCourseId(args);
    
    console.error(`[API] Requesting quizzes for course: ${courseId}`);
    
    const response = await this.axiosInstance.get('', {
      params: {
        wsfunction: 'mod_quiz_get_quizzes_by_courses',
        courseids: [courseId],
      },
    });

    const quizzes = response.data.quizzes || [];
    
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(quizzes, null, 2),
        },
      ],
    };
  }

  private async getSubmissions(args: any) {
    const studentId = args.studentId;
    const assignmentId = args.assignmentId;
    
    console.error(`[API] Requesting submissions${studentId ? ` for student ${studentId}` : ''}`);
    
    try {
      // Primero obtenemos todas las tareas
      const assignmentsResponse = await this.axiosInstance.get('', {
        params: {
          wsfunction: 'mod_assign_get_assignments',
          courseids: [MOODLE_COURSE_ID],
        },
      });

      // Validación de respuesta
      if (!assignmentsResponse.data || !assignmentsResponse.data.courses || !Array.isArray(assignmentsResponse.data.courses)) {
        console.error('[API] Invalid assignments response structure:', assignmentsResponse.data);
        return {
          content: [
            {
              type: 'text',
              text: 'Error: Respuesta inválida de la API de Moodle al obtener tareas.',
            },
          ],
          isError: true,
        };
      }

      const assignments = assignmentsResponse.data.courses[0]?.assignments || [];
      
      // Si se especificó un ID de tarea, filtramos solo esa tarea
      const targetAssignments = assignmentId
        ? assignments.filter((a: any) => a.id === assignmentId)
        : assignments;
      
      if (targetAssignments.length === 0) {
        return {
          content: [
            {
              type: 'text',
              text: 'No se encontraron tareas para el criterio especificado.',
            },
          ],
        };
      }

      // Para cada tarea, obtenemos todas las entregas
      const submissionsPromises = targetAssignments.map(async (assignment: any) => {
        try {
          const submissionsResponse = await this.axiosInstance.get('', {
            params: {
              wsfunction: 'mod_assign_get_submissions',
              assignmentids: [assignment.id],
            },
          });

          // Validación de respuesta de submissions
          const submissions = submissionsResponse.data?.assignments?.[0]?.submissions || [];
          
          // Obtenemos las calificaciones para esta tarea
          const gradesResponse = await this.axiosInstance.get('', {
            params: {
              wsfunction: 'mod_assign_get_grades',
              assignmentids: [assignment.id],
            },
          });

          // Validación de respuesta de grades
          const grades = gradesResponse.data?.assignments?.[0]?.grades || [];
          
          // Si se especificó un ID de estudiante, filtramos solo sus entregas
          const targetSubmissions = studentId
            ? submissions.filter((s: any) => s.userid === studentId)
            : submissions;
          
          // Procesamos cada entrega
          const processedSubmissions = targetSubmissions.map((submission: any) => {
            const studentGrade = grades.find((g: any) => g.userid === submission.userid);
            
            return {
              userid: submission.userid,
              status: submission.status,
              timemodified: submission.timemodified ? new Date(submission.timemodified * 1000).toISOString() : 'N/A',
              grade: studentGrade?.grade !== undefined ? studentGrade.grade : 'No calificado',
            };
          });
          
          return {
            assignment: assignment.name,
            assignmentId: assignment.id,
            submissions: processedSubmissions.length > 0 ? processedSubmissions : [],
          };
        } catch (error) {
          console.error(`[API] Error processing assignment ${assignment.id}:`, error);
          return {
            assignment: assignment.name,
            assignmentId: assignment.id,
            submissions: [],
            error: axios.isAxiosError(error) ? error.response?.data?.message || error.message : 'Error desconocido',
          };
        }
      });

      const results = await Promise.all(submissionsPromises);
      
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(results, null, 2),
          },
        ],
      };
    } catch (error) {
      console.error('[API] Fatal error in getSubmissions:', error);
      if (axios.isAxiosError(error)) {
        return {
          content: [
            {
              type: 'text',
              text: `Error de API de Moodle: ${error.response?.data?.message || error.message}. Verifica que el token tenga permisos para mod_assign_get_submissions y mod_assign_get_grades.`,
            },
          ],
          isError: true,
        };
      }
      throw error;
    }
  }

  private async provideFeedback(args: any) {
    if (!args.studentId || !args.assignmentId || !args.feedback) {
      throw new McpError(
        ErrorCode.InvalidParams,
        'Student ID, Assignment ID, and feedback are required'
      );
    }

    console.error(`[API] Providing feedback for student ${args.studentId} on assignment ${args.assignmentId}`);
    
    const response = await this.axiosInstance.get('', {
      params: {
        wsfunction: 'mod_assign_save_grade',
        assignmentid: args.assignmentId,
        userid: args.studentId,
        grade: args.grade || 0,
        attemptnumber: -1, // Último intento
        addattempt: 0,
        workflowstate: 'released',
        applytoall: 0,
        plugindata: {
          assignfeedbackcomments_editor: {
            text: args.feedback,
            format: 1, // Formato HTML
          },
        },
      },
    });

    return {
      content: [
        {
          type: 'text',
          text: `Feedback proporcionado correctamente para el estudiante ${args.studentId} en la tarea ${args.assignmentId}.`,
        },
      ],
    };
  }

  private async getSubmissionContent(args: any) {
    if (!args.studentId || !args.assignmentId) {
      throw new McpError(
        ErrorCode.InvalidParams,
        'Student ID and Assignment ID are required'
      );
    }

    console.error(`[API] Requesting submission content for student ${args.studentId} on assignment ${args.assignmentId}`);
    
    try {
      // Utilizamos la función mod_assign_get_submission_status para obtener el contenido detallado
      const response = await this.axiosInstance.get('', {
        params: {
          wsfunction: 'mod_assign_get_submission_status',
          assignid: args.assignmentId,
          userid: args.studentId,
        },
      });

      // Procesamos la respuesta para extraer el contenido relevante
      const submissionData = response.data.submission || {};
      const plugins = response.data.lastattempt?.submission?.plugins || [];
      
      // Extraemos el texto de la entrega y los archivos adjuntos
      let submissionText = '';
      const files = [];
      
      for (const plugin of plugins) {
        // Procesamos el plugin de texto en línea
        if (plugin.type === 'onlinetext') {
          const textField = plugin.editorfields?.find((field: any) => field.name === 'onlinetext');
          if (textField) {
            submissionText = textField.text || '';
          }
        }
        
        // Procesamos el plugin de archivos
        if (plugin.type === 'file') {
          const filesList = plugin.fileareas?.find((area: any) => area.area === 'submission_files');
          if (filesList && filesList.files) {
            for (const file of filesList.files) {
              files.push({
                filename: file.filename,
                fileurl: file.fileurl,
                filesize: file.filesize,
                filetype: file.mimetype,
              });
            }
          }
        }
      }
      
      // Construimos el objeto de respuesta
      const submissionContent = {
        assignment: args.assignmentId,
        userid: args.studentId,
        status: submissionData.status || 'unknown',
        submissiontext: submissionText,
        plugins: [
          {
            type: 'onlinetext',
            content: submissionText,
          },
          {
            type: 'file',
            files: files,
          },
        ],
        timemodified: submissionData.timemodified || 0,
      };
      
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(submissionContent, null, 2),
          },
        ],
      };
    } catch (error) {
      console.error('[Error]', error);
      if (axios.isAxiosError(error)) {
        return {
          content: [
            {
              type: 'text',
              text: `Error al obtener el contenido de la entrega: ${
                error.response?.data?.message || error.message
              }`,
            },
          ],
          isError: true,
        };
      }
      throw error;
    }
  }

  private async getQuizGrade(args: any) {
    if (!args.studentId || !args.quizId) {
      throw new McpError(
        ErrorCode.InvalidParams,
        'Student ID and Quiz ID are required'
      );
    }

    console.error(`[API] Requesting quiz grade for student ${args.studentId} on quiz ${args.quizId}`);
    
    try {
      const response = await this.axiosInstance.get('', {
        params: {
          wsfunction: 'mod_quiz_get_user_best_grade',
          quizid: args.quizId,
          userid: args.studentId,
        },
      });

      // Procesamos la respuesta
      const result = {
        quizId: args.quizId,
        studentId: args.studentId,
        hasGrade: response.data.hasgrade,
        grade: response.data.hasgrade ? response.data.grade : 'No calificado',
      };
      
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(result, null, 2),
          },
        ],
      };
    } catch (error) {
      console.error('[Error]', error);
      if (axios.isAxiosError(error)) {
        return {
          content: [
            {
              type: 'text',
              text: `Error al obtener la calificación del quiz: ${
                error.response?.data?.message || error.message
              }`,
            },
          ],
          isError: true,
        };
      }
      throw error;
    }
  }

  private async getVplAssignments(args?: any) {
    // Resolver courseId automáticamente desde courseName si es necesario
    const courseId = await this.resolveCourseId(args);
    
    console.error(`[API] Requesting VPL assignments for course: ${courseId}`);
    
    try {
      const response = await this.axiosInstance.get('', {
        params: {
          wsfunction: 'core_course_get_contents',
          courseid: courseId,
        },
      });

      const vplActivities = [];
      for (const section of response.data) {
        for (const module of section.modules || []) {
          if (module.modname === 'vpl') {
            vplActivities.push({
              name: module.name,
              vplid: module.instance,
              cmid: module.id,
              section: section.name,
              intro: module.description || '',
            });
          }
        }
      }
      
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(vplActivities, null, 2),
          },
        ],
      };
    } catch (error) {
      console.error('[Error]', error);
      if (axios.isAxiosError(error)) {
        return {
          content: [
            {
              type: 'text',
              text: `Error al obtener tareas VPL: ${
                error.response?.data?.message || error.message
              }`,
            },
          ],
          isError: true,
        };
      }
      throw error;
    }
  }

  private async getVplSubmission(args: any) {
    if (!args.vplId || !args.studentId) {
      throw new McpError(
        ErrorCode.InvalidParams,
        'VPL ID and Student ID are required'
      );
    }

    console.error(`[API] Requesting VPL submission for student ${args.studentId} on VPL ${args.vplId}`);
    
    try {
      // VPL requiere el CMID para obtener la entrega
      const moduleId = args.cmId || args.vplId;
      
      const response = await this.axiosInstance.get('', {
        params: {
          wsfunction: 'mod_vpl_open',
          id: moduleId,
        },
      });

      const result = {
        vplId: args.vplId,
        studentId: args.studentId,
        cmId: moduleId,
        submissionData: response.data,
        status: response.data.status || 'No submission found',
      };
      
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(result, null, 2),
          },
        ],
      };
    } catch (error) {
      console.error('[Error]', error);
      if (axios.isAxiosError(error)) {
        return {
          content: [
            {
              type: 'text',
              text: `Error al obtener entrega VPL: ${
                error.response?.data?.message || error.message
              }. Nota: VPL requiere el CMID (Course Module ID) para funcionar correctamente.`,
            },
          ],
          isError: true,
        };
      }
      throw error;
    }
  }

  public async getForums(args?: any) {
    // Resolver courseId automáticamente desde courseName si es necesario
    const courseId = await this.resolveCourseId(args);

    console.error(`[API] Requesting forums for course: ${courseId}`);

    try {
      const response = await this.axiosInstance.get('', {
        params: {
          wsfunction: 'mod_forum_get_forums_by_courses',
          courseids: [courseId],
        },
      });

      console.error('[API Response] Forums response:', response.data);

      const forums = response.data.forums || [];

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(forums, null, 2),
          },
        ],
      };
    } catch (error) {
      console.error('[Error] Failed to get forums:', error);
      if (axios.isAxiosError(error)) {
        return {
          content: [
            {
              type: 'text',
              text: `Error al obtener foros: ${
                error.response?.data?.message || error.message
              }`,
            },
          ],
          isError: true,
        };
      }
      throw error;
    }
  }

  public async getForumDiscussions(args: any) {
    const { forumId } = args;

    if (!forumId) {
      throw new McpError(
        ErrorCode.InvalidParams,
        'Forum ID is required'
      );
    }

    console.error(`[API] Requesting discussions for forum ${forumId}`);

    try {
      const response = await this.axiosInstance.get('', {
        params: {
          wsfunction: 'mod_forum_get_forum_discussions',
          forumid: forumId,
        },
      });

      const discussions = response.data.discussions || [];

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(discussions, null, 2),
          },
        ],
      };
    } catch (error) {
      console.error('[Error] Failed to get forum discussions:', error);
      if (axios.isAxiosError(error)) {
        return {
          content: [
            {
              type: 'text',
              text: `Error al obtener discusiones del foro: ${
                error.response?.data?.message || error.message
              }`,
            },
          ],
          isError: true,
        };
      }
      throw error;
    }
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('Moodle MCP server running on stdio');
  }
}

const server = new MoodleMcpServer();
server.run().catch(console.error);
