import swaggerJsdoc from "swagger-jsdoc";

const SWAGGER_URL = process.env.SWAGGER_URL;
const PATH_API = process.env.API_PATH;

const options = {
  definition: {
    openapi: "3.0.0",
    info: {
      title: "Sistema Nacional de Gestión de Recursos y Riesgos",
      version: "1.0.0",
      description: "API REST del Sistema Nacional de Gestión de Recursos y Riesgos, responsable \
        de centralizar la información de las ONGs, sus capacidades y los recursos \
        disponibles para la atención de emergencias. \
        Permite consultar y validar organizaciones y recursos, evaluar capacidades, \
        registrar compromisos de recursos adjudicados y liberarlos al finalizar \
        su participación en una emergencia."
    },
    servers: [
      {
        url: SWAGGER_URL
      }
    ],
    components: {
      securitySchemes: {
        BearerAuth: {
          type: "http",
          scheme: "bearer",
          bearerFormat: "JWT",
          description: "Ingresá el access_token obtenido en " + PATH_API + "/auth/login."
        }
      },
      schemas: {
        Error: {
          type: "object",
          properties: {
            error: {
              type: "object",
              properties: {
                code: { type: "string", example: "NO_TOKEN_PROVIDED" },
                message: { type: "string", example: "No se proporcionó el token" }
              }
            }
          }
        }
      }
    },
    security: [{ BearerAuth: [] }]
  },
  apis: ["./src/routes/*.js"]
};

export const swaggerSpec = swaggerJsdoc(options);
