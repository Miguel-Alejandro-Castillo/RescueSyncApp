// errors/api.error.js

export default class ApiError extends Error {

  constructor(code, message = 'Internal Server Error', status = 500) {
    super(message);
    this.code = code;
    this.status = status;
  }

}