# 隐私与数据安全说明

PhotoDateRescue 会处理本地照片、视频和相册导出目录。真实媒体文件通常包含高度敏感的个人信息，包括拍摄时间、地点、设备信息、人物画面、聊天截图和社交平台缓存文件。

## 项目安全原则

- 默认只生成副本，不修改源文件。
- 不自动导入 Apple Photos / iCloud。
- 不自动删除任何照片或视频。
- 不把任何文件上传到远程服务。
- 报告和 manifest 可能包含本地绝对路径，因此也应视为隐私数据。

## 开源仓库不要提交什么

不要提交：

- 真实照片、视频、Live Photo 配对文件。
- Android 原始导出目录，例如 `Xiaomi14-raw-export`。
- Apple Photos library，例如 `.photoslibrary`。
- 真实运行输出目录，例如 `PhotoDateRescue-output`、`live-output`、`live-work`。
- 包含个人路径的报告，例如 `summary.json`、`files.csv`、`errors.csv`、`manifest.json`。
- 带有姓名、微信、QQ、学校、公司、地理位置等信息的截图。

## 如果需要添加测试样本

建议使用人工构造的最小样本：

- 不含真实人物、不含真实地理信息。
- 文件尺寸尽量小。
- 元数据只保留测试所需字段。
- 文件名不要包含个人信息。

如果必须使用真实样本调试，应放在仓库外部目录，并通过命令参数传入。

## 发布前建议检查

```bash
git status --short
git ls-files | grep -Ei '(.jpg|.jpeg|.png|.webp|.heic|.heif|.mp4|.mov|.m4v|.3gp|photoslibrary)$' || true
git ls-files | grep -Ei '(raw-export|live-full-build|live-full-dryrun|PhotoDateRescue-output|Pictures|DCIM|WeiXin|QQ)' || true
```

这些命令命中结果不一定都是问题，但需要逐项确认。
