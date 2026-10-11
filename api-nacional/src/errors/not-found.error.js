// errors/not-found.error.js

import ApiError from './api.error.js';

export default class NotFoundError extends ApiError {

  constructor(
    code = 'NOT_FOUND',
    message = 'Resource not found'
  ) {
    super(code, message, 404);
  }

}