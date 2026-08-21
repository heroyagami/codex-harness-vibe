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
  DURATION_IN_FRAMES,
} from "../remotion/transition-config";

const FROM_COMPOSITE = staticFile("input/from-composite.png");
const TO_COMPOSITE = staticFile("input/to-composite.png");

export const CustomTransition: React.FC = () => {
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

  return (
    <AbsoluteFill style={{ backgroundColor: BACKGROUND_COLOR }}>
      <Img
        src={FROM_COMPOSITE}
        style={{ height: "100%", opacity: 1 - progress, width: "100%" }}
      />
      <AbsoluteFill style={{ opacity: progress }}>
        <Img src={TO_COMPOSITE} style={{ height: "100%", width: "100%" }} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
