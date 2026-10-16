# NovelFactory 工程说明

面向 Codex 工作区的小说工厂工程：文件驱动、Agent 分工、断点续跑。

- 引擎：`NovelFactory/core/`（零第三方依赖，标准库实现）
- 提示词：`NovelFactory/resources/prompts/`（5 个 Agent 角色）
- 命令：`python -m NovelFactory.scripts.run {init|outline|write|monitor|export}`
- 详细：见 `GUIDE.md`（使用）与 `API.md`（接口）
