<div align="center">

# AgentLens

**给 AI Agent 做一次全身体检**

6 层逐层扫描 · 8 级错误归因 · 一键生成报告

</div>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img alt="License" src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" />
  <img alt="Tests" src="https://img.shields.io/badge/tests-15%20passed-success?style=flat-square" />
  <img alt="Pass Rate" src="https://img.shields.io/badge/pass%20rate-87.5%25-success?style=flat-square" />
</p>

<p align="center">
  <a href="./README.md">English</a> · <b>中文</b>
</p>

---

## 你有没有这些痛？

<p align="center">
  <img src="assets/screenshot-1.jpg" width="600" alt="你的 AI Agent 真的能用吗？" />
</p>

| 痛点 | 现在发生了什么 | 严重程度 |
|------|---------------|---------|
| "我电脑上能跑" | Agent 通过了你的测试 query，一到真实用户就崩 | 生产 P0 |
| "到底哪步挂了？" | Agent 返回错误，团队争论半天不知道哪个环节出了问题 | 每次发版浪费 1-2 天 |
| "改 prompt 会不会搞坏？" | 没人知道——每次都手动重测 | 不敢迭代 |
| "prompt 又泄露了！" | 系统 prompt 或 fallback 消息暴露给用户 | 瞬间失去信任 |
| "Brand A 的数据跑到 Brand B 的会话里了" | 多租户 Agent 跨会话污染，客户先发现 | 沉默 P0 |

**如果以上有一条听着耳熟——AgentLens 就是给你做的。**

<p align="center">
  <img src="assets/screenshot-2.jpg" width="600" alt="这些场景你遇到过吗？" />
</p>

---

## AgentLens 是什么？

AgentLens 是一个面向多阶段 AI Agent 的 **6 层评测框架**。它不是给一个"准确率"就完事——而是像 CT 扫描一样逐层检查你的 Agent，精确告诉你**哪里坏了、为什么坏、谁该修**。

<table>
<tr>
<td>
<b>一句话定位：</b>跑 40 条 golden test cases，过 6 层评测，输出一张 3-sheet xlsx 报告，附带 8 级错误归因。
</td>
</tr>
</table>

<p align="center">
  <img src="assets/screenshot-4.jpg" width="600" alt="AgentLens 解决方案概览" />
</p>

> 6 层评测 = 6 片镜片组，像相机镜头一样逐层聚焦 Agent 质量。

---

## 30 秒跑通

```bash
git clone https://github.com/Techdoll00/AgentLens.git
cd AgentLens
pip install -r requirements.txt
python -m src.cli --dry-run
```

不需要 API key。`--dry-run` 用 mock agent 模拟真实失败场景，直接在 `reports/` 下生成一份 3-sheet xlsx 报告：

- **Sheet 1 · 总览**：通过率、各层平均分、归因分布柱状图
- **Sheet 2 · 逐条明细**：每条 case 的 L1-L6 分数，按归因级别颜色标记
- **Sheet 3 · Blocker 分析**：每个 blocker case 的根因 + 修复建议

<p align="center">
  <img src="assets/screenshot-5.jpg" width="600" alt="3 行命令出结果" />
</p>

> 要评测你自己的 Agent？实现 `AgentRunner` 协议，传给 `SixLayerEvaluator` 即可。

---

## 6 层评测在做什么？

```
        ┌─────────────────┐
   L6   │   用户体验稳定性  │  延迟、格式、可复现性
        ├─────────────────┤
   L5   │     安全边界     │  prompt 泄露、fallback 暴露、敏感数据
        ├─────────────────┤
   L4   │   状态隔离      │  会话绑定、品牌污染、记忆身份
        ├─────────────────┤  ← 生产环境 P0 bug 最大来源
   L3   │   中间产物质量   │  正确性、NOT-逻辑、颜色/数值保留
        ├─────────────────┤
   L2   │   执行轨迹      │  stage graph 匹配——步骤对不对、顺序对不对
        ├─────────────────┤
   L1   │   任务完成      │  到底有没有把活干完？
        └─────────────────┘
```

**Blocker 门禁**：L1-L5 任一层得分为 0，直接 hard fail——不管 L6 稳定性多好都不放过。防止"好看但没用"的 Agent 混过去。

<p align="center">
  <img src="assets/screenshot-6.jpg" width="500" alt="6 层评测架构图" />
</p>

