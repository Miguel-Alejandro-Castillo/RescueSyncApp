import { createClient } from "redis";

const redisUrl = process.env.REDIS_URL;

export async function initRedisClient() {
  if (!redisUrl) {
    throw new Error("REDIS_URL is not configured");
  }

  const client = createClient({
    url: redisUrl
  });

  client.on("error", (error) => {
    console.error("Redis client error", error);
  });

  await client.connect();
  await client.ping();

  return client;
}

export async function closeRedisClient(client) {
  if (!client?.isOpen) {
    return;
  }

  await client.quit();
}