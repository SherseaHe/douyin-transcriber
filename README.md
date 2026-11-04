# Douyin Transcriber：抖音视频转文字与口播文案提取 Skill

中文 | [English](README.en.md) · [安装配置](docs/configuration.md) · [Agent Skill](SKILL.md) · [问题反馈](https://github.com/SherseaHe/douyin-transcriber/issues)

**Douyin Transcriber 是一个 MIT 开源的抖音语音转写工具，同时提供 Agent Skill 和 Python CLI。** 输入抖音分享链接或本地音视频，使用 FFmpeg 与豆包 ASR 提取口播文案，输出 TXT、Markdown 和 JSON。适合整理视频逐字稿、提取口播素材，以及为后续内容总结提供原文。

An open-source **Douyin video-to-text Agent Skill and Python CLI** for speech transcription with FFmpeg and Doubao ASR. Converts spoken audio into TXT, Markdown and JSON; includes verified caching and an Agent-assisted browser fallback.

## 项目速览

| 项目 | 说明 |
| --- | --- |
| 项目名称 | Douyin Transcriber / `douyin-transcriber` |
| 主要用途 | 抖音视频转文字、口播文案提取、本地音视频转写 |
| 使用方式 | 支持 SKILL.md 的 Agent（已在 Codex 场景实测）或独立 Python CLI |
| 输入 | 抖音分享文本/短链/完整链接、本地音视频、公开 MP3/WAV/OGG URL |
| 输出 | TXT 逐字稿、Markdown 逐字稿、ASR JSON、运行摘要 JSON |
| 语音识别 | 火山引擎豆包录音文件识别极速版 `volc.bigasr.auc_turbo` |
| 配置 | Python 3.10+、FFmpeg/ffprobe、ASR Key；抖音直接下载另需 yt-dlp |
| 平台 | macOS / Linux；Windows 需要 WSL，原生 Windows 不支持 |
| 费用 | 代码采用 MIT 免费开源；云端 ASR 按服务账户计费 |
| 能力边界 | 处理语音；不做画面理解、OCR、自动翻译或 SRT 导出 |

快速导航：[安装](#安装与配置) · [CLI 用法](#命令行使用) · [输出与缓存](#输出与缓存) · [常见问答](#常见问答) · [配置与排障](docs/configuration.md)

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

## 常见问答

### 如何把抖音视频转成文字？

安装本项目的 Python、FFmpeg 和 yt-dlp 依赖，配置豆包 ASR Key，然后运行 `python3 scripts/douyin_transcribe.py '抖音分享链接'`。CLI 会尝试获取媒体、提取音频并转写。平台阻止直接下载时，需要使用浏览器兜底或提供本地音视频文件。

### 可以提取抖音视频文案吗？

可以提取视频中**说出来的口播文案**，生成逐字稿。画面字幕、图文帖文字和没有声音的文字内容不在转写范围内；这些需要另行使用 OCR 工具。

### 这是免费、离线运行的工具吗？

代码以 MIT 许可证开源。音频提取在本地进行，但识别需要把音频发送到火山引擎豆包 ASR，可能产生费用。项目没有本地 Whisper 后端，完整转写不能离线完成。回归测试使用模拟 ASR，可以离线运行。

### 能在 Codex 或其他 AI Agent 中使用吗？

仓库提供 `SKILL.md` 和 `agents/openai.yaml`，已在 Codex 场景实测。其他支持 SKILL.md 的客户端可按各自安装规则加载，浏览器工具和环境变量需要另外配置；不依赖特定浏览器插件。也可以完全不使用 Agent，直接运行 Python CLI。

### 支持 TikTok、B站或小红书链接吗？

当前链接解析只针对抖音（Douyin），不支持国际版 TikTok、B站或小红书链接。对合法取得的本地音视频文件，可以使用相同的转写流程。

### 如何让 AI 总结抖音视频？

先用本项目生成 `transcript.md`，再让 Agent 根据逐字稿总结重点。语音转写和内容总结是两个步骤；基于逐字稿的摘要不能替代对视频画面的分析。

### 为什么浏览器能播放，命令行却提示 403？

浏览器播放与直接下载使用的请求环境不同，抖音可能要求验证或新的 Cookie。项目提供经过用户授权的浏览器媒体提取流程，但不会自动绕过验证，也不会默认读取 Cookie。参见 [浏览器兜底](SKILL.md#browser-fallback) 和 [故障排查](docs/configuration.md#常见问题)。

## 测试

```bash
python3 -B scripts/test_transcribe.py
```

测试不需要 API Key、不访问抖音、不调用 ASR；需要 FFmpeg/ffprobe。覆盖缓存串稿、内容更新、损坏结果、失败重跑、独立下载目录、半成品清理、并发锁及真实音频提取。

2026-11-04 的一次人工实测：约 16 分 30 秒英文音频，经浏览器兜底获取音轨后，豆包 ASR 返回 179 个语音片段，识别请求耗时约 10.7 秒；重复运行命中缓存。这是单次观察，不是性能基准，10.7 秒不包括浏览器操作与下载。未测量词错率，也不保证其他链接的下载成功率或识别质量。第三方视频及转写内容未收录到仓库。

可复现的离线验证见 [回归测试源码](scripts/test_transcribe.py)。项目事实与能力边界以本仓库 README、配置文档和代码为准。

## 数据与费用

转写音频发送到火山引擎豆包 ASR，按服务账户的规则计费。仓库不包含 API Key、Cookie、用户视频或转写样本。离线测试不会发起付费调用。请处理你有权使用的内容。

## License

[MIT](LICENSE)。许可证适用于本仓库代码与文档，不授予第三方视频内容的使用权。
