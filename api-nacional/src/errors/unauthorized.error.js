import ApiError from './api.error.js';

export default class UnauthorizedError
  extends ApiError {

  constructor(
    code = 'UNAUTHORIZED',
    message = 'Unauthorized'
  ) {
    super(code, message, 401);
  }

}