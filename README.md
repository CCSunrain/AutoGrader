# AutoGrader

把「一次不可追溯的模型打分」改造成「可检查、可修正、可回放的实验报告评阅流程」。

首个场景：高校《数据结构与算法》实验报告评阅（重点演示排序算法实验；兼容样例为最短路径实验）。

- 技术栈：React + TypeScript 前端 ｜ FastAPI 模块化单体 + 独立 worker ｜ PostgreSQL
- AI 形态：有限状态工作流 + 工具权限受限 + 结构化输出 + 确定性规则算分
- 环境管理：后端用 **uv**（`uv.lock` 锁定依赖，`.python-version` 固定 Python 3.13）
- 产品基线：见 `docs/project-baseline.md`；模块进度见 `docs/implementation-status.md`

## 当前进度

已交付完整业务闭环 + 前端（详见 `docs/implementation-status.md`）：

- **后端**：多租户 + 5 角色、认证、课程/作业/量表、上传解析（PDF/Markdown + 位置）、
  循证评阅（证据状态 + 证据定位 + 矛盾检测 + 待复核）、人工复核、成绩发布（仅教师）、
  版本对比、班级统计、持久任务 worker。
- **前端**：登录、工作台、三栏评阅台（证据高亮 + 档位复核 + 发布）、学生结果、版本对比。
- **评估**：三方案对比脚本 `backend/scripts/evaluate.py`（一次性打分 / 带证据 / 循证评阅）。

## 快速开始（Docker Compose）

```bash
cp .env.example .env        # 按需填入 POSTGRES_PASSWORD / JWT_SECRET / LLM_BASE_URL / LLM_API_KEY / LLM_MODEL
docker compose up --build  # 启动 db + backend + worker + frontend
```

- 前端：http://localhost（nginx，含 /api 反代）
- 后端 API：http://localhost:8000
- 健康检查：`GET http://localhost:8000/api/health`
- 交互式文档：http://localhost:8000/docs
- **服务器部署**：完整步骤见 `docs/deployment.md`

### 本地开发（不依赖 Docker，用 uv 管理环境）

```bash
cd backend
uv sync                          # 按 pyproject + uv.lock 创建/同步 .venv，安装全部依赖（含 dev）
uv run python -m app.db.init_db        # 建表（需本地 PostgreSQL）
uv run uvicorn app.main:app --reload   # 起 API（http://localhost:8000）
uv run python -m app.worker.main       # 另起 worker
```

> 常用：`uv run pytest` 跑测试；`uv add <pkg>` / `uv remove <pkg>` 增删依赖（自动更新 `uv.lock`）。
> 冒烟测试：`uv run python tests/smoke_test.py`（SQLite 内存，14 项）。

### 前端（本地开发）

```bash
cd frontend
npm install
npm run dev        # Vite dev server（http://localhost:5173，/api 代理到 :8000）
```

生产构建：`npm run build`（产出 `frontend/dist/`）。

### 一键起服务（后端 + worker + 前端）

```bash
# 后端（另开终端）
uv run --project backend uvicorn app.main:app --host 0.0.0.0 --port 8000
uv run --project backend python -m app.worker.main

# 前端（另开终端）
cd frontend && npm run dev
```

## 目录结构

```
backend/
  app/
    core/       # config / db / security / roles / deps（认证与多租户依赖）
    models/     # SQLAlchemy 模型（含 workspace_id 隔离）
    schemas/    # Pydantic 请求/响应
    api/        # 路由：auth / courses / rubrics / submissions / reviews / health
    services/   # ai_client、tasks、storage、parsers（PDF/Markdown 解析）、grading（循证评阅）
    worker/     # 独立 worker（PG 任务表 + FOR UPDATE SKIP LOCKED + 状态机）
    db/         # init_db（dev 建表）
  scripts/      # evaluate.py（三方案对比评估）
  tests/        # 冒烟 + 端到端测试
  alembic/      # 迁移配置（增量变更用）
frontend/       # React + Vite + TS 前端
  src/pages/    # Login / Dashboard / CourseDetail / ReviewDesk / StudentResult / VersionCompare
docker-compose.yml
.env.example
```

## 迁移策略

- 开发阶段：`python -m app.db.init_db`（`create_all`，幂等）快速建表。
- 增量/生产：`alembic revision --autogenerate -m "..."` 生成迁移，`alembic upgrade head` 应用。

## 设计要点

- **多租户**：所有业务表带 `workspace_id`，所有查询强制按当前工作区过滤。
- **角色**：owner / teacher / ta / student；demo 通过 `User.is_demo` + 独立工作区实现。
- **任务恢复**：后台任务持久化在 PG，worker 用 `FOR UPDATE SKIP LOCKED` 领取，
  租约过期后可被重新领取，worker 崩溃不丢任务。
