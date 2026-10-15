export async function fetchVpnState() {
  try {
    const res = await fetch('/api/v5/vpn/state');
    if (res.ok) return await res.json();
  } catch {}
  return { active: true, id: 'vpn' };
}
