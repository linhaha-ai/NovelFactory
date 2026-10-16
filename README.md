# NovelFactory 小说工厂

在 Codex 工作区中批量生产长篇网文的工程化流水线：**大纲 → 细纲 → 章节写作 → 自动审稿 → 记忆更新**，文件驱动、断点续跑、杜绝吃书。

## 快速上手（2 分钟）

在项目根目录 `E:\code-workspace\ai-code\ai-book` 打开终端：



```
# 1. 初始化写作工作区（已就绪，可跳过）
python -m NovelFactory.scripts.run init

# 2. 生成大纲（总纲 → 卷纲 → 前5章细纲），然后人工审阅 plot/ 下文件
python -m NovelFactory.scripts.run outline "主角林辰，都市上班族，金手指随身灵泉，爽文快节奏" --start 1 --end 5

# 3. 启动章节生产流水线（真实调用本地 Ollama 模型）
python -m NovelFactory.scripts.run write --start 1 --end 5

# 4. 查看进度 / 导出合集
python -m NovelFactory.scripts.run monitor
python -m NovelFactory.scripts.run export
```

> 想先看流程不烧 token：
>
> `python -m NovelFactory.scripts.run write --dry-run`

## 目录结构



```
ai-book/
├─ AGENTS.md                 # Codex 自动加载的总控指令（打开项目即生效）
├─ NovelFactory/             # 可运行的 Python 工程
│  ├─ core/                  # 引擎：utils / models / database / engine
│  ├─ agents/                # 提示词加载器
│  ├─ scripts/               # run / init / outline / pipeline / export / monitor
│  ├─ templates/             # 大纲、细纲、人物模板
│  ├─ resources/
│  │  ├─ prompts/            # 5 个 Agent 系统提示词
│  │  ├─ styles/             # 文风规范
│  │  └─ guidelines/         # 写作守则
│  └─ docs/                  # GUIDE.md / API.md
└─ novel_factory/            # 写作工作区（已初始化）
   ├─ config.toml            # 小说配置 + LLM 后端配置
   ├─ world.md               # 世界观
   ├─ characters/            # 人物档案（hero / villain / 更多）
   ├─ plot/                  # full_outline / volume / chapter_plans
   ├─ manuscript/            # 成品章节 ch001.md ...
   └─ memory/                # timeline.md / foreshadow.md / novel.db
```

## 后端配置（novel\_factory/config.toml）

默认走本地 Ollama（`qwen3.5:9b`）。改用 OpenAI 兼容接口：



```
[llm]
provider = "openai"
base_url = "https://api.openai.com/v1"
model = "gpt-4o"
# 并设置环境变量 OPENAI_API_KEY（或 CODEX_API_KEY）
```

## 合规提示

AI 生成内容必须人工终审后发布；禁止洗稿抄袭、违禁题材。