# Douyin Transcriber 安装配置：抖音转文字 Skill 与豆包 ASR

[项目介绍](../README.md) · [English guide](../README.en.md) · [Agent 工作流](../SKILL.md)

本页说明如何安装抖音口播转写 Skill、配置 `VOLC_ASR_API_KEY`，并验证本地文件与抖音链接转写。

## 1. 准备运行环境

需要 Python 3.10+、FFmpeg（包含 ffprobe）。解析抖音链接还需要 yt-dlp。Python 业务脚本没有第三方库依赖。

macOS：

```bash
brew install python ffmpeg yt-dlp
```

Ubuntu / Debian（请确认 Python 至少 3.10）：

```bash
sudo apt update
sudo apt install python3 ffmpeg pipx
pipx install yt-dlp
pipx ensurepath
```

重新打开终端，让 PATH 生效。Windows 使用 WSL 后按 Linux 步骤操作；原生 Windows 不支持当前使用的 `fcntl` 文件锁。

检查依赖：

```bash
python3 --version
ffmpeg -version
ffprobe -version
yt-dlp --version
```

更新 yt-dlp 时应沿用安装方式，例如 `brew upgrade yt-dlp` 或 `pipx upgrade yt-dlp`。更新不能保证绕过抖音的访问限制。

## 2. 安装 Skill

```bash
mkdir -p ~/.agents/skills
git clone https://github.com/SherseaHe/douyin-transcriber.git ~/.agents/skills/douyin-transcriber
cd ~/.agents/skills/douyin-transcriber
```

如果目标目录已存在，先比较并备份旧版本。也可以克隆到普通目录，直接使用 CLI；作为 Skill 使用时，按你的 Agent 客户端规则放置目录并刷新 Skill 列表或重新开始会话。

## 3. 开通豆包 ASR

1. 登录火山引擎，进入豆包语音控制台。
2. 开通“录音文件识别极速版”，确认账户可使用资源 `volc.bigasr.auc_turbo`。
3. 在控制台的 API Key 管理中创建或取得具备相应服务权限的密钥。
4. 确认额度/计费已就绪；API Key 与火山引擎通用 AccessKey/SecretKey 不是同一组配置。

本项目使用：

| 配置 | 值 |
| --- | --- |
| 环境变量 | `VOLC_ASR_API_KEY` |
| HTTP 认证头 | `X-Api-Key` |
| 资源 ID | `volc.bigasr.auc_turbo` |
| 接口 | `https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash` |

不需要配置标准版的轮询接口、App ID 或对象存储上传地址。本地音频以 Base64 发送；公开音频 URL 可直接提交。默认自动识别语言，可通过 `--language zh-CN`、`--language en-US` 指定。

官方参考（2026-11-04 核对）：[极速版 API](https://docs.volcengine.com/docs/doubao-voice/recording-file-recognition-lite-http?lang=zh)、[接入必读](https://docs.volcengine.com/docs/doubao-voice/access-must-read-1?lang=zh)。服务限制、权限和计费以官方最新文档及控制台为准。

## 4. 设置密钥

**只需设置一个环境变量。** 下面的占位值必须换成你的 API Key：

```bash
export VOLC_ASR_API_KEY='替换成你的_API_Key'
```

避免将真实密钥写入命令历史，可以在终端交互输入：

```bash
# macOS 默认 zsh
read -s 'VOLC_ASR_API_KEY?请输入豆包 ASR API Key: '
export VOLC_ASR_API_KEY
printf '\n'
```

Bash：

```bash
read -r -s -p '请输入豆包 ASR API Key: ' VOLC_ASR_API_KEY
export VOLC_ASR_API_KEY
printf '\n'
```

设置仅对当前 shell 及其启动的进程生效。如果需要持久配置，可在自己的 `~/.zshrc` 或 `~/.bashrc` 中加入 export，或使用你的运行器提供的环境变量/密钥设置。不要把真实值写进仓库。

**桌面 Agent 注意：** GUI 启动的应用不一定继承终端环境变量。要在实际运行脚本的进程里设置该变量，或从已设置变量的环境启动运行器。重启应用后再检查。开源版不会自动读取 `~/.zshrc`，也不会自动加载 `.env`。

只检查“是否存在”，不打印密钥：

```bash
python3 -c 'import os; print("已配置" if os.environ.get("VOLC_ASR_API_KEY", "").strip() else "未配置")'
```

## 5. 验证与首次转写

先运行免费离线测试：

```bash
python3 -B scripts/test_transcribe.py
```

然后选一段自己的、包含清晰语音的短音频做真实测试（会调用 ASR）：

```bash
python3 scripts/douyin_transcribe.py '/absolute/path/to/sample.mp3' --out-dir outputs/smoke-test --json
```

确认 `status` 为 `ok`，打开 `transcript_raw.txt` 核对内容。相同命令再运行应返回 `cached`，不重复调用 ASR。接着测试抖音分享链接；如果返回 403，需要浏览器兜底或使用合法取得的本地文件。

## 常见问题

| 问题 | 处理 |
| --- | --- |
| `Missing VOLC_ASR_API_KEY` | 在执行脚本的同一环境设置变量；开源版不读取 shell 配置文件 |
| 401、403 或资源权限错误来自 ASR | 检查 Key、极速版服务权限和计费状态；不要把完整密钥发到 Issue |
| 403 / `Fresh cookies ... needed` 来自抖音 | 停止重复尝试，按 Skill 的浏览器兜底流程处理；Cookie 访问需要另行明确授权 |
| 找不到 ffmpeg / ffprobe / yt-dlp | 安装对应命令并检查 Agent 进程的 PATH |
| ASR 超时 | 当前请求超时为 30 秒；检查网络与文件大小，必要时先切成较短的本地音频分别转写。不要自动重试付费请求 |
| 超长或超大音频 | 当前不自动分段，按服务限制自行切分后处理 |
| 输入 M4A | 使用主 CLI，会先转成 MP3；不要直接传给低层 flash 脚本 |
| 输出是英文 | 转写保留原声语言；要中文可另做翻译，画面上的中文字幕不会被 OCR |
| 提示另一任务正在使用目录 | 等前一进程退出，或指定不同 `--out-dir`；不要靠删除 `.lock` 绕过运行中的锁 |
| 修改了文件却想强制重转 | 主 CLI 通常会自动识别内容变化；也可使用 `--force` |
| 浏览器兜底后标题/来源为空或是本地路径 | CLI 只知道传入的临时文件；由 Agent 补充经过确认的公开视频信息，不能写入签名媒体 URL |

浏览器、终端和 Agent 可能受到不同网络/执行权限限制。权限不足时使用运行器的正常审批流程，不要把临时访问数据写入长期日志。
