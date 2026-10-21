(() => {
  NuxivaDesk.register('repair_workbench', {
    render(el, data, ctx) {
      const frame = document.createElement('iframe');
      frame.src = `/repair-workbench?project=${encodeURIComponent(data.project_id)}&session=${encodeURIComponent(data.session_id)}`;
      frame.title = ctx.t('title');
      frame.className = 'repair-workbench-frame';
      el.replaceChildren(frame);
    },
    update() {},
    destroy(el) { el.replaceChildren(); },
  });
})();
