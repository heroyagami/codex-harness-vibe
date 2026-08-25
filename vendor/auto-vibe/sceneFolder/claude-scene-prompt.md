---
scene_id: AUTO
output_file: AUTO
fps: 30
timeline_origin_seconds: AUTO
frame_range: AUTO
render_range_seconds: AUTO
duration_in_frames: AUTO
visual_theme: AUTO
background_image: AUTO
background_anchor: AUTO
transition_handles: AUTO
boundary_contract: |-
  AUTO
subtitle_text: |-
  TODO: 保留本场景字幕的 SRT 时间轴和正文，移除序号行。
research_brief: |-
  TODO: 本场景必要的事实和当前目录内的素材路径。
---

根据以上文案制作一个以 MG 为骨架的动画场景；需要真实时间、空间或情绪表演时，可用 omni-video 创作 cinematic 镜头或视频素材，再与 MG 合成。当前目录是初始化好的 Remotion 项目。

先把字幕转译成观众能瞬间感受到的具体画面，确定一个情绪目标和一个主视觉。根据 `subtitle_text` 的绝对时间判断本场景是否位于全片开头；首幕负责建立全片的视觉期待，给予最高视觉优先级，优先让 1–2 个意象以完整大图或特写主导画面。让主意象占据主要画幅，从尺度、景别、构图、明暗和运动中选择 1–2 项形成张力；人物处境与情绪优先用具体的人物或环境图像承载，MG 围绕主体动作、视线、轮廓与留白强化含义和节拍。语义中心改变时同步更换画面主角：人物群像可用若干有辨识度的完整大图快闪，抽象名词可化为独立占屏的物体或机制特写。文字、卡片和装饰作为次级标注。画面若需展示来源，只写 GitHub 仓库名或路径（如 `vibe-motion/auto-motion`），域名、网址等引流信息统一隐去。生成图片时先提出内容特有的视觉概念，再明确主体状态、景别与镜头、构图、光影、材质和留白，使每张图足以独立成为一个镜头。

## 镜头判断

先写一句镜头意图：观众起初看到或感到什么，结尾发现什么。人物处境与情绪、环境氛围、物理过程、材质变化和空间尺度适合 cinematic 镜头；概念结构、步骤、比较、数据和精确文字适合 MG。cinematic 场景可用 omni-video 创作单一连续镜头，也可生成局部视频 plate，再用 MG 标注、遮罩、跟随和强调。

景别定义观众距离：远景建立处境与尺度，中景承载动作与关系，特写锁定情绪或证据。镜头运动服务认知变化：推近聚焦或加压，拉远揭示环境或孤立，横移跟随因果，升降揭示尺度，固定镜头形成凝视。每个短镜头设置一个主体动作、一个主相机运动和一个清晰落点；运动在语义落点前稳定收束。

## 时间与交接

- `duration_in_frames` 是 `default` Composition 的固定帧数。
- 当前本地帧对应的全片绝对时间为：`timeline_origin_seconds + (frame_range[0] + useCurrentFrame()) / fps`。用它对齐 `subtitle_text` 的绝对 SRT 节拍。
- `boundary_contract` 只约束首帧或末帧的交接主体；其余画面与动画按本场景内容独立设计。
- 场景动画稳定收束到 `boundary_contract` 定义的边界状态，为相邻场景的独立转场提供清晰交接。
- `transition_handles.entry/exit` 为 `true` 时，交付流程会从同一个前景组件导出透明前景和完整画面边界帧。

## 制作流程

