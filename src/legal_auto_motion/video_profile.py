from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VideoProfile:
    name: str
    width: int
    height: int
    fps: int
    left: int
    right: int
    top: int
    content_bottom: int
    subtitle_bottom: int
    edge_guard: int

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height

    def safe_zone_prompt(self) -> str:
        return (
            f"平台UI安全线：关键主体、人物脸、数字、结论和Logo保持在 "
            f"x={self.left}..{self.right}、y={self.top}..{self.content_bottom}；"
            f"字幕不得低于 y={self.subtitle_bottom}。"
        )

    def subtitle_force_style(self, *, font_name: str = "Microsoft YaHei", font_size: int = 12) -> str:
        margin_l = self.left
        margin_r = max(0, self.width - self.right)
        margin_v = max(0, self.height - self.subtitle_bottom)
        return (
            f"FontName={font_name},FontSize={font_size},PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H90000000,BorderStyle=1,Outline=1,Shadow=0,Alignment=2,"
            f"MarginL={margin_l},MarginR={margin_r},MarginV={margin_v}"
        )


def profile_from_config(video: dict, safe_zone: dict) -> VideoProfile:
    return VideoProfile(
        name=str(video.get("profile", "custom")),
        width=int(video["width"]),
        height=int(video["height"]),
        fps=int(video["fps"]),
        left=int(safe_zone["left"]),
        right=int(safe_zone["right"]),
        top=int(safe_zone["top"]),
        content_bottom=int(safe_zone["content_bottom"]),
        subtitle_bottom=int(safe_zone["subtitle_bottom"]),
        edge_guard=int(safe_zone["edge_guard"]),
    )


CURRENT_RENDERER_PROFILE = VideoProfile(
    name="compact_3_4",
    width=1080,
    height=1440,
    fps=30,
    left=110,
    right=970,
    top=145,
    content_bottom=1000,
    subtitle_bottom=1295,
    edge_guard=60,
)

# Migration target only. The vendor renderer is not yet declared compatible with
# this profile; it exists so prompts, subtitle policy and safe-zone math can be
# exercised before the Remotion runtime is migrated.
VERTICAL_9_16_TARGET = VideoProfile(
    name="vertical_9_16_target",
    width=1080,
    height=1920,
    fps=30,
    left=90,
    right=990,
    top=180,
    content_bottom=1420,
    subtitle_bottom=1740,
    edge_guard=60,
)


def renderer_compatible(profile: VideoProfile) -> bool:
    return (profile.width, profile.height, profile.fps) == (
        CURRENT_RENDERER_PROFILE.width,
        CURRENT_RENDERER_PROFILE.height,
        CURRENT_RENDERER_PROFILE.fps,
    )
