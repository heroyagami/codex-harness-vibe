import React from "react";
import {
  AbsoluteFill,
  Easing,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import {
  BACKGROUND_COLOR,
  BACKGROUND_HEIGHT,
  BACKGROUND_IMAGE,
  BACKGROUND_WIDTH,
  DURATION_IN_FRAMES,
  FOREGROUND_TRAVEL,
  FROM_BACKGROUND_ANCHOR,
  FROM_FOREGROUND_IMAGE,
  HEIGHT,
  TO_BACKGROUND_ANCHOR,
  TO_FOREGROUND_IMAGE,
  WIDTH,
} from "../remotion/transition-config";

const INPUTS = {
  background: staticFile(BACKGROUND_IMAGE),
  fromForeground: staticFile(FROM_FOREGROUND_IMAGE),
  toForeground: staticFile(TO_FOREGROUND_IMAGE),
};

const Panel: React.FC<{
  src: string;
  x: number;
  y: number;
  opacity: number;
}> = ({ src, x, y, opacity }) => (
  <AbsoluteFill
    style={{ opacity, transform: `translate3d(${x}px, ${y}px, 0)` }}
  >
    <Img src={src} style={{ height: "100%", width: "100%" }} />
  </AbsoluteFill>
);

export const ParallaxTransition: React.FC = () => {
  const frame = useCurrentFrame();
  const linearProgress = interpolate(
    frame,
    [0, Math.max(1, DURATION_IN_FRAMES - 1)],
    [0, 1],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    },
  );
  const progress = Easing.inOut(Easing.cubic)(linearProgress);
  const anchorX = interpolate(
    progress,
    [0, 1],
    [FROM_BACKGROUND_ANCHOR.x, TO_BACKGROUND_ANCHOR.x],
  );
  const anchorY = interpolate(
    progress,
    [0, 1],
    [FROM_BACKGROUND_ANCHOR.y, TO_BACKGROUND_ANCHOR.y],
  );
  const backgroundX = -anchorX * (BACKGROUND_WIDTH - WIDTH);
  const backgroundY = -anchorY * (BACKGROUND_HEIGHT - HEIGHT);
  const foregroundTravelX =
    -Math.sign(TO_BACKGROUND_ANCHOR.x - FROM_BACKGROUND_ANCHOR.x) *
    FOREGROUND_TRAVEL;
  const foregroundTravelY =
    -Math.sign(TO_BACKGROUND_ANCHOR.y - FROM_BACKGROUND_ANCHOR.y) *
    FOREGROUND_TRAVEL;
  const fromOpacity = interpolate(linearProgress, [0.88, 1], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const toOpacity = interpolate(linearProgress, [0, 0.12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{ backgroundColor: BACKGROUND_COLOR, overflow: "hidden" }}
    >
      <Img
        src={INPUTS.background}
        style={{
          height: BACKGROUND_HEIGHT,
          left: 0,
          position: "absolute",
          top: 0,
          transform: `translate3d(${backgroundX}px, ${backgroundY}px, 0)`,
          width: BACKGROUND_WIDTH,
        }}
      />
      <Panel
        src={INPUTS.fromForeground}
        x={foregroundTravelX * progress}
        y={foregroundTravelY * progress}
        opacity={fromOpacity}
      />
      <Panel
        src={INPUTS.toForeground}
        x={-foregroundTravelX * (1 - progress)}
        y={-foregroundTravelY * (1 - progress)}
        opacity={toOpacity}
      />
    </AbsoluteFill>
  );
};
