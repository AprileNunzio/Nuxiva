export async function fetchMusicState() {
  try {
    const res = await fetch('/api/v5/music/state');
    if (res.ok) return await res.json();
  } catch {}
  return { active: true, id: 'music' };
}
