export function containRect(width: number, height: number, sourceWidth: number, sourceHeight: number) {
  if (width <= 0 || height <= 0 || sourceWidth <= 0 || sourceHeight <= 0) {
    return { left: 0, top: 0, width: 0, height: 0 };
  }
  const scale = Math.min(width / sourceWidth, height / sourceHeight);
  const fittedWidth = sourceWidth * scale;
  const fittedHeight = sourceHeight * scale;
  return { left: (width - fittedWidth) / 2, top: (height - fittedHeight) / 2,
    width: fittedWidth, height: fittedHeight };
}
