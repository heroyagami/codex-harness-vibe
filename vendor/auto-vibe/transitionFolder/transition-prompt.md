---
transition_id: AUTO
transition_type: AUTO
output_file: AUTO
fps: 30
frame_range: AUTO
time_range_seconds: AUTO
duration_in_frames: AUTO
visual_theme: AUTO
from_scene_id: AUTO
to_scene_id: AUTO
from_background_anchor: AUTO
to_background_anchor: AUTO
reason: AUTO
subtitle_context: AUTO
---

制作当前独立转场片段。相邻场景已完成并通过交接素材校验，标准化输入位于 `public/input/`。

1. 查看两张 `*-composite.png` 和透明前景，结合 `reason`、`subtitle_context` 判断前后语义、主体关系与节奏落点。
2. `transition_type: parallax` 时使用 `scenes/ParallaxTransition.tsx`，让共享背景按场景锚点移动、透明前景以更大位移形成清晰差速。`transition_type: custom` 时在 `scenes/CustomTransition.tsx` 实现一个与素材关系对应的视觉机制。
3. 第 0 帧准确呈现 `from-composite.png`，第 `duration_in_frames - 1` 帧准确呈现 `to-composite.png`；中间过程可组合完整画面、透明前景和共享背景，让动作服务语义并保持主体可辨识。
4. 保持 `duration_in_frames`、30fps 和 1080×1440 技术规格。全部帧由 `useCurrentFrame()` 确定，运动在首尾稳定收束。
5. 依赖由脚手架预装。运行 `pnpm run verify`、`pnpm run remotion:render`、`pnpm run render:verify`，交付当前 `output_file`。相邻场景目录作为只读参考，全部改动留在当前转场目录。

完成时报告实现选择、首尾衔接检查和实际帧数。
