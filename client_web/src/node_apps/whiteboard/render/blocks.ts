import { CALLOUT, Item, MONO, SANS, SERIES, ink, n, niceStep, numbers, points, roundRect, s, strings } from './primitives';

function title(g: CanvasRenderingContext2D, item: Item, size: number): void {
  const text = s(item, 'title');
  if (text) {
    g.fillStyle = '#ffd166';
    g.font = `${size}px ${SANS}`;
    g.textBaseline = 'top';
    g.fillText(text, n(item, 'x') + 12, n(item, 'y') + 8);
  }
}

export function drawPlot(g: CanvasRenderingContext2D, item: Item): void {
  const [x, y, w0, h0] = [n(item, 'x'), n(item, 'y'), n(item, 'w', 400), n(item, 'h', 300)];
  const [xmin, xmax, ymin, ymax] = [n(item, 'xmin', -10), n(item, 'xmax', 10), n(item, 'ymin', -10), n(item, 'ymax', 10)];
  if (xmax <= xmin || ymax <= ymin) {
    return;
  }
  const pad = 46;
  const x0 = x + pad;
  const y0 = y + (s(item, 'title') ? 40 : 14);
  const w = w0 - pad - 14;
  const h = h0 - (y0 - y) - 34;
  const sx = (v: number) => x0 + ((v - xmin) / (xmax - xmin)) * w;
  const sy = (v: number) => y0 + h - ((v - ymin) / (ymax - ymin)) * h;
  g.save();
  g.fillStyle = 'rgba(0,0,0,.25)';
  g.fillRect(x, y, w0, h0);
  title(g, item, 26);
  g.font = `14px ${MONO}`;
  g.lineWidth = 1;
  for (const [lo, hi, axis] of [[xmin, xmax, 'x'], [ymin, ymax, 'y']] as const) {
    const step = niceStep(hi - lo);
    for (let v = Math.ceil(lo / step) * step, guard = 0; v <= hi + 1e-9 && guard < 60; v += step, guard += 1) {
      g.strokeStyle = 'rgba(255,255,255,.08)';
      g.beginPath();
      if (axis === 'x') {
        g.moveTo(sx(v), y0);
        g.lineTo(sx(v), y0 + h);
      } else {
        g.moveTo(x0, sy(v));
        g.lineTo(x0 + w, sy(v));
      }
      g.stroke();
      g.fillStyle = 'rgba(255,255,255,.55)';
      const label = Math.abs(v) < 1e-9 ? '0' : `${+v.toPrecision(3)}`;
      if (axis === 'x') {
        g.textBaseline = 'top';
        g.fillText(label, sx(v) - 8, y0 + h + 6);
      } else {
        g.textBaseline = 'middle';
        g.fillText(label, x + 4, sy(v));
      }
    }
  }
  g.strokeStyle = 'rgba(255,255,255,.6)';
  g.lineWidth = 2;
  g.beginPath();
  if (ymin <= 0 && ymax >= 0) {
    g.moveTo(x0, sy(0));
    g.lineTo(x0 + w, sy(0));
  }
  if (xmin <= 0 && xmax >= 0) {
    g.moveTo(sx(0), y0);
    g.lineTo(sx(0), y0 + h);
  }
  g.stroke();
  const series = Array.isArray(item.series) ? (item.series as Item[]) : [];
  g.save();
  g.beginPath();
  g.rect(x0, y0, w, h);
  g.clip();
  series.forEach((line) => {
    g.strokeStyle = ink(line, SERIES[0]);
    g.lineWidth = 3;
    g.beginPath();
    let pen = false;
    for (const [px, py] of points(line.points)) {
      if (py === null) {
        pen = false;
        continue;
      }
      if (pen) {
        g.lineTo(sx(px), sy(py));
      } else {
        g.moveTo(sx(px), sy(py));
      }
      pen = true;
    }
    g.stroke();
  });
  g.restore();
  g.font = `18px ${MONO}`;
  g.textBaseline = 'top';
  series.forEach((line, i) => {
    g.fillStyle = ink(line, SERIES[0]);
    g.fillText(s(line, 'label'), x0 + 10, y0 + 8 + i * 24);
  });
  g.restore();
}

