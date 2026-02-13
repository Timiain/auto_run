# DeepCLI（架构重构版）

面向科研自动实验规划与迭代的 **CLI 多智能体系统**。

## 架构重构亮点

- 从单文件重构为模块化包：`deepcli/agents`、`deepcli/core`、`deepcli/llm`。
- Agent 职责清晰，文件即通信，状态持久化可恢复。
- 保留并可直接复用 `get_chat_response(...)`，同时支持 OpenAI 与 Ollama。
- Planner 增加“智能预算策略 + 可选 LLM hint”，让计划更智能。

## 目录

```text
.
├── deepcli.py                  # CLI 入口（兼容）
├── deepcli/
│   ├── cli.py                  # argparse 命令分发
│   ├── core/
│   │   ├── io.py               # JSON/YAML 读写
│   │   └── models.py           # ProjectPaths
│   ├── llm/
│   │   └── client.py           # get_chat_response
│   └── agents/
│       ├── project_manager.py
│       ├── env_installer.py
│       ├── scanner.py
│       ├── concept.py
│       ├── planner.py
│       ├── runner.py
│       ├── optimizer.py
│       └── reporter.py
├── PRODUCT_DISCUSSION.md       # 与产品经理的智能化路线讨论
└── requirements.txt
```

## 安装

```bash
pip install -r requirements.txt
```

## 命令

```bash
python deepcli.py init <project_dir> [--force]
python deepcli.py run [--plan <file>] [--concept <file>]
python deepcli.py status [--verbose]
python deepcli.py report <run_id> [--output <file>]
python deepcli.py iterate <run_id> [--concept <file>] [--execute]
python deepcli.py config [--set key=value]
```

## 可选 LLM 规划增强

在项目根目录放置 `.deepcli_llm.json`：

```json
{
  "enabled": true,
  "model": "ollama#llama3.1",
  "base_url": "http://127.0.0.1:11434",
  "api_key": ""
}
```

`ExperimentPlanner` 会把构思转成简短 tuning hint，写入 `experiment_plan.yaml` 的 `llm_hint` 字段。
