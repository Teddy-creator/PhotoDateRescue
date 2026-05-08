# PhotoDateRescue 开源发布检查清单

这份清单用于发布 Mac-first v1.0 前的最后确认。目标是让项目对国内普通用户也能安全上手，同时避免误提交真实照片、报告或隐私路径，并清楚区分 macOS 与 Windows 的功能边界。

## 1. 发布前必须确认

- [x] 选择开源许可证：MIT License，版权署名为 `C1oud`。
- [x] 确认 README 中的安装命令、依赖说明和 `photodaterescue wizard` 流程可按步骤跑通。
- [x] 确认 `pyproject.toml` 的作者信息、项目描述、版本号适合公开。
- [x] 确认仓库没有真实照片、视频、Apple Photos library、导出报告、绝对隐私路径或 API key。
- [x] 确认 `.gitignore` 能排除本地输出目录、真实相册导出目录和临时测试目录。
- [x] 确认 GitHub 仓库描述说明这是 Mac-first 工具；Windows 支持普通照片 / 视频修复，不承诺 Apple Live Photo 构建。
- [x] 确认内部计划文档、真实样本路径和本机绝对路径没有作为公开文档发布。

建议 GitHub 仓库简介：

```text
安卓换 iPhone 后照片/视频时间线乱了？PhotoDateRescue 会扫描本地导出的媒体目录，安全生成可导入 Apple Photos 的修复副本。macOS 优先，Windows 支持普通照片/视频核心修复流程。
```

## 2. 本地验证命令

```bash
cd /path/to/PhotoDateRescue
source .venv/bin/activate

photodaterescue doctor
photodaterescue --help
photodaterescue wizard
.venv/bin/python -m pytest -q
```

`photodaterescue wizard` 至少要验证：

- 主菜单为中文。
- 退出流程不会写入文件。
- 只检查环境流程可运行。
- 对一个小样本目录可以完成扫描并写出报告。
- Live Photo 流程会先 dry-run，不会自动导入 Apple Photos。
- Windows 下向导会跳过 Apple Live Photo 构建，只处理普通照片 / 视频时间线。

## 3. 真实数据安全检查

发布前运行：

```bash
git status --short
git ls-files | grep -Ei '(.jpg|.jpeg|.png|.webp|.heic|.heif|.mp4|.mov|.m4v|.3gp|photoslibrary)$' || true
git ls-files | grep -Ei '(raw-export|live-full-build|live-full-dryrun|PhotoDateRescue-output|Pictures|DCIM|WeiXin|QQ)' || true
```

如果命中真实个人数据，先移出仓库，再提交。

## 4. 建议发布说明

首个公开版本可以这样描述：

```text
PhotoDateRescue v0.1.0 是一个 Mac-first 的相册迁移修复工具，主要用于安卓迁移到 iPhone 后的照片/视频时间线错乱，以及安卓动态照片的审计、提取和配对保留。

本版本提供中文终端向导 `photodaterescue wizard`，默认不修改源文件、不自动导入 Apple Photos、不自动删除重复项。Windows 重点支持普通照片 / 视频修复；Apple Live Photo 元数据写入仅作为 macOS + `makelive` 路径处理。
```

更完整的 GitHub Release 文案见 `docs/release-notes-v0.1.0.md`。

## 5. 暂不承诺的能力

- 不直接写入 Apple Photos / iCloud。
- 不自动删除重复照片。
- 不保证 HEIC / AVIF 嵌入式动态照片提取。
- 不支持 Windows 上构建 Apple Photos 可识别的 Live Photo。
- 不保证所有国产安卓相册私有格式都能恢复。
