# NovelFactory 使用指南（GUIDE）

## 一、工作流总览

```
[初始化] → [大纲：总纲→卷纲→细纲] → [人工确认细纲] → [流水线：写作→审稿→重写→记忆] → [人工终审] → [导出]
```

## 二、第一次使用

1. 确认 Python ≥ 3.10（本项目用 Python 3.13 验证，零第三方依赖）。
2. 打开终端进入 `E:\code-workspace\ai-code\ai-book`。
3. 运行 `python -m NovelFactory.scripts.run init` 初始化写作工作区（已随项目就绪，幂等可重跑）。
4. 编辑 `novel_factory/config.toml`：
   - `[novel]` 填书名、题材、单章目标字数、文风；
   - `[llm]` 填后端：本地 Ollama（默认 `qwen3.5:9b`）或 OpenAI 兼容接口。
5. 编辑 `novel_factory/world.md`、`characters/hero.md`、`characters/villain.md` 填写世界观与人物。

## 三、大纲阶段

```powershell
python -m NovelFactory.scripts.run outline "主角林辰，都市上班族，金手指随身灵泉，爽文快节奏" --start 1 --end 5
```

- 生成 `plot/full_outline.md` → `plot/volume1.md` → `plot/chapter_plans/ch001_plan.md ... ch005_plan.md`
- **必须人工审阅**：细纲是否有冲突、有无流水账、钩子是否成立。修改后直接编辑对应 md 文件。

## 四、生产阶段

```powershell
python -m NovelFactory.scripts.run write --start 1 --end 5
```

流水线行为：
- 已存在的章节自动跳过（断点续跑）；
- 每章：写作 → 审稿（人设/设定/文字/结构 + 字数硬校验）→ 不通过自动重写 1 次 → 仍不合格标记【人工复审】并停止；
- 审核通过后自动更新 `memory/timeline.md` 与 `memory/foreshadow.md`。

## 五、人工复审处理

- 看 `memory/novel.db` 或 `monitor` 输出找到标记章节；
- 直接编辑该章 `manuscript/chNNN.md` 修复问题；
- 重跑流水线 `write`，已修复章节会跳过，继续后续章节。

## 六、进度与导出

```powershell
python -m NovelFactory.scripts.run monitor                 # 每章字数/状态/记忆规模
python -m NovelFactory.scripts.run export --formats txt,html,docx
```

- `export/《书名》_合集.txt`：各平台上传常用
- `export/《书名》.html`：浏览器阅读
- docx 需先 `pip install python-docx`

## 七、切换后端

- Ollama（默认）：保证 `ollama serve` 运行，`ollama pull qwen3.5:9b`（或你本地已有模型名写入 config）。
- OpenAI 兼容：改 `config.toml` 的 `[llm]`，设置环境变量 `OPENAI_API_KEY`。

## 八、合规红线

AI 生成内容发布前必须人工终审；禁止洗稿、抄袭、违禁题材；遵守各小说平台内容规范。
