import swaggerJsdoc from "swagger-jsdoc";

const SWAGGER_URL = process.env.SWAGGER_URL;
const options = {
  definition: {
    openapi: "3.0.0",
    info: {
      title: "Sistema Nacional de Gestión de Recursos y Riesgos",
      version: "1.0.0",
      description: "API del Sistema Nacional de Gestión de Recursos y Riesgos"
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
          description: "Ingresá el access_token obtenido en /api/v1/auth/login."
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
