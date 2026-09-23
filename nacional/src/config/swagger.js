import swaggerJsdoc from "swagger-jsdoc";

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
        url: "http://localhost:3000"
      }
    ]
  },
  apis: ["./src/routes/*.js"]
};

export const swaggerSpec = swaggerJsdoc(options);