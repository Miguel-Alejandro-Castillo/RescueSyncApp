export const API_RESCUE =
    `${import.meta.env.VITE_API_RESCUE_URL ?? "http://localhost:3000"}${import.meta.env.VITE_API_RESCUE ?? "/api/rescue"}`;

export const API_NACIONAL =
    `${import.meta.env.VITE_API_NACIONAL_URL}${import.meta.env.VITE_API_NACIONAL}`;

export const ENDPOINTS = {
    LOGIN: `${API_RESCUE}/auth/login`,
    LOGOUT: `${API_RESCUE}/auth/logout`,
    EMERGENCIAS:
        `${API_RESCUE}/emergencias`
};
