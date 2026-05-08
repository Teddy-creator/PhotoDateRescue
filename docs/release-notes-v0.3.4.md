# PhotoDateRescue v0.3.4 发布说明

PhotoDateRescue v0.3.4 修复 Windows `.exe` 真机 smoke test 中发现的 GUI 显示问题。

## 修复内容

- GUI 主窗口默认尺寸从 `780x560` 调整为 `920x720`。
- GUI 主体增加滚动条，避免 Windows 高缩放或小窗口下“扫描与修复 / 处理结果”区域被裁掉。
- 长说明文字会随窗口宽度重新换行。
- 环境状态改为更清楚的多行格式，区分“影响”和“安装提示”。
- 增加“重新检查”按钮，安装 ExifTool / FFmpeg 后可以不用重启窗口直接刷新状态。
- 版本号更新为 `0.3.4`。

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
