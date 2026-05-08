# PhotoDateRescue

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Platform: macOS | Windows core](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows%20core-black.svg)
![Language: Python](https://img.shields.io/badge/Language-Python-3776AB.svg)

一键修复安卓迁移到 iPhone / Apple Photos 后错乱的照片时间线，安全生成可导入的副本。

它会扫描本地导出的媒体目录，分析照片和视频中的时间信息，并生成修复后的安全副本。原始文件不会被修改，也不会自动写入 Apple Photos 或 iCloud。

主要面向安卓手机先导出到电脑，再由本工具处理，最后手动导入 Apple Photos / iCloud 的场景。macOS 是优先验证平台；Windows 支持核心的扫描、报告、普通照片 / 视频修复和 `adb` 导出流程；Windows 不承诺生成 Apple Photos 可识别的 Live Photo。

## Features

- 中文向导 `photodaterescue wizard`，适合普通用户直接上手。
- 扫描、报告、修复、对账、安卓动态照片排查一条线完成。
- 默认只生成安全副本，不修改源文件。
- Windows 核心流程可用：扫描、修复、报告、安卓导出；普通照片和视频是 Windows 支持重点。
- 支持安卓 Motion Photo 审计、提取和跨平台配对包；Apple Live Photo 元数据写入仅在 macOS + `makelive` 路径下验证。
- 支持 Live Photo 元数据只读检查，可批量判断配对关系是否已经具备 Apple 常见识别信号。

## 适用场景

- 安卓手机迁移到 iPhone 后，部分照片显示成错误导入日期。
- 微信、QQ、下载图、截图等外部来源图片时间线混乱。
- 部分视频缺少 Apple Photos 能识别的创建时间。
- 想从安卓 Motion Photo 中尽量拆出静态图和短视频配对；如需 Apple Live Photo，优先使用 macOS 路径。
- 想先生成报告、人工确认，再决定是否导入相册。

## 核心能力

- 扫描照片 / 视频目录并生成结构化报告。
- 为照片和视频生成修复后的副本，不改动源文件。
- 识别伪装后缀，例如 `.jpg` 实际是 `PNG`、`WEBP`、`HEIC`。
- 优先使用媒体内嵌时间，缺失时回退到文件修改时间和创建时间。
- 支持常见安卓缓存、回收站、缩略图目录过滤。
- 支持通过 `adb pull -a` 导出安卓媒体目录并尽量保留文件时间。
- 支持安卓 Motion Photo 审计、提取与跨平台配对包；macOS 可选生成 Apple Live Photo 兼容输出。
- 动态照片按来源格式识别：Apple 元数据、Android Motion Photo / MicroVideo 标记、小红书 sidecar 配对等会分别报告，不简单按手机品牌混在一起。
- 提供中文终端向导 `photodaterescue wizard`，适合不想手写长命令的用户。

## 一键使用

安装完成后，普通用户只需要运行：

```bash
photodaterescue doctor
photodaterescue wizard
```

`wizard` 是推荐入口。它会用中文一步步引导你选择原始媒体目录、输出目录、扫描报告、修复副本和 Live Photo 救援选项。

## macOS 小白图形界面

如果你不想使用终端，可以使用实验性的 macOS 图形界面。第一版 GUI 聚焦普通照片 / 视频时间线修复：

- 选择安卓照片 / 视频导出文件夹
- 选择安全输出文件夹
- 先扫描并查看摘要
- 再生成修复后的安全副本

GUI 不会自动导入 Apple Photos，不会删除原图。高级动态照片 / Live Photo 工作流仍建议使用 CLI。

小白使用指南见 [`docs/manual/macos-gui-beginner-guide.md`](docs/manual/macos-gui-beginner-guide.md)。

开发者可通过 `photodaterescue-gui` 从源码启动 GUI；维护者可用 `scripts/build-macos-app.sh` 构建本地 `.app`，详细打包说明见 [`docs/packaging/macos-gui.md`](docs/packaging/macos-gui.md)。

## 使用流程

1. 先把安卓手机里的照片和视频导出到 Mac 上的普通文件夹。
2. 运行 `photodaterescue doctor` 检查环境。
3. 运行 `photodaterescue wizard` 按向导完成扫描和修复。
4. 先检查输出结果，确认时间线正确。
5. 再把修复后的副本手动导入 Apple Photos。

默认输出结构：

```text
PhotoDateRescue-output/
  scan-report/
  repaired-media/
  live-work/
  live-output/
```

## 安全原则

PhotoDateRescue 默认按“先保护数据，再修复时间线”的方式工作：

- 不修改源文件。
- 不自动导入 Apple Photos / iCloud。
- 不自动删除重复项。
- 所有修复结果写入你指定的输出目录。
- 高风险文件会进入报告，建议人工确认后再处理。

## 支持范围

当前支持：

- 图片：`jpg`、`jpeg`、`png`、`webp`、`heic`、`heif`
- 视频：`mp4`、`mov`、`m4v`、`3gp`
- 平台：macOS 优先；Windows 支持核心扫描 / 修复 / 报告 / `adb` 导出流程
- Windows 支持普通照片和视频修复；动态照片在 Windows 上只做到审计、提取和配对包，不承诺 Apple Photos 识别为 Live Photo。
- 普通照片和视频修复逻辑尽量使用通用元数据，其他安卓设备理论上可用。
- Motion Photo / Live Photo 恢复需要更多真实样本验证，不承诺覆盖所有品牌私有格式。
- 已针对小红书保存的 `Camera_XHS_*` + `xhs_live_photo_*` sidecar 结构做配对识别；可识别带 Xiaomi 机型信息和 `MicroVideo` / `MotionPhoto` 标记的小米原生相机嵌入式动态照片候选，并已在 macOS + `makelive` 下完成小样本元数据写入验证。

暂不承诺：

- 直接写入 Apple Photos / iCloud
- 自动删除重复照片
- `gif`
- HEIC / AVIF 嵌入式动态照片提取
- Windows 上构建 Apple Photos 可识别的 Live Photo
- 所有安卓品牌的 Motion Photo / Live Photo 私有格式恢复

## 安装

### macOS

```bash
git clone https://github.com/Teddy-creator/PhotoDateRescue.git
cd PhotoDateRescue

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

运行扫描或修复前，需要安装 `exiftool`。如果要处理视频，也建议安装 `ffmpeg`：

```bash
brew install exiftool ffmpeg
```

如果要构建 Apple Live Photo 兼容输出，还需要安装 `makelive`：

```bash
uv tool install makelive
```

也可以参考 [`makelive` releases page](https://github.com/RhetTbull/makelive/releases) 安装预编译包。

### Windows 核心流程

Windows 目前建议先使用核心流程：扫描、报告、普通照片 / 视频修复、`adb` 导出。动态照片可做审计、提取和跨平台配对包；Apple Photos 可识别的 Live Photo 构建不属于 Windows 支持范围。

```powershell
git clone https://github.com/Teddy-creator/PhotoDateRescue.git
cd PhotoDateRescue

py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

Windows 还需要准备：

- ExifTool：下载 Windows 版 `exiftool.exe`，并加入 `PATH`。
- FFmpeg：推荐用 `winget` / `choco` / `scoop` 安装，或手动把 `ffmpeg.exe`、`ffprobe.exe` 加入 `PATH`。
- Android Platform-Tools：如果要从安卓手机导出媒体，把 `adb.exe` 加入 `PATH`。

检查环境：

```powershell
photodaterescue doctor
photodaterescue wizard
```

## 快速开始

大多数情况下，直接使用向导即可：

```bash
photodaterescue doctor
photodaterescue wizard
```

向导会引导你完成：

- 选择安卓导出的原始媒体目录
- 选择安全输出目录
- 应用常见缓存目录排除规则
- 先扫描并生成报告
- 按需生成修复后的照片 / 视频副本
- 按需排查安卓动态照片；macOS 下可选生成 Live Photo 兼容输出

如果你不确定应该选什么，优先选择向导里的推荐流程。Windows 下向导会跳过 Apple Live Photo 构建，只处理普通照片 / 视频时间线；动态照片可通过高级命令保留为静态图 + 短视频配对包。

## 高级用法

### 从安卓设备导出媒体

```bash
photodaterescue android-pull \
  --device-path /sdcard/DCIM \
  --device-path /sdcard/Pictures \
  --device-path /sdcard/Movies \
  --output /path/to/android-export
```

`android-pull` 内部使用 `adb pull -a`，这对微信、QQ 等来源的视频很重要，因为它们可能没有可靠的内嵌时间，只能依赖文件修改时间。

Windows 下也可以使用 `android-pull`，前提是 `adb.exe` 已经加入 `PATH`。如果没有加入 `PATH`，可以显式传入路径：

```powershell
photodaterescue android-pull `
  --adb "C:\Android\platform-tools\adb.exe" `
  --device-path /sdcard/DCIM `
  --device-path /sdcard/Pictures `
  --device-path /sdcard/Movies `
  --output C:\Users\you\Pictures\android-export
```

### 扫描媒体目录

```bash
photodaterescue scan \
  --input /path/to/android-export \
  --report /path/to/report
```

带缓存目录过滤的例子：

```bash
photodaterescue scan \
  --input /path/to/android-export \
  --report /path/to/report \
  --exclude "Pictures/.thumbnails" \
  --exclude "Pictures/.gs*" \
  --exclude "DCIM/.globalTrash"
```

扫描报告包括：

- `summary.json`
- `files.csv`
- `high_risk.csv`

### 生成修复副本

```bash
photodaterescue repair \
  --input /path/to/android-export \
  --output /path/to/repaired-media \
  --report /path/to/report
```

建议先导入少量修复样本到 Apple Photos，确认时间线正确后再批量导入。

### 恢复安卓 Motion Photo / Live Photo

macOS 用户如需生成 Apple Live Photo 兼容输出，可以先 dry-run：

```bash
photodaterescue rescue-live \
  --input /path/to/android-export \
  --work-dir /path/to/live-work \
  --output /path/to/live-output \
  --exclude "Pictures/.thumbnails" \
  --dry-run
```

确认报告后再真正生成输出：

```bash
photodaterescue rescue-live \
  --input /path/to/android-export \
  --work-dir /path/to/live-work \
  --output /path/to/live-output \
  --exclude "Pictures/.thumbnails"
```

`motion-extract` 会在 `extraction.csv` 和 `extracted_pairs.csv` 中写出 `source_type`、`source_reason`，用于区分小米原生相机嵌入式动态照片、通用 Motion Photo / MicroVideo 候选等来源。
中文向导和 `rescue-live-manifest.json` 也会汇总这些来源统计，方便先看有多少小米原生候选能进入提取流程。可提取出静态图 + 短视频配对，不等于 Apple Photos 一定识别为 Live Photo。

Windows 用户或不想依赖 `makelive` 时，只建议生成跨平台配对包：

```bash
photodaterescue rescue-live \
  --input /path/to/android-export \
  --work-dir /path/to/live-work \
  --output /path/to/live-output \
  --exclude "Pictures/.thumbnails" \
  --dry-run

photodaterescue live-build \
  --backend portable-pair \
  --pairs-csv /path/to/live-work/motion-audit/pairs.csv \
  --source-root /path/to/android-export \
  --output /path/to/live-pairs \
  --report /path/to/live-pair-report
```

`portable-pair` 会把静态图、短视频和 `pair.json` 放在同一个配对目录里，方便后续检查和实验。它只表示“动态照片关系被保留下来”，不是 Apple Live Photo，不保证 Apple Photos 会直接识别成 Live Photo。

如果你已经有一对图片 / 视频，可以用只读检查命令看看它们是否带有 Apple Live Photo 常见配对元数据：

```bash
photodaterescue live-inspect \
  --image /path/to/IMG_001.jpg \
  --video /path/to/IMG_001.mov
```

`live-inspect` 只读取元数据，不修改文件。它能提示 Content Identifier 是否匹配、是否疑似存在 Apple Maker Notes、视频时长等信息；但最终能否被 Apple Photos 识别，仍需要真实导入验收。

如果你已经通过 `motion-audit` 或 `rescue-live --dry-run` 得到了 `pairs.csv`，可以批量生成只读诊断报告：

```bash
photodaterescue live-probe \
  --pairs-csv /path/to/live-work/motion-audit/pairs.csv \
  --source-root /path/to/android-export \
  --report /path/to/live-probe-report
```

`live-probe` 会写出 `live-probe.csv`、`errors.csv` 和 `live-probe-manifest.json`。它不会修改原始图片或视频，主要用于判断哪些配对已经有匹配的 Apple Live Photo 元数据信号、哪些在 Windows 写入实验上会被缺少 Apple Maker Notes 等问题挡住。

## 命令总览

- `doctor`：检查本机依赖。
- `wizard`：运行中文终端向导。
- `android-pull`：通过 `adb pull -a` 导出安卓媒体目录。
- `scan`：扫描媒体目录并写出报告。
- `repair`：生成修复后的媒体副本。
- `motion-audit`：只读审计疑似安卓动态照片 / Live Photo 候选。
- `motion-extract`：从嵌入式 JPEG 动态照片中提取视频。
- `live-build`：从图片 / 视频配对生成输出副本；`makelive` 后端用于 macOS Apple Live Photo，`portable-pair` 后端用于跨平台配对包。
- `live-inspect`：只读检查图片 / 视频配对中的 Live Photo 元数据信号。
- `live-probe`：批量只读检查 `pairs.csv` 中的 Live Photo 元数据信号。
- `rescue-live`：串联 Motion Photo 审计、提取和 Live Photo 构建流程。
- `reconcile`：对比候选导出目录和已修复基线目录。
- `classify-unmatched`：分类对账后的剩余文件。
- `materialize-unmatched`：把分类后的剩余文件复制或移动到实体分类目录。

## 大图库建议流程

1. 优先使用 `photodaterescue wizard` 走推荐流程。
2. 如果要从安卓设备导出，优先使用 `photodaterescue android-pull`，这样更容易保留文件修改时间。
3. 先扫描，再修复，不要跳过报告检查。
4. 先导入少量样本到 Apple Photos 验证。
5. 验证正确后，再批量导入修复后的副本。
6. 如需恢复安卓动态照片，先使用向导或 `rescue-live --dry-run`；Windows 仅保留配对包，macOS 才尝试 Apple Live Photo 输出。

## 隐私与数据安全

PhotoDateRescue 只处理本地文件，不会主动上传照片、视频或报告。

但请注意，报告中可能包含文件名、拍摄时间、绝对路径等隐私信息。发布 issue、分享日志或提交测试样本前，请先确认没有包含真实个人媒体文件和隐私路径。

更多说明见：

- `docs/privacy-and-data-safety.md`
- `docs/release-checklist.md`
- `docs/manual/apple-photos-import-checklist.md`
- `docs/packaging/macos-gui.md`

## 开发与测试

```bash
source .venv/bin/activate
python -m pytest -q
photodaterescue --help
```

## Roadmap

- 补充更多真实 Apple Photos 导入验证说明。
- 扩展不同安卓厂商 Motion Photo 样本兼容性。
- 继续完善 Windows 普通照片 / 视频修复文档和真实设备验证。
- 保持 Windows 动态照片边界清晰：支持审计、提取、跨平台配对包，不承诺 Apple Live Photo 构建。
- 在有真实样本支撑后，再考虑 HEIC / AVIF 嵌入式动态照片提取。

## License

PhotoDateRescue is released under the MIT License.

Copyright (c) 2026 C1oud.
