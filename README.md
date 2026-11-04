# Douyin Transcriber

把抖音分享链接或本地音视频转成口播文字的 Agent Skill，也可以直接作为 Python CLI 使用。使用 FFmpeg 提取音频，通过豆包录音文件识别极速版生成 TXT、Markdown 和 JSON。

## 能做什么

- 接收抖音分享文本、短链、完整视频链接、本地音视频或公开音频 URL。
- 自动尝试网页解析和 yt-dlp 下载；被平台拦截时提供 Agent 浏览器兜底流程。
- 根据输入身份、文件内容和输出校验值复用缓存，避免同名文件串稿。
- 隔离每次运行的临时文件，清理中断下载，阻止同一输出目录的并发覆盖。

**范围：语音转写。** 不包含画面理解、画面字幕 OCR、自动翻译或 SRT 导出。CLI 不自动启动/操作浏览器，也不能保证每个抖音链接都可直接下载。

## 安装与配置

支持 Python 3.10+、macOS / Linux；Windows 请使用 WSL。macOS 已实测，Linux 可运行回归测试；原生 Windows 不支持 POSIX 文件锁。

```bash
# macOS：系统依赖
brew install python ffmpeg yt-dlp

# 克隆到 Agent 可发现的 Skill 目录；目标目录应不存在
mkdir -p ~/.agents/skills
git clone https://github.com/SherseaHe/douyin-transcriber.git ~/.agents/skills/douyin-transcriber
```

已有同名 Skill 时，先备份或克隆到其他目录比较，不要覆盖私人配置。其他 Agent 客户端请使用其对应的 skills 目录。

在火山引擎开通豆包语音的**录音文件识别极速版**，获取有该服务权限的 API Key，再在运行进程中设置 `VOLC_ASR_API_KEY`。CLI 只读取环境变量，不读取 `.env` 或 shell 配置文件。

**完整步骤、Linux 安装、密钥设置、桌面 Agent 环境和排障见 [配置文档](docs/configuration.md)。**

配置后，在 Agent 中使用：

```text
使用 $douyin-transcriber 提取这个视频的口播：<抖音分享链接>
```

## 命令行使用

以下命令在仓库目录执行，结果默认写入当前工作目录的 `outputs/`：

```bash
# 整段分享文本也可以作为一个参数传入
python3 scripts/douyin_transcribe.py 'https://v.douyin.com/分享码/'

# 本地视频、音频（含 M4A）
python3 scripts/douyin_transcribe.py '/path/to/video.mp4' --out-dir outputs/example

# 输出 JSON 摘要
python3 scripts/douyin_transcribe.py '/path/to/audio.m4a' --json

# 强制刷新缓存，或指定识别语言
python3 scripts/douyin_transcribe.py '/path/to/video.mp4' --force --language en-US
```

Python 脚本仅依赖标准库。FFmpeg/ffprobe 和 yt-dlp 是外部命令；本地文件转写不需要 yt-dlp。

## 输出与缓存

| 文件 | 内容 |
| --- | --- |
| `transcript_raw.txt` | ASR 原文 |
| `transcript.md` | Markdown 原文 |
| `raw_result.json` | ASR 返回值，包含语音片段等字段 |
| `summary.json` | 输入身份、文件校验、耗时、输出路径和预览 |

默认目录为 `outputs/douyin-transcriber/{label}-{input-hash}`。本地文件的路径/内容或识别语言变化会使缓存失效；损坏的结果也不会被复用。URL 缓存以输入链接为身份，同一个 URL 的远端内容变化需要 `--force`。短链与长链不共用缓存。

临时目录在运行结束或异常时清理，原始本地输入不删除。`.lock` 文件和空的 `work` 父目录可能保留，这是正常的。结果包含本地路径或输入 URL，分享前请检查。

## 链接下载失败怎么办

抖音可能返回 403、验证页面或要求 fresh cookies。程序会给出失败步骤；若浏览器能播放，可由 Agent 按 [SKILL.md](SKILL.md#browser-fallback) 获取经过授权的临时媒体地址。

浏览器播放正常不代表 CLI 能直接下载。平台可能分离音视频：下载前应核对时长和音轨。签名地址只能临时保存，完成后删除；公开 Skill 不预先授予 Cookie 或浏览器数据访问权限。

## 测试

```bash
python3 -B scripts/test_transcribe.py
```

测试不需要 API Key、不访问抖音、不调用 ASR；需要 FFmpeg/ffprobe。覆盖缓存串稿、内容更新、损坏结果、失败重跑、独立下载目录、半成品清理、并发锁及真实音频提取。

曾对约 16 分 30 秒的视频完成浏览器音频兜底与豆包转写，并验证重复运行命中缓存。该实测不代表抖音链接始终可直接下载；识别质量仍可能受语言、背景音乐和术语影响。

## 数据与费用

转写音频发送到火山引擎豆包 ASR，按服务账户的规则计费。仓库不包含 API Key、Cookie、用户视频或转写样本。离线测试不会发起付费调用。请处理你有权使用的内容。

## License

[MIT](LICENSE)。许可证适用于本仓库代码与文档，不授予第三方视频内容的使用权。