export function drawChart(g: CanvasRenderingContext2D, item: Item): void {
  const [x, y, w0, h0] = [n(item, 'x'), n(item, 'y'), n(item, 'w', 400), n(item, 'h', 300)];
  const values = numbers(item.values);
  const labels = strings(item.labels);
  if (values.length === 0) {
    return;
  }
  const top = y + (s(item, 'title') ? 44 : 14);
  const h = h0 - (top - y) - 40;
  const max = Math.max(...values.map(Math.abs), 1e-9);
  g.save();
  g.fillStyle = 'rgba(0,0,0,.25)';
  g.fillRect(x, y, w0, h0);
  title(g, item, 26);
  g.font = `16px ${SANS}`;
  if (s(item, 'kind') === 'pie') {
    const total = values.reduce((a, b) => a + Math.max(0, b), 0) || 1;
    const cx = x + h0 / 2 + 10;
    const cy = top + h / 2;
    const r = Math.max(4, Math.min(h / 2, w0 / 3));
    let angle = -Math.PI / 2;
    values.forEach((v, i) => {
      const da = (Math.max(0, v) / total) * Math.PI * 2;
      g.fillStyle = SERIES[i % SERIES.length];
      g.beginPath();
      g.moveTo(cx, cy);
      g.arc(cx, cy, r, angle, angle + da);
      g.closePath();
      g.fill();
      g.textBaseline = 'middle';
      g.fillRect(cx + r + 30, top + 9 + i * 26, 14, 14);
      g.fillStyle = '#f4f4f0';
      g.fillText(`${labels[i] ?? ''} ${Math.round((Math.max(0, v) / total) * 100)}%`, cx + r + 52, top + 16 + i * 26);
      angle += da;
    });
  } else {
    const left = x + 20;
    const w = w0 - 40;
    const slot = w / values.length;
    const base = top + h;
    g.strokeStyle = 'rgba(255,255,255,.5)';
    g.beginPath();
    g.moveTo(left, base);
    g.lineTo(left + w, base);
    g.stroke();
    const ys = values.map((v) => base - (Math.max(v, 0) / max) * (h - 24));
    values.forEach((v, i) => {
      const cx = left + slot * i + slot / 2;
      if (s(item, 'kind') === 'bar') {
        g.fillStyle = SERIES[i % SERIES.length];
        g.fillRect(cx - slot * 0.32, ys[i], slot * 0.64, base - ys[i]);
      }
      g.fillStyle = '#f4f4f0';
      g.textAlign = 'center';
      g.textBaseline = 'bottom';
      g.fillText(`${+v.toPrecision(4)}`, cx, ys[i] - 4);
      g.textBaseline = 'top';
      g.fillText(labels[i] ?? '', cx, base + 8);
      g.textAlign = 'left';
    });
    if (s(item, 'kind') === 'line') {
      g.strokeStyle = SERIES[0];
      g.lineWidth = 3;
      g.beginPath();
      ys.forEach((yy, i) => {
        const cx = left + slot * i + slot / 2;
        if (i) {
          g.lineTo(cx, yy);
        } else {
          g.moveTo(cx, yy);
        }
      });
      g.stroke();
    }
  }
  g.restore();
}

