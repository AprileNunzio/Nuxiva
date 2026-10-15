export async function fetchEmergencyState() {
  try {
    const res = await fetch('/api/v5/emergency/state');
    if (res.ok) return await res.json();
  } catch {}
  return { active: true, id: 'emergency' };
}
