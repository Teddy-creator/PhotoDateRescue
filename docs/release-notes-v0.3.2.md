# PhotoDateRescue v0.3.2 发布说明

PhotoDateRescue v0.3.2 是一个 Windows CI 兼容性补丁版本，用于继续推进 Windows GUI `.exe` alpha 自动构建。

## 修复内容

- 修复部分测试默认假设运行在 macOS，导致 Windows runner 上走到正确 Windows 分支后断言失败的问题。
- 修复 `live-inspect` / `motion-extract` 遇到缺失输入文件时，可能先提示缺少 ExifTool 而不是直接提示文件缺失的问题。
- 版本号更新为 `0.3.2`。

## 平台边界

- Windows `.exe` 仍是 alpha，不是稳定安装包。
- `.exe` 未签名，可能触发 Windows SmartScreen 或杀软提示。
- `.exe` 不内置 ExifTool / FFmpeg / adb。
- Windows GUI 只承诺普通照片 / 视频时间线修复。
- Windows 不承诺构建 Apple Photos 可识别的 Live Photo。

## 安全原则

- 不修改源媒体文件。
- 不自动导入 Apple Photos / iCloud。
- 不自动删除照片或视频。
- 不上传任何照片、视频或报告。
