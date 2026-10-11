import jwt from "jsonwebtoken";
import ApiResponse from "../utils/api-response.js";

export default function verifyJWT(
  req,
  res,
  next
) {

  const authHeader = req.headers.authorization;

  if (!authHeader) {

    return ApiResponse.unauthorized(
      res,
      "NO_TOKEN_PROVIDED",
      "No token provided"
    );

  }

  const [scheme, token] = authHeader.split(" ");

  if ( scheme !== "Bearer" || !token) {
    return ApiResponse.unauthorized(
      res,
      "INVALID_AUTHORIZATION_HEADER",
      "Authorization header must use Bearer scheme"
    );
  }

  try {

    const decoded = jwt.verify(
      token,
      process.env.JWT_SECRET
    );

    req.token = token;
    req.user = decoded;

    return next();

  } catch {

    return ApiResponse.unauthorized(
      res,
      "FAILED_TO_AUTHENTICATE_TOKEN",
      "Failed to authenticate token"
    );

  }

}