1. 阅读字幕、research 补充、`public/img/` 和 `public/video/` 中的素材。`research_brief` 提供事实上下文、视觉重点与素材路径。缺失的必要图片用 image-gen 生成到 `public/img/`；需要 cinematic 表达时，按 omni-video 指引生成到 `public/video/`，优先使用 9:16 并让关键动作保持在居中的 3:4 安全画幅内。选用或生成素材后，确认主体、动作、朝向、表情、留白和可叠加区域，据此确定裁切、`object-position` 与 MG 锚点；图片使用 kimi-img-viewer，视频抽取起始、转折和落点帧合成联系表后查看。
2. 补全 `frame.md`，先写镜头意图，再明确视觉意象、主次层级、关键节拍、元素与字幕同步；使用视频时同时记录素材路径、入出点、3:4 裁切和 MG 锚点。`design-system/` 中有文件夹时，读取其中的 `DESIGN.md` 并采用该视觉规范；没有时，根据本场景内容自定视觉语言。`visual_theme: light` 时，可将合适的设计系统适度转译为编辑拼贴，以拟物阴影、拼贴白边等强化前景在浅色复古报纸上的层级与可读性。用缩略静帧自检：主意象一眼可认，文案转折对应一次明确的视觉变化，图片或视频拥有镜头级面积，前景在共享背景上对比清晰。随设计系统提供的字体位于 `public/fonts/`。
3. 在 `scenes/DefaultScene.tsx` 实现画面，未覆盖区域保留 Alpha，元素自身按设计呈现。视频层用 `OffthreadVideo` 与 `staticFile()`，以 `trimBefore` / `trimAfter` 对齐帧段并设为 `muted`，用 `objectFit` / `objectPosition` 完成安全裁切；让 MG 对齐稳定、可辨识的画面特征或留白区，并在主体动作之后落版。短视频平台 UI 安全线按 1080×1440 画布固定为 x=110..970、y=145..1295；人物脸、数字、结论、Logo、字幕和其他关键内容不得越线，主画面关键主体优先保持在 y<=1000，只有背景纹理与非必要装饰可越线。主视觉坐标独立于 `background_anchor`，以内容安全区中心为基准；场景壳按 `background_anchor` 展示共享纹理远景。`AbsoluteFill` 默认 `flexDirection: "column"`；使用 `alignItems` 或 `justifyContent` 时显式声明主轴，`column` 的水平居中用 `alignItems: "center"`，`row` 的水平居中用 `justifyContent: "center"`。用同一前景组件生成完整画面与带 Alpha 的前景边界帧。保留 `remotion/Root.tsx` 和 `remotion/scene-config.ts` 的合成与时长契约。
4. 依赖由脚手架预装。依次运行 `pnpm run verify`、`pnpm run remotion:render` 和 `pnpm run render:verify`，输出并校验当前 `output_file`；通过后立即汇报 `[[USER_MESSAGE]]候选视频已通过技术校验`。
5. 首个通过 `render:verify` 的 MOV 作为候选成片。视觉复核总预算为 1 轮：抽取首个内容稳定帧、语义转折帧和末帧时，必须使用 `node scripts/remotion-cli.mjs still default <输出路径> --frame=<帧号>`；禁止使用 `npx remotion`、`pnpm exec remotion` 或直接调用 `node_modules/.bin/remotion`，以确保复用共享 Chrome。将静帧合成一张联系表，只调用一次 kimi-img-viewer。阻断项限定为主视觉或事实错误、关键信息不可读、明显裁切或重叠、边界状态不符合 `boundary_contract`；无阻断项即确认候选成片。视觉复核最多触发 1 次集中修正并重跑第 4 步，技术命令失败则按报错修复；完成后汇报 `[[USER_MESSAGE]]单轮视觉复核完成`。
6. 最终 MOV 确认后，当任一 `transition_handles` 为 `true` 时，运行一次 `pnpm run transition-handles:render`，生成并校验 `artifacts/scene-manifest.json`、带 Alpha 的前景边界帧和完整画面参考帧。

## 阶段汇报

阶段消息通过 `SendUserMessage` 实时转发给用户。每完成一个阶段、遇到困难或单阶段超过 5 分钟时，立即调用一次：`message` 只放一行 `[[USER_MESSAGE]]...`，`status` 使用 `normal`。调用成功后继续任务。

示例：

[[USER_MESSAGE]]需求和素材理解完成
[[USER_MESSAGE]]画面方案已确定
[[USER_MESSAGE]]开始实现
[[USER_MESSAGE]]开始视频渲染
[[USER_MESSAGE]]候选视频已通过技术校验
[[USER_MESSAGE]]单轮视觉复核完成
[[USER_MESSAGE]]视频与交接素材渲染完成
