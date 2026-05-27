# Nexent Paper Writing Agent

基于 [Nexent](https://github.com/ModelEngine-Group/nexent) 平台的三元推理面，在本地运行的端到端论文自动写作 MCP Agent。

## 为什么需要这个项目

学术写作需要大量文献梳理、章节组织、图表生成和格式编排。传统上这些环节完全依靠手工作业；项目试图验证一种新型工作流：**Human-in-the-loop 确认大纲 → 后台全自动写作 → Word 成品交付**，让作者专注于研究方向与材料准备，而非文字排版和格式。

## 核心架构

项目采用 **三元推理代理 + 本地执行面** 的混合架构：

| 代理 | 职责 | 调用方式 |
|------|------|----------|
| **Generator_Writer** | 按大纲逐章写作，带引用标注 | LLM 调用 |
| **Generator_Coder** | 为结果数据生成 Matplotlib 绘图代码 | LLM 调用 + 本地沙盒执行 |
| **Discriminator** | 审查章节质量与证据合规性，驱动重写循环 | LLM 调用 |

三个代理运行在 Nexent 平台的推理面上；所有编排逻辑（6 阶段状态机）、材料管理、代码沙盒、证据审计和 DOCX 渲染在本地 Python 进程中完成，不依赖第三方 API。

## 关键设计

- **证据门禁**：写作前检查材料充足性，材料不足时拒绝生成，仅在用户明确确认后方可启动降级写作（图表/数据标记为"模拟占位"）
- **图表沙盒**：Generator_Coder 生成的代码在本地 `subprocess` 沙盒中执行，失败后自动带报错信息重试（最多 3 次 Debug 循环）
- **质量审计**：写作完成后对全稿执行确定性规则检查（EEG 通道一致性、分类器范围冲突、结果数字无证据支撑、结论过度声称等）
- **任务隔离**：每篇论文独占材料缓存、图片资产、输出路径和下载链接，不同主题不会串稿
- **Word 成品**：直接生成重庆大学硕士专业学位论文格式的 `.docx`，包含中英文封面、摘要、可跳转目录域、分章正文、图/表题注编号、参考文献和致谢
- **非技术主题保护**：自然语言处理判别论文主题领域，避免在非工程主题（文学、经济等）中插入算法流程图或模拟实验表格

## 工作流程

用户上传材料或给出主题后，Agent 首先生成大纲并等待人工确认；确认后仅启动一次整篇后台写作任务，经逐章写作 → 审查 → 引用解析 → 渲染，最终输出可下载的 `.docx` 文档。

## 功能概览

- 大纲确认闭环：`generate_outline -> confirm_outline_and_start_writing -> get_write_paper_job_status`
- Word 成品交付：重庆大学硕士专业学位风格、双语前置页、可跳转目录域、章节编号题注、参考文献
- 多格式材料输入：DOCX、TXT、PDF、CSV、TSV、XLSX、ZIP、PNG、JPG、JPEG、WEBP
- 图文资产：用户上传图片、DOCX 内嵌图片、开放源图片、研究框架图、方法流程图、结果图表
- 任务隔离：每次任务独立保存材料、资产、输出路径和下载链接，防止不同主题串稿
- 降级写作：材料不足但用户接受降级时，允许生成明确标记为“模拟数据/待替换”的图表和正文
- 非技术主题保护：文学等非工程主题不会误插入算法流程图或模拟实验表格
- 长任务兼容方案：提供 Nexent `v2.1.1` 的页面保活/流式输出补丁，避免长篇写作期间页面长时间无响应

## 目录结构

```text
core/                  LLM、文献检索与内容规范化
execution/             DOCX 渲染、图表生成、渲染校验
orchestrator/          任务、材料、资产、大纲确认与质量状态
tests/                 单元测试
patches/               可选的 Nexent 平台补丁
main.py                MCP 服务入口
config.example.yaml    服务配置示例
.env.example           环境变量示例
Dockerfile             Agent 容器镜像
docker-compose.yml     Agent 一键容器启动配置
nexent-system-prompt.md Nexent 智能体配置说明
```

## 使用前准备

### 必需环境

- 一个可用的 OpenAI-compatible LLM API 或 Anthropic API
- Nexent 本地平台实例
- Python 3.10+，或 Docker Desktop / Docker Engine + Compose

### 推荐环境

- Microsoft Word：在 Windows 原生运行 Agent 时，可在交付前自动填充 Word 的可跳转目录文本
- LibreOffice：可用于将 DOCX 转换为 PDF 做视觉验收，不影响 Agent 运行

### 关于目录的限制

Word 目录是文档域，不是写死的普通文本。本项目生成真正的目录域。Windows 原生部署且已安装 Word 时，Agent 会尝试在交付前调用 Word 更新目录，使用户打开文档即可看到可点击目录。

Docker 容器为 Linux 环境，无法内置 Microsoft Word COM 自动化。因此 Docker 模式可以完整生成论文和目录域，但目录的预填充效果取决于用户打开文档后在 Word 中执行“更新目录”。如要求交付即显示已填充目录，请在安装了 Word 的 Windows 主机上直接运行 Agent。

## 方式一：Windows 原生部署（推荐用于最终 Word 交付）

### 1. 克隆并安装

```powershell
git clone https://github.com/NanAnNuo/nexent-paper-writing-agent.git
Set-Location nexent-paper-writing-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-windows.txt
Copy-Item .env.example .env
Copy-Item config.example.yaml config.yaml
```

如果机器未安装 Microsoft Word，可以改用 `pip install -r requirements.txt`；论文仍会生成，但目录需要用户在 Word 中手动更新。

### 2. 配置模型与服务地址

编辑 `.env`：

```dotenv
LLM_PROVIDER=openai
LLM_API_KEY=your-api-key
LLM_MODEL=your-model-name
LLM_BASE_URL=https://your-openai-compatible-api.example/v1
LLM_MAX_TOKENS=32768
SEMANTIC_SCHOLAR_API_KEY=

# 最终下载链接由用户浏览器访问。本机使用 Nexent 时保留 localhost 即可。
PAPER_AGENT_ADVERTISED_HOST=localhost
PAPER_AGENT_HOST=0.0.0.0
PAPER_AGENT_PORT=8001
```

说明：

- `LLM_API_KEY` 必填；不要提交 `.env`。
- `SEMANTIC_SCHOLAR_API_KEY` 可选；未配置时系统会在可行情况下使用降级检索源。
- `PAPER_AGENT_ADVERTISED_HOST` 被写入最终 DOCX 下载链接。Nexent 页面和浏览器位于本机时使用 `localhost`；跨机器访问时改为浏览器可访问的 IP 或域名。
- `config.yaml` 可继续调整材料、图表和输出目录参数；环境变量优先覆盖服务地址和端口。

### 3. 启动服务

```powershell
python main.py
```

出现以下类型日志即表示服务就绪：

```text
启动 MCP 服务: 0.0.0.0:8001
文件下载: http://localhost:8001/download?path=...
```

### 4. 在 Nexent 注册 MCP

如果 Nexent 运行在 Docker 中，而 Agent 运行在 Windows 宿主机上，MCP 地址不能填写 `localhost:8001`。Docker Desktop 常用地址为：

```text
http://host.docker.internal:8001/sse
```

如果该地址在你的 Docker 环境不可达，则使用容器可访问的宿主机 IP：

```text
http://<host-ip>:8001/sse
```

在 Nexent 智能体中启用下列 MCP 工具，并将 [nexent-system-prompt.md](./nexent-system-prompt.md) 的内容配置为智能体约束：

```text
ingest_materials
list_materials
generate_outline
confirm_outline_and_start_writing
write_paper
get_write_paper_job_status
list_write_paper_jobs
```

### 5. 标准论文写作流程

1. 在 Nexent 对话中上传材料，或给出明确论文主题和要求。
2. Agent 调用 `generate_outline(...)`，返回并展示大纲与 `outline_id`。
3. 用户检查大纲。如果材料不足，可补充材料，或明确接受降级写作。
4. 用户确认后，Agent 调用 `confirm_outline_and_start_writing(outline_id=...)`；不得重新生成大纲。
5. Agent 通过 `get_write_paper_job_status(job_id)` 等待整篇后台写作完成。
6. 页面返回当前任务专属的 `.docx` 下载链接。
7. 打开 Word 检查标题、正文、图表、上传图片、参考文献、目录及语言一致性。

## 方式二：Docker Compose 部署 Agent

Docker 模式用于快速启动 MCP 服务，适合试用、部署和复现实验流程。

### 1. 准备配置

```powershell
git clone https://github.com/NanAnNuo/nexent-paper-writing-agent.git
Set-Location nexent-paper-writing-agent
Copy-Item .env.example .env
Copy-Item config.example.yaml config.yaml
```

> **⚠️ 必须执行 `Copy-Item config.example.yaml config.yaml`**，否则 Docker 会将 `config.yaml` 创建为目录而非文件，导致容器启动失败。

按上文要求编辑 `.env`，至少配置模型 API。若用户浏览器就在运行 Docker 的同一台机器上，保留：

```dotenv
PAPER_AGENT_ADVERTISED_HOST=localhost
PAPER_AGENT_PORT=8001
```

### 2. 构建并启动

```powershell
docker compose up -d --build
docker compose ps
docker compose logs -f paper-agent
```

容器将：

- 将 MCP 与下载服务发布到宿主机 `8001` 端口
- 将 `./data` 挂载为持久化任务/输出目录
- 加载本地 `config.yaml` 与 `.env`
- 安装中文字体以支持图表中的中文标题

### 3. Docker 模式下连接 Nexent

若 Nexent 同样运行在 Docker 中，通过宿主机发布端口连接本 Agent：

```text
http://host.docker.internal:8001/sse
```

也可将两套 Compose 服务接入同一自定义 Docker network，再使用 Agent 容器名访问；这种方式需要同时调整返回给浏览器的 `PAPER_AGENT_ADVERTISED_HOST`，确保下载链接仍可由用户浏览器打开。

### 4. 停止与清理

```powershell
docker compose down
```

`data/` 中的本地生成物不会被提交到 Git。删除 `data/` 会清除本地任务、素材缓存、图片和输出文档。

## 如遇到 Nexent 平台限制导致的 Agent 写作超时终止问题

长篇论文写作会在 MCP 工具中持续数分钟。Nexent `v2.1.1` 原版运行层在工具等待期间可能长时间没有可见消息，并且会逐碎片缓慢刷新模型输出。本仓库提供了经本地验证的补丁：

```text
patches/nexent-v2.1.1-long-task-progress.patch
```

该补丁只修改 Nexent 的以下文件：

```text
sdk/nexent/core/agents/run_agent.py
test/sdk/core/agents/test_run_agent.py
```

行为变更：

- 合并连续的 `model_output_thinking`、`model_output_deep_thinking` 与 `model_output_code` 流片段，减少逐字输出
- 删除每个小片段额外等待 `0.05s` 的人为延时
- MCP 工具静默执行时，每隔 `20` 秒输出一次可见进度保活文本

### 1. 获取与匹配 Nexent 源码

以下步骤针对已验证的 Nexent `v2.1.1`。其他版本请先执行 `git apply --check`，若失败不要强行应用。

```powershell
git clone https://github.com/ModelEngine-Group/nexent.git
Set-Location nexent
git checkout v2.1.1
```

### 2. 应用本仓库附带补丁

将 `<paper-agent-path>` 替换为本 Agent 仓库路径：

```powershell
git apply --check --whitespace=nowarn '<paper-agent-path>\patches\nexent-v2.1.1-long-task-progress.patch'
git apply --whitespace=nowarn '<paper-agent-path>\patches\nexent-v2.1.1-long-task-progress.patch'
```

运行针对性测试：

```powershell
python -m pytest test/sdk/core/agents/test_run_agent.py -q
```

### 3. 让 Nexent Docker runtime 加载修改后的代码

Nexent `v2.1.1` 的 Docker runtime 使用镜像内安装的 Python 包，仅修改宿主机源码不会自动作用于运行容器。打开 Nexent 仓库中的 `docker/docker-compose.yml`，在 `nexent-runtime` 服务的 `volumes:` 下增加这一行：

```yaml
      - ../sdk/nexent/core/agents/run_agent.py:/opt/backend/.venv/lib/python3.10/site-packages/nexent/core/agents/run_agent.py:ro
```

然后重建 runtime 容器：

```powershell
Set-Location docker
docker compose up -d --force-recreate nexent-runtime
```

### 4. 验证补丁已加载

```powershell
docker exec nexent-runtime /opt/backend/.venv/bin/python -c "from nexent.core.agents.run_agent import _coalesce_cached_messages,SSE_KEEPALIVE_INTERVAL_SECONDS; import json; out=_coalesce_cached_messages([json.dumps({'type':'model_output_thinking','content':'a'}),json.dumps({'type':'model_output_thinking','content':'b'})]); print(json.loads(out[0])['content'], SSE_KEEPALIVE_INTERVAL_SECONDS)"
```

预期输出：

```text
ab 20.0
```

### 5. 补丁说明与回退

- 此补丁修复的是 Nexent 页面与运行层的长工具等待体验，不修改论文内容，也不替代 Agent 自身的任务隔离逻辑。
- 如果未来官方 Nexent 已合并等效修复，不应重复应用本补丁。
- 使用 Git 管理 Nexent 源码时，补丁应用后请单独提交，避免与 API Key、`.env` 或其他本地 Docker 配置混合提交。

## 测试与验证

### Agent 单元测试

```powershell
python -m compileall -q core execution orchestrator main.py tests
python -m unittest discover -s tests -q
```

当前发布版本本地验证结果为 `88` 项单元测试通过（包含 Docker 环境变量覆盖与无密钥导入测试）。

### MCP 工具发现验证

服务启动后可运行：

```powershell
@'
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://127.0.0.1:8001/sse") as client:
        tools = await client.list_tools()
        print([tool.name for tool in tools])

asyncio.run(main())
'@ | python -
```

工具列表应至少包含：

```text
generate_outline
confirm_outline_and_start_writing
get_write_paper_job_status
```

### 成品验收建议

- 使用两个完全不同主题连续生成两篇论文，核查标题、章节、图表、引用和下载路径没有串稿
- 上传一张图片材料，检查最终 DOCX 是否包含该图
- 缺真实数据并接受降级写作时，检查图题和表题是否明确标注“模拟数据/待替换”
- Windows + Word 模式下，检查目录是否可点击跳转且打开文档不弹出外部字段更新提示
- Docker 模式下，检查论文、图片和目录域是否生成，并在 Word 中更新目录后验证跳转

## 数据安全与提交规则

以下文件或目录包含密钥、上传材料、运行状态、图片缓存或生成文档，已排除在 Git 外，不应上传至公开仓库或问题讨论：

```text
.env
config.yaml
data/checkpoints/
data/assets/
data/outputs/
data/chroma_db/
data/verification/
figures_path_check/
server_stdout.log
server_stderr.log
mcp_output.log
```

发布截图或 DOCX 前，请自行检查其中是否包含 API Key、个人信息、未公开材料和不应公开的研究数据。

## 已知限制

- Docker 模式不具备 Microsoft Word COM 自动化，无法在容器内部预填 Word 目录显示文本
- 开放源图片检索可用性受网络与第三方 API 限制；失败时系统将继续交付文档并给出警告
- 材料不足时生成的模拟结果只能作为占位，不得视作真实实验结论
- 长任务页面保活需要应用本仓库提供的 Nexent 补丁，或使用未来包含等效修复的官方版本

## License

本项目基于 [Apache License 2.0](./LICENSE) 发布。
