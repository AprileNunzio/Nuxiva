export async function fetchLawsState() {
  try {
    const res = await fetch('/api/v5/laws/state');
    if (res.ok) return await res.json();
  } catch {}
  return { active: true, id: 'laws' };
}
