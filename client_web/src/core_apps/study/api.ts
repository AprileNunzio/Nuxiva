export async function fetchStudyState() {
  try {
    const res = await fetch('/api/v5/study/state');
    if (res.ok) return await res.json();
  } catch {}
  return { active: true, id: 'study' };
}
