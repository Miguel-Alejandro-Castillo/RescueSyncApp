import { ACTIONS, canAccess } from './permissions.js';

export function getLoginDestination(from, memberships) {
  if (typeof from !== 'string' || !from.startsWith('/') || from.startsWith('//') || from.includes('\\')) {
    return '/dashboard';
  }
  const pathname = from.split(/[?#]/)[0].replace(/\/+$/, '') || '/';
  if (pathname === '/' || pathname === '/dashboard') return from;
  const permission = ACTIONS.find(action => action.path === pathname)?.permission
    || (/^\/emergencias\/[^/]+\/lotes$/.test(pathname) ? 'ofertas.crear' : null);
  return permission && canAccess(memberships, permission) ? from : '/dashboard';
}
