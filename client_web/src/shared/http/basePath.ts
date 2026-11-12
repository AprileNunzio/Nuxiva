export function adminPath(path: string): string {
  const mounted = window.location.pathname === '/admin' || window.location.pathname.startsWith('/admin/');
  return mounted && /^\/(api|static|vendor|widgets)(\/|$)/.test(path) ? `/admin${path}` : path;
}
