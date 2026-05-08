# PhotoDateRescue v0.3.0 发布说明

PhotoDateRescue v0.3.0 增加 Windows GUI `.exe` alpha 打包流程。这个版本的重点是让维护者可以通过 GitHub Actions 生成实验性的 Windows GUI 包，方便后续真实 Windows 机器验证。

## 更新内容

- 新增 GitHub Actions 工作流：`Windows EXE Alpha`。
- 新增本地 Windows 打包脚本：`scripts/build-windows-exe.ps1`。
- 新增 Windows exe alpha 打包说明：`docs/packaging/windows-exe-alpha.md`。
- README 增加 Windows exe alpha 入口和限制说明。
- 版本号更新为 `0.3.0`。

## Alpha 边界

- Windows `.exe` 当前是 alpha，不是稳定安装包。
- `.exe` 未签名，可能触发 Windows SmartScreen 或杀软提示。
- `.exe` 不内置 ExifTool / FFmpeg / adb。
- ExifTool 仍需用户自行安装并加入 `PATH`。
- Windows GUI 只承诺普通照片 / 视频时间线修复。
- Windows 不承诺构建 Apple Photos 可识别的 Live Photo。

## 安全原则

- 不修改源媒体文件。
- 不自动导入 Apple Photos / iCloud。
- 不自动删除照片或视频。
- 不上传任何照片、视频或报告。
