export async function fetchAgentsState() {
  try {
    const res = await fetch('/api/v5/agents/state');
    if (res.ok) return await res.json();
  } catch {}
  return { active: true, id: 'agents' };
}
