# PhotoDateRescue v0.3.3 发布说明

PhotoDateRescue v0.3.3 是一个很小的 CLI 校验顺序补丁，用于继续修复 Windows EXE alpha 自动构建中暴露的测试差异。

## 修复内容

- 修复 `motion-extract` 遇到缺失 `--candidates-csv` 时，仍可能先检查 ExifTool 并返回依赖错误的问题。
- 缺失 CSV 现在会优先返回输入错误，便于 Windows 用户和 CI 得到更准确的提示。
- 版本号更新为 `0.3.3`。

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
