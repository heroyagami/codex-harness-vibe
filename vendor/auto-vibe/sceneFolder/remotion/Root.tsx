import React from "react";
import { AbsoluteFill, Composition, Img, staticFile } from "remotion";
import { DefaultScene } from "../scenes/DefaultScene";
import { coverBackgroundGeometry } from "./background-geometry";
import {
  BACKGROUND_ANCHOR,
  BACKGROUND_COLOR,
  BACKGROUND_HEIGHT,
  BACKGROUND_IMAGE,
  BACKGROUND_WIDTH,
  DURATION_IN_FRAMES,
  FPS,
  HEIGHT,
  WIDTH,
} from "./scene-config";

export const COMPOSITION_ID = "default";
export const FOREGROUND_COMPOSITION_ID = "foreground";

const geometry = coverBackgroundGeometry({
  sourceWidth: BACKGROUND_WIDTH,
  sourceHeight: BACKGROUND_HEIGHT,
  canvasWidth: WIDTH,
  canvasHeight: HEIGHT,
  anchor: BACKGROUND_ANCHOR,
});

const backgroundStyle: React.CSSProperties = {
  height: geometry.height,
  left: geometry.left,
  maxWidth: "none",
  position: "absolute",
  top: geometry.top,
  width: geometry.width,
};

const BackgroundPlate: React.FC = () => (
  <Img src={staticFile(BACKGROUND_IMAGE)} style={backgroundStyle} />
);

const CompositeScene: React.FC = () => (
  <AbsoluteFill
    style={{ backgroundColor: BACKGROUND_COLOR, overflow: "hidden" }}
  >
    <BackgroundPlate />
    <DefaultScene />
  </AbsoluteFill>
);

const ForegroundScene: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: "transparent" }}>
    <DefaultScene />
  </AbsoluteFill>
);

export const Root = () => (
  <>
    <Composition
      id={COMPOSITION_ID}
      component={CompositeScene}
      durationInFrames={DURATION_IN_FRAMES}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
    />
    <Composition
      id={FOREGROUND_COMPOSITION_ID}
      component={ForegroundScene}
      durationInFrames={DURATION_IN_FRAMES}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
    />
  </>
);
