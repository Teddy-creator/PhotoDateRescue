# PhotoDateRescue v0.2.1 发布说明

PhotoDateRescue v0.2.1 是一个小型文案与发布页打磨版本，重点帮助第一次打开项目的用户更快判断自己该下载什么、从哪里开始、哪些能力暂不承诺。

## 我该用哪个入口

| 你的情况 | 推荐入口 |
| --- | --- |
| macOS，不想用终端 | 下载 `PhotoDateRescue-v0.2.1-macOS.zip` |
| Windows，可以安装 Python | 按 `docs/manual/windows-gui-source-guide.md` 从源码运行 `photodaterescue-gui` |
| 想处理高级 Motion Photo / Live Photo | 使用 CLI，并先 dry-run 和小样本验证 |

## 更新内容

- README 首屏增加 macOS / Windows / 高级 CLI 的入口选择表。
- GUI 首屏安全提示补充“先小样本验证”。
- Release 说明补充陌生用户下载选择和边界提醒。
- 版本号更新为 `0.2.1`。

## 平台边界

- macOS Release 提供 `.app` 压缩包。
- Windows 当前提供源码运行 GUI，不提供 `.exe` 安装包。
- GUI 只承诺普通照片 / 视频时间线修复。
- Live Photo / Motion Photo 高级恢复仍建议使用 CLI，并先 dry-run 和小样本验证。

## 安全原则

- 不修改源媒体文件。
- 不自动导入 Apple Photos / iCloud。
- 不自动删除照片或视频。
- 不上传任何照片、视频或报告。
