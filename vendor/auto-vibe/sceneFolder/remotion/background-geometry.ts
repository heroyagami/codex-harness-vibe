export type BackgroundAnchor = {
  x: number;
  y: number;
};

export type CoverBackgroundGeometry = {
  scale: number;
  width: number;
  height: number;
  left: number;
  top: number;
};

export const coverBackgroundGeometry = ({
  sourceWidth,
  sourceHeight,
  canvasWidth,
  canvasHeight,
  anchor,
}: {
  sourceWidth: number;
  sourceHeight: number;
  canvasWidth: number;
  canvasHeight: number;
  anchor: BackgroundAnchor;
}): CoverBackgroundGeometry => {
  const scale = Math.max(canvasWidth / sourceWidth, canvasHeight / sourceHeight);
  const width = sourceWidth * scale;
  const height = sourceHeight * scale;
  const overflowX = Math.max(0, width - canvasWidth);
  const overflowY = Math.max(0, height - canvasHeight);

  return {
    scale,
    width,
    height,
    left: -anchor.x * overflowX,
    top: -anchor.y * overflowY,
  };
};
