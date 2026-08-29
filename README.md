# Codex Harness Vibe

一套可复用的 AI 动效视频生产 Harness。输入旁白音频和带时间轴的 SRT 字幕，由 Codex 负责全片理解与流程控制，Claude Code 在隔离目录中制作 Remotion 镜头，系统自动执行事实、时间、渲染、视觉、序列和合成质量门。

它不是“按关键词套卡片模板”的一键 PPT 生成器，而是一条可暂停、可审查、可返工、可断点续跑的视频生产流水线。

```text
音频 + SRT
    ↓
Codex 语义导演（完整理解文案、拆分语义镜头）
    ↓
Scene Plan + Fact Contracts + Frame Ledger
    ↓
隔离 Claude Worker（逐镜头设计并编写 Remotion）
    ↓
事实审查 + 局部时间审查
    ↓
逐镜头渲染 + 可见性检查
    ↓
Codex 三帧视觉 Critic
    ↓
不合格 → Claude 定向返工 → 重新审查与渲染
    ↓
序列联系表 + 重复布局检查
    ↓
独立转场 Worker
    ↓
旁白、字幕、镜头、转场合成
    ↓
final.mp4 + 完成报告
```

## 适用范围

- 法律科普、商业分析、知识讲解、产品介绍等无真人出镜视频；
- 已有配音与 SRT，希望自动完成语义分镜、动效制作和合成；
- 需要逐镜头返工、失败续跑和质量报告，而不是一次性生成脚本；
- 需要约束屏幕事实、数字、日期、金额和结论，减少模型编造；
- 希望复用制作判断、视觉语法和生产流程，而不是复用某一期视频的整套布局。

它不适合以实拍剪辑、复杂人物表演、口型同步或大量生成式视频素材为主的项目。

## 许可证与上游说明

本项目原创的 Harness 总控、测试和文档采用 [MIT License](LICENSE)。`vendor/auto-vibe` 是经授权修改的 auto-motion / auto-vibe 第三方生产底座，不因本仓库采用 MIT 而被重新授权；其著作权与使用条件仍归原权利人及原授权约定管辖。详情见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

案例音频、字幕、图片、字体、商标、API Key、模型账户和生成成片不因放入运行目录而自动获得 MIT 授权。公开分发前请自行确认对应素材和第三方服务条款。

## 当前成熟度

Harness 的可复用框架已经完成，以下能力已有实现：

- 完整 SRT 语义导演和精确字幕覆盖；
- 场景与转场的连续帧账本；
- 隔离 Claude 场景 Worker；
- Remotion 镜头与独立转场；
- 事实白名单和局部帧审查；
- 渲染、可见性和平台 UI 安全区检查；
- 三帧视觉 Critic、14/16 门槛和自动返工；
- 序列联系表与重复主体布局检查；
- 模型路由、调用预算、失败重试和配额阻塞状态；
- Windows pnpm 依赖联接、Remotion Chromium 缓存和 ffmpeg 合成；
- 输入或模型变化后的精确失效与断点续跑。

当前 35 项自动测试通过。框架完成不等于每一期视频自动完成：一条正式视频只有在最终文件存在、所有质量门通过并经过人工完整观看后才算交付。长视频首次生产仍可能暴露模型配额、提示遵循、素材、字体、浏览器或个别镜头审美问题。

## 系统要求

建议使用 Windows 10/11，并安装：

- Git；
- Python 3.11+ 与 Pillow；
- Node.js 和 pnpm；
- ffmpeg 与 ffprobe；
- Claude Code CLI；
- Codex CLI。

还需要为 Codex 和 Claude Code 配置可用的登录状态、模型账户或 API 代理。不要把 API Key 写入仓库。

## 安装与环境检查

```powershell
git clone https://github.com/heroyagami/codex-harness-vibe.git
cd codex-harness-vibe

.\legal-motion.ps1 doctor
```

仓库自带视频生产底座。Remotion 的 `node_modules` 不进入 Git，第一次生产时自动安装，并由各场景通过共享依赖目录复用。

