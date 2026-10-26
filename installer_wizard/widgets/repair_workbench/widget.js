(() => {
  NuxivaDesk.register('repair_workbench', {
    render(el, data, ctx) {
      if (!data.project_id || !data.session_id) return;
      const frame = document.createElement('iframe');
      frame.src = `/repair-workbench?project=${encodeURIComponent(data.project_id)}&session=${encodeURIComponent(data.session_id)}`;
      frame.title = ctx.t('title');
      frame.className = 'repair-workbench-frame';
      el.replaceChildren(frame);
      const onMessage = (event) => {
        if (event.origin !== location.origin || event.source !== frame.contentWindow || event.data?.type !== 'nuxiva:repair-exit') return;
        fetch('/api/desk/close', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Nuxiva-Request': '1' },
          body: JSON.stringify({ key: `repair:${data.project_id}` }) });
      };
      window.addEventListener('message', onMessage);
      el._repairCleanup = () => window.removeEventListener('message', onMessage);
    },
    update() {},
    destroy(el) { el._repairCleanup?.(); el.replaceChildren(); },
  });
})();
