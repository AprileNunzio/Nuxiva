export async function fetchHandsState() {
  try {
    const res = await fetch('/api/v5/hands/state');
    if (res.ok) return await res.json();
  } catch {}
  return { active: true, id: 'hands' };
}
