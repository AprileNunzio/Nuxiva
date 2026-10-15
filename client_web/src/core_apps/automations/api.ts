export async function fetchAutomationsState() {
  try {
    const res = await fetch('/api/v5/automations/state');
    if (res.ok) return await res.json();
  } catch {}
  return { active: true, id: 'automations' };
}
