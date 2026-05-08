# Changelog

## 0.3.0 - Windows exe alpha packaging

### Added

- 新增 GitHub Actions Windows GUI exe alpha 构建工作流。
- 新增 Windows exe alpha 本地打包脚本。
- 新增 Windows exe alpha 打包说明文档。

### Known Limitations

- Windows exe alpha 不内置 ExifTool / FFmpeg / adb。
- Windows exe alpha 未签名，可能触发 SmartScreen 或杀软提示。

## 0.2.1 - First-run copy polish

### Changed

- README 首屏增加 macOS / Windows / 高级 CLI 的入口选择表。
- GUI 首屏安全提示补充“先小样本验证”。
- Release 说明补充陌生用户下载选择和边界提醒。

## 0.2.0 - GUI usability polish

### Changed

- GUI 会在选择源目录后更明确地展示推荐安全输出目录。
- GUI 扫描结果改为按可修复、正常、高风险、不支持、错误分类展示。
- GUI 修复完成后显示更清楚的 Apple Photos 手动导入下一步提示。
- GUI 内直接展示平台边界，避免误解 Windows / Live Photo 支持范围。

## 0.1.2 - Windows GUI source support

### Changed

- 图形界面改为跨平台普通照片 / 视频修复入口，Windows 可从源码运行 `photodaterescue-gui`。
- Windows 图形界面使用 Windows 原生方式打开输出文件夹。
- GUI 依赖提示根据当前平台显示 macOS 或 Windows 安装建议。

## 0.1.1 - Release download polish

### Changed

- README 首屏新增普通用户下载 GitHub Release 版的指引。
- 补充未签名 macOS `.app` 需要右键打开的说明。
- GUI 在扫描 / 修复前检查必需依赖 ExifTool，并给出更清楚的中文提示。

## 0.1.0 - Mac-first preview

### Added

- 中文终端向导：`photodaterescue wizard`
- 普通照片 / 视频时间线扫描与安全副本修复
- 安卓 Motion Photo 审计、提取和 Apple Live Photo 兼容输出构建
- `rescue-live` 一键安全工作流
- Android `adb pull -a` 导出辅助命令
- 对账、剩余文件分类和实体分类目录生成命令
- 发布前检查清单与隐私数据安全说明

### Safety

- 不修改源文件
- 不自动导入 Apple Photos / iCloud
- 不自动删除重复项
- 输出和报告默认写入用户指定目录

### Known Limitations

- Live Photo 构建目前以 macOS + `makelive` 为主
- 不支持直接写入 Apple Photos / iCloud
- 暂不支持 HEIC / AVIF 嵌入式动态照片提取
- Windows 后续可以优先支持扫描、修复和提取，但 Apple Live Photo 构建仍需另行验证
