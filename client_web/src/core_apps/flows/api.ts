export async function fetchFlowsState() {
  try {
    const res = await fetch('/api/v5/flows/state');
    if (res.ok) return await res.json();
  } catch {}
  return { active: true, id: 'flows' };
}
