import React from "react";
import { AbsoluteFill, Composition, Img, staticFile } from "remotion";
import { DefaultScene } from "../scenes/DefaultScene";
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

const backgroundStyle: React.CSSProperties = {
  height: BACKGROUND_HEIGHT,
  left: 0,
  position: "absolute",
  top: 0,
  transform: `translate3d(${-BACKGROUND_ANCHOR.x * (BACKGROUND_WIDTH - WIDTH)}px, ${-BACKGROUND_ANCHOR.y * (BACKGROUND_HEIGHT - HEIGHT)}px, 0)`,
  width: BACKGROUND_WIDTH,
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
