---
visual_theme: dark
---

读取当前目录的 `transcription.srt`，规划 MG 或 cinematic + MG 场景，并根据叙事与节奏为每个场景边界选择硬切或独立转场；按编号运行 `./scenes/scene-NNN/run-claude-ai.sh`，交给 claude 实现场景；用 codex subagent 制作需要独立渲染的转场，最终交付完整动效视频。存在 `full-script.md` 时用它理解上下文。

# Research 与素材

通读字幕，联网搞明白专有名词和专业概念（包括但不限于人物、机构、产品、品牌、论文等）。把事实定义、关键结论、关系和出处线索写入 `resources/research.md`。专业概念若有，要补充 1–2 个代表性实例及依据。

Research 过程中同时收集视觉素材，包括但不限于专业名词和代表性实例的logo、网络参考图片等；也可使用 imagegen 补充素材。人物处境与情绪、环境氛围、物理过程、材质变化或空间尺度需要连续镜头表达时，交给 claude 尝试 omni-video，并把生成片段作为镜头主体或素材层与 MG 合成；概念结构、步骤、比较、数据与精确文字用可控 MG 组织。`resources/research.md` 只承载事实研究，是后续给scene通过research_brief传递分镜所需要的专业知识，而画面方案留给claude自行设计。

# 场景与转场计划

每个场景承载一个完整语义段落，可包含多条相邻字幕。话题或叙事任务发生实质转换、且需要重建主要视觉结构时再开新场景；同一表达的列举、补充条件、参数说明和连续步骤归入同一场景。一句话完整归入一个场景。按此拆分 N(>=1) 个场景，把详细计划写入 `scene-plan.json`：

```json
{
  "fps": 30,
  "total_duration_seconds": "5.500",
  "scenes": [
    {
      "time_range_seconds": ["0.000", "3.250"],
      "subtitle_text": "00:00:00,000 --> 00:00:01,500\n介绍评测对象\n00:00:01,500 --> 00:00:03,000\n补充参与模型",
      "research_brief": "无额外补充",
      "image_resources": []
    },
    {
      "time_range_seconds": ["3.250", "5.500"],
      "subtitle_text": "00:00:03,500 --> 00:00:05,500\n转入结果展示",
      "research_brief": "无额外补充",
      "image_resources": []
    }
  ],
  "transitions": [
    {
      "type": "parallax",
      "time_range_seconds": ["2.750", "3.750"],
      "reason": "用前后景位移延续空间动势，保持讲解连贯"
    }
  ]
}
```

## 时间轴

- `time_range_seconds` 是场景的内容归属区间，使用绝对 SRT 秒数。所有场景连续覆盖第一条字幕开始到最后一条字幕结束；`total_duration_seconds` 精确等于两者之差。
- `subtitle_text` 按原顺序完整分配每个 cue，保留绝对时间轴和正文，移除序号。纯静默场景可用空字符串。校验器会核对时间、正文、顺序和唯一性。
- `transitions` 按场景边界排列，数量固定为 `N - 1`。每项选择 `type: hard_cut`、`type: parallax` 或 `type: custom`，并用 `reason` 写明语义与节奏依据。
- 明确的章节转换、对比、重击或快速节拍使用 `hard_cut`，在场景边界直接切换，写作 `{"type": "hard_cut", "reason": "..."}`。
- 需要动效承接时默认使用 `parallax`，以共享背景和透明前景的差速运动延续空间动势。素材本身存在明确的形态呼应、遮挡关系、运动方向或状态变化时，可使用 `custom`，采用匹配剪辑、遮罩、擦除、推拉、形变、材质变化等对应机制。
- `parallax` 和 `custom` 的 `time_range_seconds` 是原时间轴内跨越场景边界的独立替换片段。时长按该边界的实际停顿与内容节拍逐段确定，各段可不同；优先容纳字幕静默区，再向两侧取用时间。全片总时长保持不变。
- 所有秒边界统一映射到全局 30fps 帧边界。脚本派生场景帧数、转场帧数和最终拼接顺序。

`image_resources` 只写前景素材的 `source` 与 `target`。共享背景和场景锚点由脚本按主题与场景编号派生。

完成计划后运行：

```bash
/usr/local/bin/python3 scene_plan.py scene-plan.json
./prepare-scenes.sh scene-plan.json
```

准备脚本会创建：

- `scenes/scene-NNN/`：claude 的独立 Remotion 场景目录，包含固定帧数、共享背景裁窗，以及动效转场边界所需的首/末帧交接契约。
- `transitions/transition-NNN/`：每个 `parallax` 或 `custom` 边界的独立 Remotion 工作目录。

# 流水调度

按编号串行运行 `./scenes/scene-NNN/run-claude-ai.sh`，交给 claude 实现各 MG 场景。遇到 `parallax` 或 `custom` 边界时，相邻两个场景均完成并生成 `artifacts/scene-manifest.json` 后，立即准备对应转场输入并派生 codex subagent：

```bash
./stage-transition.sh scene-plan.json transition-NNN
```

让 subagent 仅在 `transitions/transition-NNN/` 工作，遵循其中的 `transition-prompt.md`，依据 `reason` 自主设计转场，渲染并验证 `transition-NNN.mov`；相邻场景作为只读输入。subagent 启动后，你继续运行下一个 claude 场景，使转场与后续场景流水并行。可用槽不足时按边界顺序排队。`hard_cut` 由最终拼接流程在场景边界直接完成。

运行 claude 时以 `yield_time_ms=30000` 启动 `./run-claude-ai.sh >/dev/null` 并保留原会话。另开消息等待会话，以 `yield_time_ms=30000` 运行 `./run-claude-ai.sh --wait-message N`（N 从 1 递增）。只轮询消息等待会话：仍在等待时，以空 `write_stdin` 和 `yield_time_ms=300000` 续等；收到第 N 条消息后，内容包含“claude 进程已结束”时回收原会话并停止等待，否则 N++ 后重开。300 秒空返回的唯一动作是立即续等；每 3 次检查一次日志修改时间和 claude/渲染进程，原会话已结束且第 N 行未产生时结束消息等待会话并报告异常。仅在新阶段、claude 结束或异常时更新用户。阶段进度只取消息等待会话 stdout；`claude-scene-*.stream.jsonl` 只查看修改时间与大小。

# 交付

等待全部场景和动效转场完成，运行：

```bash
./assemble-video.sh scene-plan.json
```

脚本按派生时间线拼接并校验 H.264 MOV、1080×1440、30fps、无音轨和实际帧数。最后运行 `./rename-workspace.sh`，把当前目录重命名为 `<前5个字幕文本字符>-<小时>-<分钟>`。
