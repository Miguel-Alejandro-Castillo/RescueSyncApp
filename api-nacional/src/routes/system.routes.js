import express from 'express';

const router = express.Router();

router.get("/", (req, res) => {
  console.log("Received request for /");
  res.send("RescueSync API Nacional is running. Hot reload enabled 1.0.");
});

router.get("/health", async (req, res) => {
  const redis = req.app.locals.redis;
  let redisStatus = "disconnected";

  if (redis?.isOpen) {
    await redis.ping();
    redisStatus = "connected";
  }

  res.json({
    status: "ok",
    service: "api-nacional",
    redis: redisStatus
  });
});

export default router;