export async function fetchIptvState() {
  try {
    const res = await fetch('/api/v5/iptv/state');
    if (res.ok) return await res.json();
  } catch {}
  return { active: true, id: 'iptv' };
}
