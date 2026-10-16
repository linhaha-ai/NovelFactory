# NovelFactory API 说明

引擎核心类：`NovelFactoryEngine`（`NovelFactory/core/engine.py`）

## 初始化

```python
from NovelFactory.core.engine import NovelFactoryEngine

engine = NovelFactoryEngine("novel_factory", dry_run=False)
```

参数：
- `workspace`：写作工作区路径
- `dry_run`：True 时不调用真实模型，用于演示链路

## 主要方法

| 方法 | 说明 |
|---|---|
| `load_context(chapter_no)` | 按需加载第 N 章上下文（细纲/人物/记忆/上章结尾），返回 dict |
| `call_llm(system, user, temperature)` | 调用后端（ollama / openai），返回文本 |
| `generate_chapter(chapter_no)` | 主笔 Agent 生成一章正文 |
| `review_chapter(chapter_no, content)` | 审稿 Agent 返回 `ReviewReport`（verdict: 通过/重写/人工） |
| `update_memory(chapter_no, content)` | 记忆 Agent 提取并追加 timeline / foreshadow |
| `run_pipeline(start, end, max_retry)` | 生产主循环，断点续跑 |
| `close()` | 关闭数据库连接 |

## 数据模型（core/models.py）

- `ChapterPlan`：单章细纲（goal / conflict / payoff / hook），`load(plan_path)` 解析
- `ReviewReport`：审稿结果，`parse(raw)` 从模型输出解析【判定】
- `list_chapter_ids(workspace)`：扫描已规划章节

## 配置（novel_factory/config.toml）

| 段 | 键 | 说明 |
|---|---|---|
| `[novel]` | title / genre / chapter_word_count / word_tolerance / tone | 书名、题材、单章字数、浮动、文风 |
| `[llm]` | provider / base_url / model / temperature_write / temperature_review / timeout | 后端与参数 |
| `[pipeline]` | start / end / max_retry | 流水线范围与重试上限 |

## 命令行入口

```powershell
python -m NovelFactory.scripts.run {init|outline|write|monitor|export}
python -m NovelFactory.scripts.pipeline --start 1 --end 5 --dry-run
python -m NovelFactory.scripts.outline  # 独立大纲脚本
python -m NovelFactory.scripts.export --formats txt,html
python -m NovelFactory.scripts.monitor
```
