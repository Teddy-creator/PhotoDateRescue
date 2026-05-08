# Changelog

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
