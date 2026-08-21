param(
    [string]$Upstream = "https://github.com/sxhzju/auto-motion.git",
    [string]$Ref = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$privateRoot = Join-Path $projectRoot ".private"
$upstreamRoot = Join-Path $privateRoot "sxhzju-auto-motion"
$vendorRoot = Join-Path $projectRoot "vendor\auto-vibe"

if (Test-Path -LiteralPath $vendorRoot) {
    Write-Host "底座已经安装：$vendorRoot"
    Write-Host "如需更新，请先备份并手动移除 vendor 与 .private 后重新运行。"
    exit 0
}

New-Item -ItemType Directory -Path $privateRoot -Force | Out-Null
if (-not (Test-Path -LiteralPath $upstreamRoot)) {
    git clone --depth 1 $Upstream $upstreamRoot
}
if ($Ref) {
    git -C $upstreamRoot fetch --depth 1 origin $Ref
    git -C $upstreamRoot checkout --detach FETCH_HEAD
}

$upstreamVibe = Join-Path $upstreamRoot "auto-vibe-"
if (-not (Test-Path -LiteralPath $upstreamVibe)) {
    throw "授权源码中未找到 auto-vibe-：$upstreamVibe"
}

New-Item -ItemType Directory -Path (Split-Path $vendorRoot -Parent) -Force | Out-Null
Copy-Item -LiteralPath $upstreamVibe -Destination $vendorRoot -Recurse

$env:PYTHONPATH = Join-Path $projectRoot "src"
python (Join-Path $projectRoot "scripts\generate_brand_assets.py") --vendor $vendorRoot

Write-Host "安装完成。下一步运行："
Write-Host ".\legal-motion.ps1 doctor"