export function drawTable(g: CanvasRenderingContext2D, item: Item): void {
  const [x, y0, w0, size] = [n(item, 'x'), n(item, 'y'), n(item, 'w', 600), n(item, 'size', 24)];
  const header = strings(item.header);
  const rows = (Array.isArray(item.rows) ? item.rows : []).map(strings);
  const all = header.length ? [header, ...rows] : rows;
  const cols = Math.max(1, ...all.map((r) => r.length));
  const rowH = size * 1.6;
  const cw = w0 / cols;
  const titled = s(item, 'title');
  let y = y0;
  g.save();
  g.textBaseline = 'middle';
  if (titled) {
    g.fillStyle = '#ffd166';
    g.font = `${size + 4}px ${SANS}`;
    g.fillText(titled, x, y + size * 0.7);
    y += size * 1.4;
  }
  all.forEach((row, r) => {
    const head = r === 0 && header.length > 0;
    g.fillStyle = head ? 'rgba(41,224,255,.18)' : r % 2 ? 'rgba(255,255,255,.04)' : 'rgba(0,0,0,.15)';
    g.fillRect(x, y, w0, rowH);
    g.font = `${head ? 'bold ' : ''}${size}px ${SANS}`;
    g.fillStyle = head ? '#29e0ff' : '#f4f4f0';
    row.forEach((cell, c) => {
      g.save();
      g.beginPath();
      g.rect(x + c * cw, y, cw - 6, rowH);
      g.clip();
      g.fillText(cell, x + c * cw + 10, y + rowH / 2);
      g.restore();
    });
    y += rowH;
  });
  const start = y0 + (titled ? size * 1.4 : 0);
  g.strokeStyle = 'rgba(255,255,255,.2)';
  g.strokeRect(x, start, w0, y - start);
  g.restore();
}

export function drawCallout(g: CanvasRenderingContext2D, item: Item): void {
  const [color, icon] = CALLOUT[s(item, 'kind')] ?? CALLOUT.info;
  const [x, y, w, h, size] = [n(item, 'x'), n(item, 'y'), n(item, 'w', 400), n(item, 'h', 120), n(item, 'size', 24)];
  g.save();
  roundRect(g, x, y, w, h, 16);
  g.fillStyle = 'rgba(6,20,26,.92)';
  g.fill();
  g.strokeStyle = color;
  g.lineWidth = 3;
  g.stroke();
  g.fillStyle = color;
  g.fillRect(x, y + 12, 6, h - 24);
  g.textBaseline = 'top';
  g.font = `bold 28px ${SANS}`;
  g.fillText(`${icon}  ${s(item, 'title')}`, x + 22, y + 14);
  g.font = `${size}px ${SANS}`;
  g.fillStyle = '#eef9ff';
  strings(item.lines).forEach((line, i) => g.fillText(line, x + 22, y + 56 + i * size * 1.35));
  g.restore();
}

export function drawMark(g: CanvasRenderingContext2D, item: Item): void {
  const [x1, y1, x2, y2] = [n(item, 'x1'), n(item, 'y1'), n(item, 'x2'), n(item, 'y2')];
  const x = Math.min(x1, x2);
  const y = Math.min(y1, y2);
  const w = Math.abs(x2 - x1);
  const h = Math.abs(y2 - y1);
  const style = s(item, 'style');
  g.save();
  g.strokeStyle = g.fillStyle = ink(item, '#ffd166');
  g.lineWidth = n(item, 'width', 4);
  g.beginPath();
  if (style === 'highlight') {
    g.globalAlpha = 0.28;
    g.fillRect(x - 6, y - 2, w + 12, h + 4);
  } else if (style === 'underline') {
    g.moveTo(x, y + h + 4);
    g.lineTo(x + w, y + h + 4);
    g.stroke();
  } else if (style === 'wavy') {
    for (let i = 0; i <= w; i += 10) {
      const yy = y + h + 4 + (i % 20 ? 4 : -4);
      if (i) {
        g.lineTo(x + i, yy);
      } else {
        g.moveTo(x, yy);
      }
    }
    g.stroke();
  } else if (style === 'circle') {
    g.ellipse(x + w / 2, y + h / 2, w / 2 + 18, h / 2 + 14, -0.04, 0, Math.PI * 2);
    g.stroke();
  } else if (style === 'box') {
    roundRect(g, x - 10, y - 8, w + 20, h + 16, 8);
    g.stroke();
  } else if (style === 'strike') {
    g.moveTo(x, y + h / 2);
    g.lineTo(x + w, y + h / 2);
    g.stroke();
  }
  g.restore();
}
