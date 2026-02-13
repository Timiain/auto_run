# 架构师 × 产品经理：如何让 DeepCLI 更智能

## 1. 当前版本定位

- **架构师观点**：我们已完成基础闭环（init→plan→run→record→iterate→report），并重构为可扩展模块。
- **PM观点**：下一步重点应从“能跑”走向“更智能、更省人力、更可信”。

## 2. 智能化优先级（建议按季度）

### P0（立即）
1. **目标对齐层**：把用户 idea 结构化为 `objective / constraints / budget / risks`。
2. **失败自愈层**：对常见报错（OOM、依赖缺失、参数非法）自动生成重试策略。
3. **结果可比层**：统一指标 Schema，支持同任务横向比较（best run、pareto front）。

### P1（短期）
1. **计划生成双轨制**：规则 planner + LLM planner，失败自动降级。
2. **主动建议**：基于历史 run 自动推荐下一轮超参范围。
3. **实验信用分**：对每个 run 打分（复现性、完整性、成本、收益）。

### P2（中期）
1. **多目标优化**：accuracy / latency / cost 三目标联合。
2. **Agent 插件市场**：支持策略包（RL、NAS、AutoML）按需安装。
3. **团队协作模式**：共享 registry/plan/report，支持审批流。

## 3. 产品化交互建议

- CLI 保持极简，但加入：
  - `deepcli suggest <run_id>`：输出 3 个最优 next actions。
  - `deepcli compare <run_id1> <run_id2>`：自动生成对比报告。
  - `deepcli doctor`：环境、依赖、数据路径、GPU 状态一键诊断。

## 4. 核心 KPI

- 计划生成时间（TTFP）
- 单轮实验成功率
- 迭代收敛速度（达到目标指标所需轮次）
- 人工介入次数

## 5. 风险与治理

- **幻觉风险**：LLM 只给建议，不直接执行破坏性命令。
- **成本失控**：强制预算护栏（epochs/GPU-hour 上限）。
- **可复现性**：每轮强制落盘 config + data hash + git commit hash。
