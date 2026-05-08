# PhotoDateRescue v0.2.0 发布说明

PhotoDateRescue v0.2.0 聚焦图形界面易用性，让普通用户更清楚该选哪个文件夹、扫描结果代表什么、修复完成后下一步该怎么做。

## 更新内容

- GUI 选择源目录后，会更明确地展示推荐安全输出目录。
- GUI 扫描结果改为分类展示：可以尝试修复、已经正常、建议先人工抽查、暂不支持、读取出错。
- GUI 修复完成后，会提示先打开输出文件夹、抽查少量结果，再手动导入 Apple Photos。
- GUI 内新增平台边界提示，明确 Windows 不承诺 Live Photo 构建或 Apple Photos 识别。
- macOS 和 Windows GUI 文档同步更新。
- 版本号更新为 `0.2.0`。

## 平台边界

- macOS Release 继续提供 `.app` 压缩包。
- Windows 当前提供源码运行 GUI，不提供 `.exe` 安装包。
- GUI 只承诺普通照片 / 视频时间线修复。
- Live Photo / Motion Photo 高级恢复仍建议使用 CLI，并先 dry-run 和小样本验证。

## 安全原则

- 不修改源媒体文件。
- 不自动导入 Apple Photos / iCloud。
- 不自动删除照片或视频。
- 不上传任何照片、视频或报告。
