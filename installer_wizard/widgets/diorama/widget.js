(() => {
  NuxivaDesk.register('diorama', {
    render(el, data, ctx) {
      if (!/^[0-9a-f]{8}$/.test(String(data.id || ''))) return;
      const frame = document.createElement('iframe');
      frame.src = `/diorama-stage?id=${encodeURIComponent(data.id)}`;
      frame.title = ctx.t('title');
      frame.className = 'diorama-frame';
      frame.allow = 'fullscreen';
      el.replaceChildren(frame);
    },
    update(el, data) {
      const frame = el.querySelector('iframe');
      if (frame && /^[0-9a-f]{8}$/.test(String(data.id || '')) && !frame.src.endsWith(`id=${data.id}`)) frame.src = `/diorama-stage?id=${encodeURIComponent(data.id)}`;
    },
    destroy(el) { el.replaceChildren(); },
  });
})();
