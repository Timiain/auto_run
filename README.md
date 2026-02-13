# deepcli

科研自动实验规划与执行的 CLI 多智能体框架（Python）。

## 快速开始

```bash
pip install -r requirements.txt
python deepcli.py init ./your_project
cd your_project
python ../deepcli.py run --concept concept.json
python ../deepcli.py status --verbose
python ../deepcli.py report <run_id>
```

## 支持命令

- `init <project_dir> [--force]`
- `run [--plan <file>] [--concept <file>]`
- `status [--verbose]`
- `report <run_id> [--output <file>]`
- `iterate <run_id> [--concept <file>] [--execute]`
- `config [--set key=value]`

## LLM 接口

内置 `get_chat_response(...)`，支持：
- OpenAI 兼容接口（`openai.OpenAI`）
- Ollama（模型名格式 `ollama#llama3.1`）

你可以在规划器/优化器中直接调用该函数，接入更复杂的自动实验策略。
