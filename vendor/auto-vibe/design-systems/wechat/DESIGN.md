# WeChat Visual Style Reference

> Category: Social & Messaging
> A quiet, mobile-native social style built around WeChat green, soft chat grays, simple surfaces, and CJK-aware system typography.

## Core Look

WeChat should feel familiar, calm, and utility-first: a light consumer canvas where one decisive green signal carries brand recognition. The visual language is understated rather than loud. Let white, soft gray, dark ink, and WeChat green do most of the work.

Use the muted chat-list gray as the default environmental color, with lighter surfaces and white message bubbles layered above it. Green marks sent, paid, confirmed, active, or connected states.

## Color Roles

- **Background**: `#ededed` for the recognizable WeChat chat-list canvas.
- **Surface**: `#f7f7f7` for quiet light layers.
- **Incoming bubble / white surface**: `#ffffff`.
- **Outgoing bubble**: `#95ec69`.
- **Primary text**: `#1a1a1a`.
- **Muted text / timestamps**: `#888888`.
- **Border / divider**: `#e0e0e0`, used quietly.
- **Accent**: WeChat green `#07c160`.

## Typography

- **Display / body**: `-apple-system`, `BlinkMacSystemFont`, `"PingFang SC"`, `"Hiragino Sans GB"`, `"Microsoft YaHei"`, `"Noto Sans SC"`, `"Helvetica Neue"`, `Helvetica`, `Arial`, sans-serif.
- **Mono**: `ui-monospace`, `"SF Mono"`, `"JetBrains Mono"`, `Menlo`, `Monaco`, `Consolas`, monospace.
- **Local substitutes**: use `Noto Sans SC` for the PingFang SC / Microsoft YaHei-style CJK UI voice via `fonts/NotoSansSC.ttf`, and `JetBrains Mono` for mono text via `fonts/JetBrainsMono.ttf`. These Google Fonts files are OFL-licensed and cover the practical regular-to-bold weights needed for Remotion scenes.
- Keep typography compact, neutral, and readable. The style should feel like mobile chat, payments, and mini programs rather than editorial branding.
- Chinese text should render cleanly with PingFang SC, Microsoft YaHei, or Noto Sans SC fallbacks.
- Titles can be slightly heavier than body text.

## Visual Traits

- Favor light gray app canvases, white bubbles, pale panels, and restrained dividers.
- Use WeChat green as the main recognition cue for action, success, payment, sent status, active state, and confirmation.
- Message-like compositions can pair `#95ec69` outgoing bubbles with white incoming bubbles.
- Rounded mobile geometry is appropriate, especially for chat bubbles, avatars, pills, and confirmation elements.
- Keep secondary information quiet with muted gray rather than extra color.
- The overall feel should be practical, trustworthy, and conversational.