`doctor` 检查 Python、Node.js、pnpm、Codex、Claude Code、ffmpeg、ffprobe、Remotion 浏览器缓存以及生产底座完整性。没有通过时不要直接开始长视频生产。

## 一条命令制作视频

准备旁白与字幕：

```text
D:\input\narration.wav
D:\input\transcription.srt
```

运行：

```powershell
.\legal-motion.ps1 produce `
  --srt "D:\input\transcription.srt" `
  --audio "D:\input\narration.wav" `
  --out "D:\output\本期视频"
```

`produce` 自动执行语义导演、场景准备、镜头生产、质量审查、返工、转场、序列检查和最终合成。重复执行相同命令会从未完成或已失效的节点继续。每期视频应使用独立输出目录，不要把运行目录放进本仓库。

### 让 Codex 代为执行

```text
根据项目 https://github.com/heroyagami/codex-harness-vibe 制作完整视频。

音频路径：D:\input\narration.wav
SRT 字幕路径：D:\input\transcription.srt
输出目录：D:\output\本期视频

使用项目现有完整 Harness。先运行 doctor，再按语义导演、隔离 Worker、事实/时间/视觉审查、自动返工、转场和最终合成的顺序执行。允许断点续跑，不要另起临时视频脚本。完成后给出最终视频路径、完成报告和所有未通过的质量门。
```

## 模型配置

配置文件为 `harness.toml`。各角色可以独立指定模型：

```toml
[models.director]
provider = "codex_text"
model = ""
fallback_model = ""

[models.scene_worker]
provider = "claude"
model = "claude-fable-5"
fallback_model = ""

[models.revision_worker]
provider = "claude"
model = "claude-fable-5"
fallback_model = ""

[models.transition_worker]
provider = "claude"
model = "claude-fable-5"
fallback_model = ""

[models.critic]
provider = "codex_images"
model = ""
fallback_model = ""
```

- `model = ""` 表示继承对应 CLI 当前默认模型；正式生产建议填写明确模型 ID；
- `fallback_model = ""` 表示不自动降级；
- 更换模型会让受影响的场景节点失效并重新执行；
- Claude 配额耗尽时记录为 `quota_blocked`，额度恢复后重复原命令即可续跑；
- 不建议在一次正式生产中频繁切换模型。

可复制一份配置并通过 `--config` 指定：

```powershell
.\legal-motion.ps1 produce `
  --srt "D:\input\transcription.srt" `
  --audio "D:\input\narration.wav" `
  --out "D:\output\本期视频" `
  --config "D:\output\harness-production.toml"
```

## 并发、返工和预算

```toml
[budget]
max_total_cost_usd = 0.0
max_model_calls = 0
max_scene_attempts = 3
max_revision_attempts = 1

[production]
scene_concurrency = 3
transition_concurrency = 2
timeout_seconds = 900
require_visual_critic = true
```

- `0` 表示不设置对应总量上限，不表示调用免费；
- 建议先用 `scene_concurrency = 1` 跑通首镜头，再提高并发；
- 不要同时对同一运行目录启动多个 Harness 实例；
- 启用美元预算时，各角色需填写可信的 `estimated_cost_usd`；
- `require_visual_critic = true` 时，读图失败或 Critic 缺失会阻止合成。

命令行可临时覆盖参数：

```powershell
.\legal-motion.ps1 produce `
  --srt "D:\input\transcription.srt" `
  --audio "D:\input\narration.wav" `
  --out "D:\output\本期视频" `
  --scene-concurrency 1 `
  --transition-concurrency 1 `
  --creative-revisions 1 `
  --timeout 1800
```

## 分阶段运行

通常只需要 `produce`。调试或人工介入时可以逐阶段执行：