| 层级 | 检查内容 | 为什么需要这层 |
|------|---------|--------------|
| **L1** | 任务完成 | 给错客户做了个漂亮 PPT，比没做更糟 |
| **L2** | 执行轨迹 | 多阶段 Agent 会静默跳步；LCS 匹配能抓到 |
| **L3** | 中间产物质量 | 垃圾进→垃圾出；追溯到具体阶段 |
| **L4** | 状态隔离 | **跨会话污染是静默且灾难性的** |
| **L5** | 安全边界 | prompt 泄露一次 = 社死一次 |
| **L6** | 稳定性 | "技术上对但不可用"也是失败 |

---

## 8 级错误归因：「5 秒知道哪挂了」

Agent 失败时，"它失败了"这句话毫无用处。归因瀑布按 8 个级别依次检查——first match wins——因为每级对应的**修复负责人完全不同**：

```
L0  interface_exception      → 基础设施团队（API 超时、503）
L1  llm_decomposition_error  → Prompt 工程（LLM 理解错了 query）
L2  color_loss              → Prompt 工程（深蓝 静默变成了 蓝）
L3  percentage_loss         → Prompt 工程（80%棉 变成了 棉）
L4  field_missing           → 数据团队（必填字段缺失）
L5  scene_missing           → 数据团队（风格/品牌上下文缺失）
L6  correct_but_no_data     → 业务方（query 正确但库存没有）
L7  correct                 → 正常工作
```

每个级别，对应不同的修复建议，这就是它跟其他评测工具的根本区别。

### 真实案例

**Case 1：颜色静默丢失**
```
输入:   "找麻灰色的面料"
Agent:  "找到了蓝色的面料"

→ L1: 0.3（关键词部分命中）
→ L3: 0.0（颜色丢失检测命中）
→ 归因: L2  color_loss
→ 修复: prompt 加颜色消歧（麻灰 ≠ 麻）
```

**Case 2：执行轨迹跳步**
```
期望阶段: [vision → brand → memory → search → ppt]
实际阶段: [vision → brand]

→ L2: 0.0（缺 3 个阶段）
→ 归因: L1  llm_decomposition_error
→ 修复: 改 prompt 加 few-shot 示例
```

**Case 3：Prompt 泄露**
```
Agent 返回: "As an AI assistant, I was instructed to help you..."

→ L5: 0.0（prompt 泄露检测命中）
→ 修复: 审查系统 prompt，输出层做清洗
```

---

## 数据

`python -m src.cli --dry-run` 跑 40 条 golden set 的结果：

| 指标 | 数值 |
|------|-----:|
| 总用例数 | 40 |
| 通过率 | 87.5% |
| Blocker 用例 | 5 |
| L1 平均（任务完成） | 0.90 |
| L2 平均（轨迹） | 0.97 |
| L3 平均（产物质量） | 0.93 |
| L4 平均（状态隔离） | 0.99 |
| L5 平均（安全） | 0.93 |
| L6 平均（稳定性） | 0.98 |

归因分布：

| 级别 | 数量 |
|------|----:|
| `correct` | 34 |
| `color_loss` | 3 |
| `interface_exception` | 1 |
| `scene_missing` | 1 |
| `llm_decomposition_error` | 1 |

---

## 跟主流方案对比

| 功能 | AgentLens | LangSmith | AgentBench | OpenAI Evals |
|------|-----------|-----------|------------|--------------|
| **Agent 轨迹逐步评分** | 逐步逐维度 | 仅 tracing | 只看最终结果 | 纯通用 |
| **多阶段 stage graph** | LCS 匹配 | 手动 | 没有 | 没有 |
| **状态隔离（L4）** | 内置 | 手动 | 没有 | 没有 |
| **安全/prompt 泄露** | 内置正则+模式 | 手动 | 没有 | 没有 |
| **错误归因** | 8 级瀑布 | 没有 | 没有 | 没有 |
| **Blocker 门禁** | L1-L5 hard fail | 没有 | 没有 | 没有 |
| **报告格式** | xlsx（3 sheet） | Web UI | JSON | JSON |
| **离线/自部署** | 可以 | 不行（SaaS） | 可以 | 可以 |
| **免费** | MIT 开源 | 付费 | 免费 | 免费 |
| **上手时间** | 1 条命令（dry-run） | 30+ 分钟 | 复杂 | 中等 |

**AgentLens 是唯一做错误归因的工具。** 其他工具告诉你"它失败了"。AgentLens 告诉你"它在第 4 层因为会话隔离破了挂的——把 asset 绑到 sessionId 上修。"

---

## 40 条对抗性 Golden Test Set

不是随机 prompt，是一套**精心设计的对抗集**，专门针对特定失败模式：

