export async function fetchAlgorithmsState() {
  try {
    const res = await fetch('/api/v5/algorithms/state');
    if (res.ok) return await res.json();
  } catch {}
  return { active: true, id: 'algorithms' };
}
