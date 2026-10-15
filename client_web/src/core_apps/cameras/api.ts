export async function fetchCamerasState() {
  try {
    const res = await fetch('/api/v5/cameras/state');
    if (res.ok) return await res.json();
  } catch {}
  return { active: true, id: 'cameras' };
}
