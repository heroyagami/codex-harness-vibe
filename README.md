# Codex Harness Vibe

可复用的 AI 动效视频生产 Harness：

`音频 + SRT → Codex 语义导演 → Claude 隔离场景 Worker → Remotion → 事实/时间/视觉审查 → 自动返工 → 转场 → 字幕音频合成`

## 新电脑直接使用

```powershell
git clone https://github.com/heroyagami/codex-harness-vibe.git
cd codex-harness-vibe

.\legal-motion.ps1 doctor
```

仓库已经自带完整生产底座，不需要再次下载。只有主动同步购买源码的新版本时，先备份并移除本地 `vendor` 与 `.private`，再运行：

```powershell
.\setup.ps1 -Ref "提交号或分支名"
```

安装要求：Git、Python 3.11+、Node.js、pnpm、ffmpeg、Claude Code、Codex CLI。Python 环境需安装 Pillow；Remotion 的 `node_modules` 会在第一次生产时自动安装，不进入 GitHub。

## 制作视频

下次可以直接把下面这段话发给已经连接本私有 GitHub 的 Codex：

```text
根据私有项目 https://github.com/heroyagami/codex-harness-vibe 制作完整视频。

音频路径：D:\input\narration.wav
SRT 字幕路径：D:\input\transcription.srt
输出目录：D:\output\本期视频

使用项目现有完整 Harness 流程，先运行 doctor，再按语义导演、隔离 Worker、事实/时间/视觉审查、自动返工、转场和最终合成的顺序执行。允许断点续跑；不要另起一套临时视频脚本。完成后给出最终视频路径和未通过的质量门。
```

如果 Codex 运行在另一台电脑或云端，需要先确认它已经获得这个私有仓库的访问权限。

也可以在本机直接运行：

```powershell
.\legal-motion.ps1 produce `
  --srt "D:\input\transcription.srt" `
  --audio "D:\input\narration.wav" `
  --out ".\runs\本期视频"
```

重复执行同一命令会从未通过或已经过期的节点续跑。更换字幕、音频、Worker 模型或 Critic 模型时，系统按输入哈希只让相关下游失效。

## 当前完成度说明

- 不是这一次从零开始、短时间内开发出整套系统；主要框架是在此前多轮、长时间开发中逐步完成的。
- 本次工作完成的是：核对购买源码、补齐模型路由/预算/状态机/Critic、修复续跑边界、整理私有融合仓库并完成发布。
- 当前 32 项自动测试、离线最小流程、环境检查和私有底座完整性检查通过。
- 私有融合版本尚未重新消耗大量额度跑完一条完整长视频。第一次正式视频仍属于生产验收，可能暴露模型效果、第三方配额或具体素材导致的问题；不能把单元测试通过等同于“任何文案都必然一次生成参考级成片”。
- 正式视频只有在成片文件存在、全部质量门通过并经人工完整观看后，才算该期视频完成。

## 模型和预算

编辑 `harness.toml`：

- Director 默认由 Codex 完整读取 SRT；
- 场景和转场默认由 Claude Code 在隔离目录中制作；
- `model = ""` 表示沿用工具当前默认模型；
- `fallback_model` 可设置失败后升级的强模型；
- `max_model_calls` 限制调用次数；
- `max_total_cost_usd` 启用时，每个角色必须填写 `estimated_cost_usd`。

## 质量门

- Director 必须完整覆盖字幕，不能遗漏、重叠或编造屏幕文案；
- 场景渲染前通过事实白名单与局部时间轴审计；
- 渲染后检查空画面、越界、字幕安全区；
- Critic 必须直接读取 early/mid/late 三帧，达到 14/16 且无 0 分；
- 无法读图、缺少证据或关闭 Critic 时，正式合成失败；
- 序列审查拒绝连续三个高度相似的主体布局。

更多说明见 [ARCHITECTURE.md](ARCHITECTURE.md) 和 [COMPLETION-CHECKLIST.md](COMPLETION-CHECKLIST.md)。
