import jwt from "jsonwebtoken";
import ApiResponse from "../utils/api-response.js";

export default function verifyJWT(
  req,
  res,
  next
) {

  const apiPath = (process.env.API_PATH || "/api/v1").replace(/\/+$/, "");
  const loginPath = `${apiPath}/auth/login`;
  const requestPath = req.path.replace(/\/+$/, "");
  if (req.method === "POST" && requestPath === loginPath) {
    return next();
  }

  const authHeader = req.headers.authorization;

  if (!authHeader) {

    return ApiResponse.unauthorized(
      res,
      "NO_TOKEN_PROVIDED",
      "No se proporcionó el token"
    );

  }

  const [scheme, token] = authHeader.split(" ");

  if ( scheme !== "Bearer" || !token) {
    return ApiResponse.unauthorized(
      res,
      "INVALID_AUTHORIZATION_HEADER",
      "El encabezado Authorization debe usar el esquema Bearer"
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
      "No se pudo validar el token"
    );

  }

}
