import jwt from "jsonwebtoken";

export default function generateAccessToken(user) {

  return jwt.sign(
    {
      sub: user.id,
      username: user.username
    },
    process.env.JWT_SECRET,
    {
      expiresIn: process.env.JWT_EXPIRES_IN
    }
  );
}