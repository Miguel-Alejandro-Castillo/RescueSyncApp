// RescueSync Backend Server
import express from "express";
import dotenv from "dotenv";

import swaggerUi from "swagger-ui-express";
import { swaggerSpec } from "./config/swagger.js";

dotenv.config();

const app = express();
const port = process.env.PORT || 3000;

app.use(express.json());

app.use(
  "/api-docs",
  swaggerUi.serve,
  swaggerUi.setup(swaggerSpec)
);

app.get("/", (req, res) => {
  console.log("Received request for /");
  res.send("RescueSync API Nacional is running. Hot reload enabled 1.0.");
});

app.listen(port, () => {
  console.log(`Server is running on port ${port}`);
});