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

- 前端：http://localhost:4850
- API：http://localhost:8850
- PostgreSQL：localhost:6250

## 演示账号

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| `admin` | `123456` | 管理员 |
| `worker` | `123456` | 缫丝工 |

## 业务规则

- 盆状态不可标成「已缫完」，除非该盆**最近一条**汤温记录落在 **38～42℃**。规则在 `backend/app/services.py`。
- **蒸汽开度带**：每个坞有唯一一条现行带（下限百分、上限百分、更新人），下限不得大于上限。种子带为 **20～40%**。
- 登记汤温时，该坞**现行蒸汽开度**必须落在开度带 **[下限, 上限]（含边界）**；出带则**整笔拒绝**，不会先写入汤温。顶栏「蒸汽开度」专页可查看现行带；仅管理员可改上下限，缫丝工只读。抽屉默认开度填 55（在 20～40 之外，便于看到拒绝）。
- 开度带只管汤温登记，**不顶掉** 38～42℃ 的已缫完汤温门槛——两者各管各的。

## 快速启动

```bash
cd SilkReel/SilkReel-01
docker compose up --build
```