```powershell
# 1. 创建隔离运行目录
.\legal-motion.ps1 new --srt "D:\input\transcription.srt" --audio "D:\input\narration.wav" --out "D:\output\本期视频"

# 2. 生成完整语义导演计划
.\legal-motion.ps1 direct --run "D:\output\本期视频"

# 3. 创建场景和转场工作区
.\legal-motion.ps1 prepare --run "D:\output\本期视频"

# 4. 制作所有场景
.\legal-motion.ps1 run-scenes --run "D:\output\本期视频"

# 仅重做指定场景
.\legal-motion.ps1 run-scenes --run "D:\output\本期视频" --scenes scene-005 scene-012 --concurrency 1

# 5. 生成联系表与序列报告
.\legal-motion.ps1 review --run "D:\output\本期视频"

# 6. 制作非硬切转场
.\legal-motion.ps1 run-transitions --run "D:\output\本期视频"

# 7. 通过所有预检后合成
.\legal-motion.ps1 assemble --run "D:\output\本期视频" --output "D:\output\本期视频\final.mp4"
```

如果 Director JSON 来自外部模型或人工审阅，可使用：

```powershell
.\legal-motion.ps1 plan-from-director --run "D:\output\本期视频" --director-plan "D:\output\director-plan.json"
```

## 完整工作流

### 1. Semantic Director

Codex 读取完整 SRT，输出每个语义镜头的 cue 范围、含义、视觉目标、视觉语法、动画过程、批准屏幕文案和前后镜头关系。系统拒绝字幕遗漏、重复覆盖、时间重叠、编造文案和长期单一视觉语法。

### 2. Isolated Scene Worker

每个场景位于独立目录，只接收本镜头的字幕、事实契约、视觉目标、设计系统和边界契约。Claude 完成 `frame.md` 和 `scenes/DefaultScene.tsx`，不负责绕过外层质量门。

### 3. Fact and Timing Gates

渲染前检查屏幕中文、数字、金额、日期、比例、案号和结论是否来自字幕或批准文案，并检查动画是否使用局部帧、是否越过 Composition 长度、全片帧账本是否连续。

### 4. Render and Visibility Gate

逐镜头检查输出存在、分辨率/帧率/帧数正确、early/mid/late 三帧有效，以及主体是否出现空画面、明显裁切、触边和层级异常。

### 5. Visual Critic and Revision Loop

Codex 必须直接读取 early、mid、late 三帧，并对以下八项各打 0–2 分：

- semantic clarity；
- visual thesis；
- information density；
- composition；
- motion purpose；
- rhythm；
- continuity；
- caption safety。

总分必须达到 14/16，且不能有 0 分。未通过时，问题交给 Revision Worker，随后重新执行事实、时间、渲染和视觉审查。没有直接帧证据时不会静默放行。

### 6. Sequence Review

联系表检查连续镜头是否出现重复主体轮廓、长期相同布局、密度单调、缺少视觉重置或存在未完成节点。单镜头合格不等于全片合格。

### 7. Transitions and Assembly

只为计划中的非硬切边界制作独立转场。最终严格按帧账本拼接，加入旁白和字幕，再用 ffprobe 写入完成报告。

## 短视频平台安全区

默认画布为 1080×1440：

- 人物脸、关键物体、数字、结论和 Logo：`x=110..970，y=145..1000`；
- 字幕保持在 `x=110..970`，字形底部不得低于 `y=1295`；
- `y=1000..1295` 主要作为字幕区；
- 背景纹理、光效和非必要装饰可以越过安全线；
- 最终字幕默认使用左右 110 px、底部 160 px 安全边距。

该规则同时进入 Worker、Critic、返工提示和最终字幕合成。

## 断点续跑

`harness-state.json` 和每个场景的 `scene-state.json` 保存输入/输出哈希、完成时间和模型信息。修改音频、SRT、Director、模型、提示或场景代码时，系统只让相关下游失效。

常见状态：

- `prepared`：工作区已准备；
- `authoring`：Worker 正在制作；
- `fact_revision`：事实或局部帧未通过；
- `creative_revision`：视觉 Critic 要求返工；
- `quota_blocked`：外部模型额度阻塞；
- `complete`：当前节点完成，不代表全片完成。

不要手工伪造状态文件。修复外部问题后重复原命令即可。

## 运行目录

