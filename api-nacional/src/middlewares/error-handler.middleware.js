import ApiResponse from '../utils/api-response.js';

export default function errorHandler(err, req, res, next) {
  console.error(err);
  return ApiResponse.error(res,
    err.code,
    err.message,
    err.status);
}