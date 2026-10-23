import jwt from "jsonwebtoken";

export default function generateAccessToken(user) {

  return jwt.sign(
    {
      sub: user.id,
      username: user.username
    },
    process.env.JWT_SECRET,
    {
      // jsonwebtoken interprets numeric strings as milliseconds (e.g. "3600" = 3.6s).
      // Convert the configured duration to a number so it is interpreted as seconds.
      expiresIn: Number(process.env.JWT_EXPIRES_IN)
    }
  );
}
