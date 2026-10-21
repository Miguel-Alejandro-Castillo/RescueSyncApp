
export const ROLE_NAMES = {
  municipal: ['operador_municipal'],
  coordinador: ['centro_coordinador'],
  ong: ['representante_ong'],
  auditor: ['auditor', 'directivo'],
};

const PERMISSION_PROFILES = {
  'ofertas.ver_propias': ['ong'],
  'emergencias.crear': ['municipal'],
  'emergencias.ver_propias': ['municipal'],
  'emergencias.ver_lotes': ['municipal'],
  'emergencias.adjudicar_ofertas': ['municipal'],
  'lotes.crear': ['coordinador'],
  'ofertas.crear': ['ong'],
  'ofertas.ver_invalidas': ['coordinador'],
};

const ROUTE_PERMISSIONS = [
  { path: '/ofertas/misofertas', permission: 'ofertas.ver_propias' },
  { path: '/emergencias/nueva', permission: 'emergencias.crear' },
  { path: '/emergencias/propias', permission: 'emergencias.ver_propias' },
  { path: '/lotes/nuevo', permission: 'lotes.crear' },
  { path: '/ofertas', permission: 'ofertas.crear' },
  { path: '/ofertas-invalidas', permission: 'ofertas.ver_invalidas' },
  { path: '/ofertas-consorcio', permission: 'ofertas.ver_propias' },
];

const ROUTE_PERMISSION_PATTERNS = [
  { pattern: /^\/emergencias\/[^/]+\/lotes$/, permission: 'ofertas.crear' },
  { pattern: /^\/emergencias\/propias\/[^/]+\/lotes\/[^/]+$/, permission: 'emergencias.ver_lotes' },
  { pattern: /^\/emergencias\/propias\/[^/]+\/lotes\/[^/]+\/adjudicar-ofertas$/, permission: 'emergencias.adjudicar_ofertas' }
];

export const ACTIONS = [
  { permission: 'ofertas.ver_validacion', profiles: ['municipal', 'coordinador', 'auditor'], path: '/validacion-ofertas', label: 'Validación de ofertas', title: 'Validación de ofertas', description: 'Consultá el resultado del chequeo de recursos al cierre de la convocatoria.' },
  { permission: 'ofertas.ver_propias', profiles: ['ong'], path: '/ofertas/misofertas', label: 'Mis ofertas', title: 'Mis ofertas', description: 'Consulte y edite las ofertas registradas.' },
  { permission: 'emergencias.crear', profiles: ['municipal'], path: '/emergencias/nueva', label: 'Nueva emergencia', title: 'Registrar una emergencia', description: 'Indicá la zona afectada, la gravedad y la situación inicial.' },
  { permission: 'emergencias.ver_propias', profiles: ['municipal'], path: '/emergencias/propias', label: 'Mis emergencias', title: 'Ver mis emergencias', description: 'Consultá las emergencias que registraste previamente.' },
  { permission: 'lotes.crear', profiles: ['coordinador'], path: '/lotes/nuevo', label: 'Lotes y convocatorias', title: 'Organizar lotes de ayuda', description: 'Elegí una emergencia pendiente, definí los recursos y publicá la convocatoria.' },
  { permission: 'ofertas.crear', profiles: ['ong'], path: '/ofertas', label: 'Ofertas', title: 'Ofrecer ayuda', description: 'Consultá las convocatorias y cargá ofertas para los lotes disponibles.' },
  { permission: 'ofertas.ver_invalidas', profiles: ['coordinador'], path: '/ofertas-invalidas', label: 'Ofertas inválidas', title: 'Ofertas inválidas', description: 'Revisá las ofertas inválidas y elegí qué acción tomar.' },
];

export function getProfiles(memberships) {
  const names = new Set((Array.isArray(memberships) ? memberships : []).map(item => item?.role?.name).filter(name => typeof name === 'string'));
  return Object.keys(ROLE_NAMES).filter(profile => ROLE_NAMES[profile].some(name => names.has(name)));
}

export function canAccess(memberships, permission) {
  const allowedProfiles = PERMISSION_PROFILES[permission];
  if (!Array.isArray(allowedProfiles)) return false;
  const profiles = getProfiles(memberships);
  return allowedProfiles.some(profile => profiles.includes(profile));
}

export function getPermissionForPath(pathname) {
  const normalizedPath = typeof pathname === 'string' ? pathname.replace(/\/+$/, '') || '/' : '';
  const exactPermission = ROUTE_PERMISSIONS.find(route => route.path === normalizedPath)?.permission;
  if (exactPermission) return exactPermission;
  return ROUTE_PERMISSION_PATTERNS.find(route => route.pattern.test(normalizedPath))?.permission ?? null;
}
