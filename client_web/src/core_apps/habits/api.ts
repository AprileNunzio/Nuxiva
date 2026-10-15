export async function fetchHabitsState() {
  try {
    const res = await fetch('/api/v5/habits/state');
    if (res.ok) return await res.json();
  } catch {}
  return { active: true, id: 'habits' };
}
