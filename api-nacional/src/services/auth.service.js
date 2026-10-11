import prisma from '../config/prisma.js';
import generateAccessToken from '../utils/jwt.util.js';
import NotFoundError from '../errors/not-found.error.js';
import UnauthorizedError from '../errors/unauthorized.error.js';

export async function login(username, password) {

  const user = await prisma.user.findUnique({
    where: { username }
  });

  if (!user || user.password !== password)
    throw new UnauthorizedError('INVALID_CREDENTIALS', 'Invalid username or password');

  const token = generateAccessToken(user);
  return {
    "access_token": token,
    "token_type": "Bearer",
    "expires_in": Number(process.env.JWT_EXPIRES_IN)
  };
}

export async function logout(userId) {
  // Implement logout logic if needed, e.g., invalidate tokens
  return true;
}