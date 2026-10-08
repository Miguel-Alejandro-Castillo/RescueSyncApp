// RescueSync Backend Server
import express from "express";
import dotenv from "dotenv";

import swaggerUi from "swagger-ui-express";
import { swaggerSpec } from "./config/swagger.js";
import { closeRedisClient, initRedisClient } from "./config/redis.js";

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

app.get("/health", async (req, res) => {
  const redis = req.app.locals.redis;
  let redisStatus = "disconnected";

  if (redis?.isOpen) {
    await redis.ping();
    redisStatus = "connected";
  }

  res.json({
    status: "ok",
    service: "rescuesync-nacional",
    redis: redisStatus
  });
});

let server;

async function startServer() {
  app.locals.redis = await initRedisClient();

  server = app.listen(port, () => {
    console.log(`Server is running on port ${port}`);
  });
}

async function shutdown(signal) {
  console.log(`Received ${signal}. Shutting down gracefully.`);

  if (server) {
    await new Promise((resolve, reject) => {
      server.close((error) => {
        if (error) {
          reject(error);
          return;
        }

        resolve();
      });
    });
  }

  await closeRedisClient(app.locals.redis);
  process.exit(0);
}

process.on("SIGINT", () => {
  shutdown("SIGINT").catch((error) => {
    console.error("Error during shutdown", error);
    process.exit(1);
  });
});

process.on("SIGTERM", () => {
  shutdown("SIGTERM").catch((error) => {
    console.error("Error during shutdown", error);
    process.exit(1);
  });
});

startServer().catch((error) => {
  console.error("Failed to start server", error);
  process.exit(1);
});