export async function fetchGoogleState() {
  try {
    const res = await fetch('/api/v5/google/state');
    if (res.ok) return await res.json();
  } catch {}
  return { active: true, id: 'google' };
}
