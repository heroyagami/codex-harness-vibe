import React from "react";
import { Composition } from "remotion";
import { CustomTransition } from "../scenes/CustomTransition";
import { ParallaxTransition } from "../scenes/ParallaxTransition";
import {
  DURATION_IN_FRAMES,
  FPS,
  HEIGHT,
  TRANSITION_TYPE,
  WIDTH,
} from "./transition-config";

export const COMPOSITION_ID = "default";
const TransitionComponent =
  TRANSITION_TYPE === "parallax" ? ParallaxTransition : CustomTransition;

export const Root = () => (
  <Composition
    id={COMPOSITION_ID}
    component={TransitionComponent}
    durationInFrames={DURATION_IN_FRAMES}
    fps={FPS}
    width={WIDTH}
    height={HEIGHT}
  />
);
