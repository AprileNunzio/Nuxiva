export async function fetchTwinState() {
  try {
    const res = await fetch('/api/v5/twin/state');
    if (res.ok) return await res.json();
  } catch {}
  return { active: true, id: 'twin' };
}
