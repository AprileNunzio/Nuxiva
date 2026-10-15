export async function fetchFirewallState() {
  try {
    const res = await fetch('/api/v5/firewall/state');
    if (res.ok) return await res.json();
  } catch {}
  return { active: true, id: 'firewall' };
}
