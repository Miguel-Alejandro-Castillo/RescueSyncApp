/* API NACIONAL Server */
import dotenv from "dotenv";
// Load environment variables from .env file
dotenv.config();

import { closeRedisClient, initRedisClient } from "./config/redis.js";
import app from "./app.js";

// ---------------------------
// Arranque del servidor HTTP
// ---------------------------

if (!process.env.PORT) {
  throw new Error("PORT is required");
}
const port = process.env.PORT;

let server;
async function startServer() {
  // Inicializar Redis y otros recursos necesarios antes de arrancar el servidor
  app.locals.redis = await initRedisClient();
  console.log("Redis client initialized");

  console.log(`Starting server on port ${port}...`);
  server = app.listen(port, () => {
    console.log(`Server is running on port ${port}`);
  });
}

/* Graceful shutdown */
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

/* Start the server */
startServer().catch((error) => {
  console.error("Failed to start server", error);
  process.exit(1);
});