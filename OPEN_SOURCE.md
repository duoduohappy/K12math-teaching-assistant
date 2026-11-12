# 开源参考与复用边界

本轮实现不是把三个项目作为可安装插件接入。已下载原始仓库核查；采用轻量独立模块，保留当前 Python + SQLite 系统。

- https://github.com/anthropics/k12-teacher-skills ：Apache-2.0。参考其教案、分层任务、形成性检测和教师观察的产品组织方式。未复制技能正文、代码、美国课程标准或连接器；不宣称中国课标已验证对齐。
- https://github.com/bcefghj/math-education-agent ：本次克隆未发现独立 LICENSE，未复制任何代码。数学模块独立使用 Python AST 与 Fraction 实现一元一次式的解析和精确校验，避免 eval；未引入其模型供应商。
- https://github.com/ningkaikok/dotty-tutor ：Apache-2.0。参考材料来源、课件审核发布、学生练习与反馈的流程设计；未复制其代码或引入 OCR、PostgreSQL 和 Worker。当前检索为按材料隔离的关键词切片检索，不是向量检索。

界面与 API 中预置生成、本地模型生成均明确区分。本地 Ollama 接口仅访问 127.0.0.1:11434，无付费 API。模型权重未下载；是否能实时生成取决于本机安装、模型与硬件。教材资料仍为自编模拟卡片，不冒充官方人教版原文。
