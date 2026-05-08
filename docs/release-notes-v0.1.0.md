# PhotoDateRescue v0.1.0 发布说明

PhotoDateRescue v0.1.0 是首个公开版本，定位为一个 macOS 优先、面向中文用户的相册迁移时间线修复工具。

## GitHub 仓库简介

```text
安卓换 iPhone 后照片/视频时间线乱了？PhotoDateRescue 会扫描本地导出的媒体目录，安全生成可导入 Apple Photos 的修复副本。macOS 优先，Windows 支持普通照片/视频核心修复流程。
```

## 本版本包含

- 中文终端向导 `photodaterescue wizard`，适合按步骤完成扫描、报告和安全修复。
- 实验性 macOS 图形界面，面向不想写命令的普通用户。
- 普通照片和视频时间线修复，默认只生成副本，不修改源文件。
- `adb pull -a` 安卓媒体导出辅助命令，尽量保留文件修改时间。
- 安卓 Motion Photo / Live Photo 候选的审计、提取和跨平台配对包。
- macOS + `makelive` 路径下的 Apple Live Photo 元数据写入实验能力。
- 隐私与数据安全说明、Apple Photos 导入检查清单、macOS GUI 小白指南。

## 平台边界

- macOS 是优先验证平台。
- Windows 支持扫描、报告、普通照片/视频修复和安卓导出流程。
- Windows 不承诺生成 Apple Photos 可识别的 Live Photo。
- Live Photo / Motion Photo 恢复仍建议先 dry-run，并用小样本导入 Apple Photos 验证。

## 安全原则

- 不修改源媒体文件。
- 不自动导入 Apple Photos / iCloud。
- 不自动删除照片或视频。
- 不上传任何照片、视频或报告。
- 报告文件可能包含本地路径，分享前请先检查隐私信息。

## 推荐发布标签

```text
v0.1.0
```

## 推荐 Release 标题

```text
PhotoDateRescue v0.1.0: 安卓迁移 iPhone 相册时间线修复工具首版
```
