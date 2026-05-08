# Windows 图形界面源码运行指南

这份指南面向 Windows 用户。当前 Windows 图形界面适合处理普通照片 / 视频时间线修复，不承诺生成 Apple Photos 可识别的 Live Photo。

## 适合解决什么问题

- 安卓换 iPhone 后，部分照片或视频时间线错乱。
- 想在 Windows 上先扫描、生成报告，再输出修复后的安全副本。
- 不想手写完整命令，但可以接受从源码安装一次工具。

## 功能边界

Windows GUI 当前支持：

- 选择安卓导出的照片 / 视频文件夹。
- 选择安全输出文件夹。
- 扫描并生成报告。
- 生成修复后的安全副本。
- 打开输出文件夹。

Windows GUI 当前不承诺：

- 构建 Apple Photos 可识别的 Live Photo。
- 自动导入 Apple Photos / iCloud。
- 自动删除重复照片。
- 直接处理 Apple Photos 图库文件。

## 安装依赖

你需要准备：

- Python 3.9 或更高版本。
- ExifTool，并确保 `exiftool.exe` 已加入 `PATH`。
- FFmpeg，建议安装并把 `ffmpeg.exe`、`ffprobe.exe` 加入 `PATH`，这样视频处理更完整。

可以先运行：

```powershell
photodaterescue doctor
```

如果 `ExifTool` 显示 missing，请先修好它。没有 ExifTool 时，GUI 会阻止扫描和修复。

## 从源码启动 GUI

```powershell
git clone https://github.com/Teddy-creator/PhotoDateRescue.git
cd PhotoDateRescue

py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .[dev]

photodaterescue-gui
```

## 推荐使用流程

1. 先把安卓手机里的照片和视频导出到 Windows 上的普通文件夹。
2. 打开 `photodaterescue-gui`。
3. 选择“安卓导出文件夹”。
4. 选择一个单独的“安全输出文件夹”。
5. 先扫描，确认摘要合理。
6. 再生成修复后的安全副本。
7. 抽查输出文件，再决定是否导入 iPhone / Apple Photos。

不要把输出文件夹选成原始文件夹，也不要在确认结果前删除手机或电脑里的原始照片。
