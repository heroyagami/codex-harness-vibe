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
  // Preserve the legacy 1080x1440 crop exactly. We only enlarge a background
  // when a larger canvas needs extra coverage; sources are never downscaled.
  const scale = Math.max(
    1,
    canvasWidth / sourceWidth,
    canvasHeight / sourceHeight,
  );
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
