# PhotoDateRescue v0.1.2 发布说明

PhotoDateRescue v0.1.2 发布 Windows 图形界面源码运行支持。这个版本的重点是让 Windows 用户也可以通过 `photodaterescue-gui` 使用普通照片 / 视频时间线修复流程。

## 更新内容

- Windows 用户可从源码运行 `photodaterescue-gui`。
- 图形界面改为跨平台普通照片 / 视频修复入口。
- Windows 下“打开输出文件夹”会使用 Windows 原生打开方式。
- GUI 依赖提示会按当前平台显示 macOS 或 Windows 安装建议。
- README 新增 Windows GUI 说明。
- 新增 Windows 图形界面源码运行指南：`docs/manual/windows-gui-source-guide.md`。
- 版本号更新为 `0.1.2`。

## 平台边界

- macOS Release 仍提供 `.app` 压缩包。
- Windows 当前提供源码运行 GUI，不提供 `.exe` 安装包。
- Windows GUI 只承诺普通照片 / 视频时间线修复。
- Windows 不承诺构建 Apple Photos 可识别的 Live Photo。
- Live Photo / Motion Photo 高级恢复仍建议使用 CLI，并先 dry-run 和小样本验证。

## 安全原则

- 不修改源媒体文件。
- 不自动导入 Apple Photos / iCloud。
- 不自动删除照片或视频。
- 不上传任何照片、视频或报告。
