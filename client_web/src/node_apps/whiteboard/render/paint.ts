import { drawCallout, drawChart, drawMark, drawPlot, drawTable } from './blocks';
import { HAND, Item, MONO, SANS, imageFor, ink, n, points, s, strings } from './primitives';

export interface Viewport {
  readonly scale: number;
}

function polyline(g: CanvasRenderingContext2D, item: Item): void {
  const pts = points(item.points);
  if (pts.length === 0) {
    return;
  }
  g.beginPath();
  pts.forEach(([x, y], i) => (i ? g.lineTo(x, y ?? 0) : g.moveTo(x, y ?? 0)));
  if (pts.length === 1) {
    g.lineTo(pts[0][0] + 0.1, pts[0][1] ?? 0);
  }
  g.stroke();
}

function arrowHead(g: CanvasRenderingContext2D, item: Item): void {
  const [x1, y1, x2, y2] = [n(item, 'x1'), n(item, 'y1'), n(item, 'x2'), n(item, 'y2')];
  const angle = Math.atan2(y2 - y1, x2 - x1);
  const size = 12 + n(item, 'width', 4) * 2;
  g.beginPath();
  g.moveTo(x2, y2);
  g.lineTo(x2 - size * Math.cos(angle - 0.45), y2 - size * Math.sin(angle - 0.45));
  g.moveTo(x2, y2);
  g.lineTo(x2 - size * Math.cos(angle + 0.45), y2 - size * Math.sin(angle + 0.45));
  g.stroke();
}

function drawImage(g: CanvasRenderingContext2D, item: Item, onImage: () => void): void {
  const [x, y, w, h] = [n(item, 'x'), n(item, 'y'), n(item, 'w', 300), n(item, 'h', 200)];
  const img = imageFor(item, onImage);
  g.save();
  if (img) {
    const ratio = Math.min(w / img.naturalWidth, h / img.naturalHeight);
    const dw = img.naturalWidth * ratio;
    const dh = img.naturalHeight * ratio;
    g.drawImage(img, x, y, dw, dh);
    g.strokeStyle = 'rgba(255,255,255,.35)';
    g.lineWidth = 2;
    g.strokeRect(x, y, dw, dh);
    const caption = s(item, 'caption');
    if (caption) {
      g.fillStyle = 'rgba(255,255,255,.7)';
      g.font = `18px ${SANS}`;
      g.textBaseline = 'top';
      g.fillText(caption, x, y + dh + 8);
    }
  } else {
    g.strokeStyle = 'rgba(255,255,255,.2)';
    g.strokeRect(x, y, w, h);
  }
  g.restore();
}

function drawFormula(g: CanvasRenderingContext2D, item: Item): void {
  const size = n(item, 'size', 32);
  const lines = strings(item.lines);
  const label = s(item, 'label');
  let left = n(item, 'x');
  g.font = `${size}px ${MONO}`;
  g.textBaseline = 'top';
  if (label) {
    g.fillStyle = '#ffd166';
    g.fillText(label, left, n(item, 'y') + ((lines.length - 1) * size * 1.25) / 2);
    left += g.measureText(`${label}  `).width;
  }
  g.fillStyle = ink(item);
  lines.forEach((line, i) => g.fillText(line, left, n(item, 'y') + i * size * 1.25));
}

export function paintBoard(g: CanvasRenderingContext2D, items: readonly Item[], view: Viewport, onImage: () => void): void {
  g.setTransform(1, 0, 0, 1, 0, 0);
  g.clearRect(0, 0, g.canvas.width, g.canvas.height);
  g.setTransform(view.scale, 0, 0, view.scale, 0, 0);
  g.lineCap = 'round';
  g.lineJoin = 'round';
  for (const item of items) {
    const type = s(item, 'type');
    g.globalCompositeOperation = type === 'erase' ? 'destination-out' : 'source-over';
    g.strokeStyle = g.fillStyle = ink(item);
    g.lineWidth = n(item, 'width', 4);
    if (type === 'stroke' || type === 'erase') {
      polyline(g, item);
    } else if (type === 'text') {
      g.font = `${n(item, 'size', 40)}px ${HAND}`;
      g.textBaseline = 'top';
      g.fillText(s(item, 'text'), n(item, 'x'), n(item, 'y'));
    } else if (type === 'line' || type === 'arrow') {
      g.beginPath();
      g.moveTo(n(item, 'x1'), n(item, 'y1'));
      g.lineTo(n(item, 'x2'), n(item, 'y2'));
      g.stroke();
      if (type === 'arrow') {
        arrowHead(g, item);
      }
    } else if (type === 'rect') {
      g.strokeRect(Math.min(n(item, 'x1'), n(item, 'x2')), Math.min(n(item, 'y1'), n(item, 'y2')), Math.abs(n(item, 'x2') - n(item, 'x1')), Math.abs(n(item, 'y2') - n(item, 'y1')));
    } else if (type === 'ellipse') {
      g.beginPath();
      g.ellipse(
        (n(item, 'x1') + n(item, 'x2')) / 2,
        (n(item, 'y1') + n(item, 'y2')) / 2,
        Math.abs(n(item, 'x2') - n(item, 'x1')) / 2 || 1,
        Math.abs(n(item, 'y2') - n(item, 'y1')) / 2 || 1,
        0,
        0,
        Math.PI * 2,
      );
      g.stroke();
    } else if (type === 'mark') {
      drawMark(g, item);
    } else if (type === 'callout') {
      drawCallout(g, item);
    } else if (type === 'formula') {
      drawFormula(g, item);
    } else if (type === 'image') {
      drawImage(g, item, onImage);
    } else if (type === 'plot') {
      drawPlot(g, item);
    } else if (type === 'chart') {
      drawChart(g, item);
    } else if (type === 'table') {
      drawTable(g, item);
    }
  }
  g.globalCompositeOperation = 'source-over';
}
