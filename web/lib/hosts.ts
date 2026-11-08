/** Host-based routing: admin.crayonlark.com (or admin.localhost) serves the /admin tree. */
export function isAdminHost(host: string | null | undefined): boolean {
  if (!host) return false;
  const hostname = host.split(":")[0].toLowerCase();
  return hostname.startsWith("admin.");
}
