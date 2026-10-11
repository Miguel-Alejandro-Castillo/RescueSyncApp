export default class ApiResponse {

  static ok(res, data) {
    return res.status(200).json({
      data
    });
  }

  static created(res, data) {
    return res.status(201).json({
      data
    });
  }

  static noContent(res) {
    return res.status(204).send();
  }

  static error(res, code = 'INTERNAL_SERVER_ERROR', message = 'Internal Server Error', status = 500) {
    return res.status(status).json({
        error: {
          code,
          message
        }
    });
  }

  static badRequest(res, code, message) {
    return this.error(res, code, message, 400);
  }

  static notFound(res, code, message) {
    return this.error(res, code, message, 404);
  }

  static conflict(res, code, message) {
    return this.error(res, code, message, 409);
  }

  static unauthorized(res, code, message) {
    return this.error(res, code, message, 401);
  }

  static forbidden(res, code, message) {
    return this.error(res, code, message, 403);
  }

}