# PhotoDateRescue v0.1.1 发布说明

PhotoDateRescue v0.1.1 是一个小修版本，重点改善普通用户第一次下载和打开 macOS 图形界面的体验。

## 更新内容

- README 首屏新增普通用户下载 Release 版的入口。
- 明确说明未签名 macOS `.app` 可能需要右键“打开”。
- GUI 在扫描 / 修复前会先检查必需依赖 ExifTool。
- 缺少 ExifTool 时，GUI 会显示更清楚的中文安装提示。
- 版本号更新为 `0.1.1`。

## 平台边界

- macOS 图形界面仍聚焦普通照片 / 视频时间线修复。
- Windows 仍支持核心 CLI 流程，Windows GUI 将在后续版本推进。
- Live Photo / Motion Photo 高级恢复仍建议使用 CLI，并先 dry-run 和小样本验证。

## 安全原则

- 不修改源媒体文件。
- 不自动导入 Apple Photos / iCloud。
- 不自动删除照片或视频。
- 不上传任何照片、视频或报告。
