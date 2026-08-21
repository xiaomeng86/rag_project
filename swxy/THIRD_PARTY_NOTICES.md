# 第三方来源说明

本项目的 DeepDoc 文档解析、RAG 分词/查询和部分 Elasticsearch 适配代码基于 InfiniFlow/RAGFlow 进行课程项目二次开发，主要位于：

- `backend/app/service/core/deepdoc/`
- `backend/app/service/core/rag/`
- `backend/app/service/core/api/utils/file_utils.py`

上述来源文件保留了 InfiniFlow Authors 的版权与 Apache License 2.0 声明。上游项目：https://github.com/infiniflow/ragflow ，许可证：https://www.apache.org/licenses/LICENSE-2.0 。本项目对其进行了格式收口、服务接口适配、模型调用、数据持久化、失败补偿和前后端契约整合；不应将 DeepDoc/RAG 核心能力表述为从零自研。

其余第三方 Python 与前端依赖及版本分别记录在 `backend/app/requirements.txt` 与 `frontend/pnpm-lock.yaml`，其版权归各自作者所有。
