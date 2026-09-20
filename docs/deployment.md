# 部署指南

AutoGrader 采用 **Docker Compose 一键部署**，包含 4 个服务：前端（nginx）、后端（FastAPI）、后台任务（worker）、数据库（PostgreSQL）。

## 一、架构

```
浏览器
   │  HTTP
   ▼
frontend (nginx :80)  ── 静态资源（React 构建产物）
   │  /api 反向代理
   ▼
backend (FastAPI :8000) ──► db (PostgreSQL :5432)
   ▲
worker (后台任务：解析 / 评阅) ──► db / 共享 uploads 卷
```

- **db**：PostgreSQL 16，数据持久化在 `pgdata` 卷。
- **backend**：处理 HTTP 请求，上传报告写入共享卷 `uploads_data`。
- **worker**：异步执行「解析」与「评阅」任务（从 `uploads_data` 读文件）。
- **frontend**：nginx 托管前端静态资源，并把 `/api` 反代到 backend。

## 二、前置要求

- 一台 Linux 服务器（腾讯云 Lighthouse / CVM 等），安全组已放通 **80** 端口（配 HTTPS 则 443）。
- 已安装 Docker 与 Docker Compose（Lighthouse 应用镜像通常自带）。

## 三、部署步骤

### 1. 上传代码

```bash
# 方式一：git clone（推荐）
git clone <仓库地址> autograder && cd autograder

# 方式二：本地打包上传
# 本地：tar czf autograder.tar.gz --exclude=node_modules --exclude=.venv --exclude=dist .
# 服务器：scp autograder.tar.gz root@<IP>:/root/ && tar xzf autograder.tar.gz && cd autograder
```

### 2. 配置环境变量

```bash
cp .env.example .env
vim .env
```

必须修改的项：

| 变量 | 说明 |
| --- | --- |
| `POSTGRES_PASSWORD` | 数据库密码（改掉默认值） |
| `JWT_SECRET` | JWT 签名密钥，用 `openssl rand -hex 32` 生成 |
| `LLM_BASE_URL` | 模型服务的 OpenAI 兼容端点（如 `https://api.xiaomimimo.com/v1`） |
| `LLM_API_KEY` | 模型服务 API Key |
| `LLM_MODEL` | 模型名（如 `mimo-v2.5`） |

### 3. 构建并启动

```bash
docker compose up --build -d
```

### 4. 检查状态

```bash
docker compose ps                      # 4 个服务都应 Up/healthy
docker compose logs -f backend worker  # 跟踪日志
```

### 5. 访问

浏览器打开 `http://<服务器IP>`，即可注册账号开始使用。

## 四、域名 + HTTPS（推荐）

生产环境建议绑定域名并启用 HTTPS。以下用 Caddy 做反向代理 + 自动签发证书：

```bash
# 1. 安装 Caddy（或直接用云平台的证书 + 负载均衡）
# 2. Caddyfile
#    your.domain.com {
#        reverse_proxy localhost:80
#    }
# 3. Caddy 会自动申请 Let's Encrypt 证书
```

> 也可把 `docker-compose.yml` 里 frontend 的 `80:80` 改为 `127.0.0.1:8080:80`，再由 Caddy 反代 `localhost:8080`，避免直接暴露容器端口。

## 五、常用运维命令

```bash
docker compose ps                        # 查看状态
docker compose logs -f backend           # 后端日志（含访问日志）
docker compose logs -f worker            # 任务日志（解析/评阅）
docker compose restart worker            # 重启某个服务
docker compose up --build -d             # 更新代码后重建
docker compose down                      # 停止（数据不丢，保留在卷中）

# 备份数据库
docker compose exec db pg_dump -U autograder autograder > backup_$(date +%F).sql

# 恢复数据库
cat backup_2026-09-20.sql | docker compose exec -T db psql -U autograder autograder
```

## 六、常见问题

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 上传报告后一直「解析中」 | worker 没跑起来或读不到文件 | `docker compose logs worker`，确认 `uploads_data` 卷已挂载 |
| 评阅报「报告解析未完成」 | 解析任务失败（parsed 未 done） | 同上，检查 worker 日志与共享卷 |
| 上传大文件 413 | nginx/后端大小限制 | 已放宽到 20MB；再大需调 `nginx.conf` 的 `client_max_body_size` |
| 模型调用失败 | LLM 配置错误 | 检查 `.env` 的 `LLM_BASE_URL/API_KEY/MODEL` |
| 502 网关错误 | backend 未就绪 | `docker compose ps`，等 backend 启动完成 |

## 七、安全建议

- 务必替换默认 `JWT_SECRET` 和 `POSTGRES_PASSWORD`。
- 生产环境可去掉 `db` 的端口映射（`10080:5432`）与 backend 的 `8000:8000`，仅通过 frontend（nginx）对外。
- 定期备份数据库（见上）。
