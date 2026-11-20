/**
 * Gestore interattivo delle reazioni visive ed emoticons a scomparsa
 * per la Pagina 80 (Tactical Web Cockpit).
 */

export function triggerEmoticonReaction(
  reactionId = "hearts",
  label = "Cuori & Affetto",
  emojis = ["💖", "💕", "❤️", "🥰", "😍"]
) {
  const stage = document.getElementById("emoticon-floating-stage");
  const drawer = document.getElementById("emoticon-popup-drawer");
  const icon = document.getElementById("emoticon-popup-icon");
  const title = document.getElementById("emoticon-popup-title");
  const sub = document.getElementById("emoticon-popup-sub");

  if (drawer) {
    if (icon) icon.textContent = emojis && emojis.length ? emojis[0] : "💖";
    if (title) title.textContent = label || "Reazione Emotiva";
    if (sub) sub.textContent = `Nuxiva lancia ${reactionId} a scomparsa`;
    drawer.classList.add("active");
    clearTimeout(drawer._timeout);
    drawer._timeout = setTimeout(() => {
      drawer.classList.remove("active");
    }, 3200);
  }

  if (stage) {
    const list = emojis && emojis.length ? emojis : ["💖", "💕", "❤️", "🥰", "😍"];
    const particleCount = 20;
    for (let i = 0; i < particleCount; i++) {
      const p = document.createElement("div");
      p.className = "floating-emoticon-particle";
      p.textContent = list[Math.floor(Math.random() * list.length)];

      const leftPercent = 10 + Math.random() * 80;
      const startBottom = 30 + Math.random() * 70;
      const delay = Math.random() * 0.7;
      const size = 1.6 + Math.random() * 1.4;

      p.style.left = `${leftPercent}%`;
      p.style.bottom = `${startBottom}px`;
      p.style.fontSize = `${size}rem`;
      p.style.animationDelay = `${delay}s`;

      stage.appendChild(p);
      setTimeout(() => {
        p.remove();
      }, 3500);
    }
  }
}

export function formatRichMessageText(text, escapeFn) {
  const escapeHtml = escapeFn || ((t) => {
    const div = document.createElement("div");
    div.textContent = t;
    return div.innerHTML;
  });

  let escaped = escapeHtml(text);
  // Converte tag reazione visiva [reaction:tipo] in badge discreto
  escaped = escaped.replace(/\[reaction:([a-zA-Z0-9_\-]+)\]/gi, (match, p1) => {
    const lower = p1.toLowerCase();
    const icon = lower === "hearts" ? "💖" : lower === "sparkles" ? "✨" : lower === "blush" ? "🥰" : "🎉";
    return `<span class="reaction-badge">${icon} ${p1}</span>`;
  });
  // Converte tag vocali [laughs], [sighs], ecc. in chip grafici
  escaped = escaped.replace(/\[([a-zA-Z_\s]{3,25})\]/g, (match, p1) => {
    return `<span class="vocal-badge">🎙️ ${p1}</span>`;
  });
  return escaped;
}
