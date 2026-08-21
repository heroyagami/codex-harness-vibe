export const TRANSITION_ID = "transition-template";
export const TRANSITION_TYPE: "parallax" | "custom" = "parallax";
export const FPS = 30;
export const WIDTH = 1080;
export const HEIGHT = 1440;
export const DURATION_IN_FRAMES = 30;
export const VISUAL_THEME = "dark" as const;
export const BACKGROUND_IMAGE = "input/background.png";
export const BACKGROUND_WIDTH = 1480;
export const BACKGROUND_HEIGHT = 1840;
export const FOREGROUND_TRAVEL = 1200;
export const BACKGROUND_COLOR = "#08090b";
export const FROM_FOREGROUND_IMAGE = "input/from-foreground.png";
export const TO_FOREGROUND_IMAGE = "input/to-foreground.png";
export const FROM_BACKGROUND_ANCHOR = {
  name: "top_left",
  x: 0,
  y: 0,
} as const;
export const TO_BACKGROUND_ANCHOR = {
  name: "top_right",
  x: 1,
  y: 0,
} as const;
