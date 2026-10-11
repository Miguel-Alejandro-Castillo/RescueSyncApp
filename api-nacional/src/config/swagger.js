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
    ]
  },
  apis: ["./src/routes/*.js"]
};

export const swaggerSpec = swaggerJsdoc(options);