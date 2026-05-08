# PhotoDateRescue v0.3.1 发布说明

PhotoDateRescue v0.3.1 是一个 Windows 兼容性补丁版本，用于修复 v0.3.0 Windows Actions 构建时暴露出的时区数据缺失问题。

## 修复内容

- 新增 `tzdata` 运行时依赖。
- 修复 Windows Python 环境下 `ZoneInfo("Asia/Shanghai")` 可能找不到时区数据库的问题。
- 版本号更新为 `0.3.1`。

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
