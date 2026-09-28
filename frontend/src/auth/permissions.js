
export const ROLE_NAMES = {
  municipal: ['operador_municipal'],
  coordinador: ['centro_coordinador'],
  ong: ['representante_ong'],
  auditor: ['auditor', 'directivo'],
};

export const ACTIONS = [
  { permission: 'emergencias.crear', profiles: ['municipal'], path: '/emergencias/nueva', label: 'Emergencias', title: 'Registrar una emergencia', description: 'Indicá la zona afectada, la gravedad y la situación inicial.' },
  { permission: 'lotes.crear', profiles: ['coordinador'], path: '/lotes/nuevo', label: 'Lotes y convocatorias', title: 'Organizar lotes de ayuda', description: 'Elegí una emergencia pendiente, definí los recursos y publicá la convocatoria.' },
  { permission: 'ofertas.crear', profiles: ['ong'], path: '/ofertas', label: 'Ofertas', title: 'Ofrecer ayuda', description: 'Consultá las convocatorias y cargá ofertas para los lotes disponibles.' },
];

export function getProfiles(memberships) {
  const names = new Set((Array.isArray(memberships) ? memberships : []).map(item => item?.role?.name).filter(name => typeof name === 'string'));
  return Object.keys(ROLE_NAMES).filter(profile => ROLE_NAMES[profile].some(name => names.has(name)));
}

export function canAccess(memberships, permission) {
  const action = ACTIONS.find(action => action.permission === permission);
  const profiles = getProfiles(memberships);
  return Boolean(action?.profiles.some(profile => profiles.includes(profile)));
}
