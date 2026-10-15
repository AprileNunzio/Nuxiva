export async function fetchPeopleState() {
  try {
    const res = await fetch('/api/v5/people/state');
    if (res.ok) return await res.json();
  } catch {}
  return { active: true, id: 'people' };
}
