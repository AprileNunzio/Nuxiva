export async function fetchPlacesState() {
  try {
    const res = await fetch('/api/v5/places/state');
    if (res.ok) return await res.json();
  } catch {}
  return { active: true, id: 'places' };
}