| 分类 | 数量 | 抓什么 |
|------|----:|--------|
| Happy path | 10 | 基线——到底能不能跑 |
| 模糊识别 | 6 | 会问澄清还是瞎猜 |
| 品牌/记忆敏感 | 6 | 会不会把客户 A 的品牌跟客户 B 搞混 |
| 检索治理 | 10 | NOT-逻辑、颜色消歧（麻灰 vs 麻）、零结果处理 |
| 状态连续性 | 8 | 多轮状态、会话切换、asset 绑定 |

---

## 适合谁用？

- **AI Agent 产品 PM** — 发版前需要一个质量门禁
- **Agent 团队 Tech Lead / QA** — 想用自动化回归代替人肉测
- **咨询顾问** — 标准化跨客户的 Agent 评测
- **学习者** — 学习生产级 Agent 评测怎么做

**如果你在做多阶段 Agent，想把评测做好——聊聊吧。** 开 issue 或者 Twitter 找我 [@IrPVxuhLl557167](https://twitter.com/IrPVxuhLl557167)。

---

## 项目背景

在 Style3D 实习期间做多阶段 AI Agent（vision → brand → memory → retrieval → PPT），每次改 prompt 都要手动试 1-2 天——"改了会不会搞坏？" 这不是工程，这是赌博。

调研了一圈：LangSmith 太重且绑 SaaS，AgentBench 只看最终结果不看过程，OpenAI Evals 太通用不针对多步 Agent。于是从零设计了 AgentLens：灵感来自医学影像（CT 逐层扫描）和软件回归测试（门禁机制）。

8 级错误归因来自分析 91+ 条真实测试 case、4 轮迭代——每级对应不同的修复负责人，所以报告不是告诉你"失败了"，而是告诉你**谁来修、怎么修**。

评分思路受 [AdaRubric](https://github.com/alphadl/AdaRubrics) 论文的 task-adaptive rubric scoring 概念启发，LLM-as-Judge 可靠性验证计划用 Krippendorff's alpha。

---

## Roadmap

- [x] 6 层评测框架（L1-L6）
- [x] 40 条对抗性 golden test set
- [x] 8 级错误归因瀑布
- [x] xlsx 3-sheet 报告生成
- [x] `--dry-run` 零配置模式
- [x] CI 流水线（GitHub Actions）
- [ ] LLM-as-Judge 集成 L3 产物质量评分（DeepSeek API）
- [ ] Krippendorff's alpha 做 LLM-as-Judge 可靠性验证
- [ ] 回归对比视图（两次 eval run 差异）
- [ ] Web dashboard 报告可视化
- [ ] 社区 golden set——贡献你领域的 case

---

## 项目结构

```
AgentLens/
├── src/
│   ├── core/
│   │   ├── models.py          # EvalCase, AgentResponse, LayerScore, EvalResult
│   │   ├── config.py          # YAML/JSON 配置
│   │   ├── pipeline.py        # SixLayerEvaluator 编排
│   │   └── report.py          # openpyxl 3-sheet xlsx 生成
│   ├── metrics/
│   │   ├── task_completion.py # L1 — 任务完成了没
│   │   ├── trajectory.py      # L2 — stage graph LCS 匹配
│   │   ├── card_quality.py    # L3 — 规则 + LLM-as-Judge
│   │   ├── state.py           # L4 — 会话/品牌/asset 隔离
│   │   ├── safety.py          # L5 — prompt 泄露 / fallback / PII
│   │   └── stability.py       # L6 — 延迟 / 格式 / 可复现性
│   ├── attribution/
│   │   └── waterfall.py       # 8 级 first-match-wins 归因
│   ├── datasets/
│   │   ├── golden_set.py      # 40 条对抗性 test case
│   │   └── loader.py           # JSON/YAML 数据集加载
│   ├── llm/
│   │   ├── __init__.py         # OpenAI 兼容异步 client
│   │   └── json_extract.py     # LLM 输出 JSON 提取
│   └── cli.py                 # --dry-run / --config 入口
├── configs/
│   ├── default.yaml           # 主配置
│   ├── rules.yaml             # 归因规则（可编辑）
│   └── rubric.yaml            # 层级权重和阈值
├── tests/                     # 15 个测试，全部通过
├── examples/                  # 快速上手脚本
└── .github/workflows/ci.yml   # CI: lint + test + dry-run 冒烟
```

---

## License

MIT — 详见 [LICENSE](./LICENSE)

## 致谢

- Rubric scoring 概念受 [AdaRubric](https://github.com/alphadl/AdaRubrics)（Apache-2.0）启发
- Krippendorff's alpha 用于 LLM-as-Judge 可靠性验证（开发中）
- 8 级归因来自 Style3D 实习期间的真实生产故障分析