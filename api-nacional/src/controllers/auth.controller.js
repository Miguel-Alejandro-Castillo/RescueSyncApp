import prisma from '../config/prisma.js';
import ApiResponse from '../utils/api-response.js'; 
import { login as loginService, logout as logoutService } from '../services/auth.service.js';

export const login = async (req, res) => {
    const { username, password } = req.body;

    const token = await loginService(username, password);
    return ApiResponse.ok(res, token);
};

export const logout = async (req, res) => {

    // Obtener el user id del sub del token decodificado
    const userId = req.user?.sub;
    await logoutService(userId);
    return ApiResponse.noContent(res);
};