# SilkReel-01 · 江口缫丝坞

缫丝盆环状作业台。登录后看到的是沿汤池围成一圈的盆位，点盆登记汤温并改状态——不是侧栏双列表 CRUD。

## 技术栈

| 层 | 技术 |
| --- | --- |
| Web API | Quart（异步 Flask 族）· Hypercorn |
| 结构 | `repositories.py` 仓储 + `services.py` 门槛，路由不直接拼 SQL |
| 数据 | SQLAlchemy 2 async · asyncpg · PostgreSQL 15 |
| 前端 | Preact 10 · Vite |
| 部署 | Docker Compose |

## 路径与端口

- 前端：http://localhost:4760
- API：http://localhost:8760
- PostgreSQL：localhost:6160

## 演示账号

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| `admin` | `123456` | 管理员 |
| `worker` | `123456` | 缫丝工 |

## 业务规则

盆状态不可标成「已缫完」，除非该盆**最近一条**汤温记录落在 **38～42℃**。规则在 `backend/app/services.py`。

登记汤温还须带上当班**蒸汽开度**：开度必须落在该坞**现行开度带**的下限与上限之间（含边界），出带则整笔拒绝，不会先写入再改。开度带字段为坞、下限百分、上限百分、更新人，同一坞现行带最多一条；仅管理员可在「蒸汽开度」专页改带，缫丝工只读。种子带为 20%～40%，抽屉开度默认填 55。开度带只管登记汤温，顶不掉已缫完的 38～42℃ 汤温带。

## 快速启动

```bash
cd SilkReel/SilkReel-01
docker compose up --build
```
