import ApiResponse from "../utils/api-response.js";

export default function notFound(req, res) {
  return ApiResponse.notFound(res, "ENDPOINT_NOT_FOUND", "Endpoint not found");
}