```text
本期视频/
├── transcription.srt
├── narration.wav / narration.mp3
├── director-plan.json
├── scene-plan.json
├── fact-contracts.json
├── harness-state.json
├── run-state.json
├── scenes/
│   ├── scene-001/
│   │   ├── frame.md
│   │   ├── fact-contract.json
│   │   ├── scene-metadata.json
│   │   ├── scenes/DefaultScene.tsx
│   │   ├── artifacts/
│   │   ├── scene-state.json
│   │   ├── worker-state.json
│   │   └── scene-001.mov
│   └── ...
├── transitions/
├── reports/
├── sequence-review.json
├── completion-report.json
└── final.mp4
```

## 完成标准

正式视频完成至少需要：

- Director 覆盖全部字幕；
- 全部场景通过事实、时间、渲染和视觉审查；
- 序列审查无阻断项；
- 所需转场全部完成；
- `final.mp4` 存在且 ffprobe 信息正确；
- 人工从头到尾观看一次，确认听得懂、看得懂、字幕同步且无平台 UI 遮挡。

## 优点

- **可复用**：新音频与 SRT 直接创建新工程；
- **全片理解**：先理解完整文案，再拆镜头；
- **场景隔离**：失败镜头单独重做，不污染其他镜头；
- **事实安全**：法律结论、金额和日期在渲染前检查；
- **真实读图**：Critic 必须提供帧证据；
- **自动返工**：不合格镜头进入定向修改循环；
- **可恢复**：配额、渲染失败或任务中断后续跑；
- **成本可控**：模型、并发、调用次数和返工预算可配置；
- **过程透明**：代码、帧图、报告、状态和中间视频全部保留。

## 局限与缺点

- **耗时**：长视频需要逐镜头生成、渲染、读图和返工；
- **消耗额度**：高质量模型和长片会产生明显调用成本；
- **模型仍是上限**：Harness 能阻止错误，不能保证弱模型产生好审美；
- **Critic 不等于人类导演**：14/16 只是最低门槛，仍可能错判；
- **返工次数有限**：复杂镜头可能需要人工修改 `frame.md` 或代码；
- **素材能力有限**：默认偏 Remotion MG，照片、截图或生成视频需另备素材或服务；
- **环境较重**：pnpm、Chromium、ffmpeg、字体和 CLI 登录都可能成为故障点；
- **全片一致性困难**：最终人工完整观看不可取消；
- **不保证复刻特定作者**：系统复用的是导演、隔离和审查方法，不复制具体作品布局。

## 常见问题

### Claude 显示 `quota_blocked`

等待额度恢复、升级额度或切换到允许的模型，再重复原 `produce` 命令。Harness 不会把配额错误当成普通场景失败无限重试。

### E 盘出现 `.pnpm-store`

这是 pnpm 为同盘硬链接创建的共享依赖仓库，不是视频项目。保留它可避免重复下载 Remotion 依赖；删除后下次会重新下载。

### Remotion 或浏览器失败

先运行 `doctor`，确认 Chrome Headless Shell、Node/pnpm 和 ffmpeg。不要为每个场景重复安装浏览器。

### 某个镜头反复失败

检查 `worker-state.json`、`creative-critique.json`、revision request 和 early/mid/late 帧。修复后只重跑指定镜头：

```powershell
.\legal-motion.ps1 run-scenes --run "D:\output\本期视频" --scenes scene-NNN --concurrency 1
```

### 可以跳过视觉 Critic 吗

调试时 `run-scenes` 提供 `--skip-critic`，但正式合成默认 fail-closed；缺少视觉证据的镜头不应正式交付。

## 开发验证

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m unittest discover -s tests -v

.\legal-motion.ps1 doctor
```

更多资料：

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [COMPLETION-CHECKLIST.md](COMPLETION-CHECKLIST.md)

## 一句话理解

Codex Harness Vibe 是“AI 导演 + 隔离场景程序员 + 自动质量审查 + 可恢复生产状态机”的组合：它把音频和字幕变成一套可追踪、可返工的视频工程，而不是承诺任何输入都能一次生成完美成片。
