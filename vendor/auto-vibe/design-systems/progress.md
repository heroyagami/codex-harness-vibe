---
goal: |
  将每个源自网页的 design system 精简成供 claude AI 制作 React / Remotion 视频时使用的轻量品牌视觉参考。成品 `DESIGN.md` 应保留有来源依据、能改变画面结果的品牌颜色、字体、几何、影像与排版特征。

  改造流程：
  - 阅读原 `DESIGN.md`、`design-tokens.json`、`tokens.css`、预览和来源证据，区分品牌视觉 DNA 与网页实现细节。
  - 将 `DESIGN.md` 按需组织并压缩，合并相近内容，只保留取证材料支持的品牌特征。
  - 提炼 3–6 个最有辨识度的品牌信号，例如明暗关系、主色使用方式、字形气质、标志性几何、影像光线和材质。每条规则都应能改变画面结果。
  - 改造以删减、合并和字体平替落地为边界；品牌规则均须能追溯到现有取证材料。
  - 清理网页实现噪音：按钮、表单、导航、hover / focus、cookie、触控目标、响应式断点、前端框架、组件 API、网页 CTA 和组件尺寸表不进入成品文档。
  - 将网页 px / rem 字号规范改写为视频排版原则：字号由画布、镜头景别、文案长度、字幕密度和安全区共同决定；用主标题、支撑信息、技术标注之间的相对层级表达尺度。
  - 全篇使用精简、正向、可执行的语言，直接描述正确的画面选择。

  字体落地：
  - 识别 display / body / mono / CJK 等实际角色，保留品牌专有字体名作为风格参考。
  - 为无法直接使用的品牌或商业字体选择一个最接近的开源平替，优先匹配字体类别、宽度、字重覆盖和整体气质。
  - 把视频实际需要的字体文件放入该 design system 的 `fonts/`；英文与中文场景按需覆盖。
  - 在 `Typography` 中写明实际加载的字体名、本地路径、适用角色与字重；字体文件使用 OFL / Apache / MIT 等允许项目使用的授权。

  处理范围：
  - 修改范围是会提供给 claude AI 的轻量参考 `DESIGN.md` 与其 `fonts/`；其余派生文件仅作为取证来源并保持原样。
  - `DESIGN.md` 保留品牌特有信息，通用 Remotion 编程规则由场景提示链负责。

criteria: |
  - 轻量：只留下能指导画面结果的品牌规则；相近信息合并为一条，避免历史介绍和重复解释。
  - 品牌化：颜色、字体、几何与影像共同形成辨识度；强调色集中为清晰信号，主视觉承担主要叙事。
  - 排版化：文字是画面中的层级与形状；固定画布可读性、字幕共存和镜头构图优先于网页字号复刻。
  - 可落地：本地字体路径真实存在，字体可被 Remotion 加载，字重和语言覆盖与文档一致。

rule: |
  每轮只处理 `weights.json` 中尚未完成且权重最高的 1 个 design system。完成 `DESIGN.md` 精简、字体落地和自检后，将下方对应 todo 标记为完成并结束本轮。
---

## Todo Design Systems

- [x] binance
- [x] bmw
- [x] claude
- [x] duolingo
- [x] ferrari
- [x] kami
- [x] lamborghini
- [x] nvidia
- [x] openai
- [x] opencode-ai
- [x] pacman
- [x] runwayml
- [x] spotify
- [x] theverge
- [x] urdu
- [x] wechat
