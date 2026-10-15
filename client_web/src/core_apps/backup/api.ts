export async function fetchBackupState() {
  try {
    const res = await fetch('/api/v5/backup/state');
    if (res.ok) return await res.json();
  } catch {}
  return { active: true, id: 'backup' };
}
