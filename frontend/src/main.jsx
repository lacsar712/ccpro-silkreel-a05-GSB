import { render } from "preact";
import { useEffect, useState } from "preact/hooks";
import { api, clearToken, setToken, token } from "./api.js";
import "./app.css";

const STATUS_LABEL = { soaking: "浸茧", reeling: "缫丝中", reeled: "已缫完" };

function Login({ onOk }) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("123456");
  const [err, setErr] = useState("");
  async function submit(e) {
    e.preventDefault();
    setErr("");
    try {
      const data = await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      setToken(data.access_token);
      onOk();
    } catch (ex) {
      setErr(ex.message);
    }
  }
  return (
    <div class="login">
      <h1>江口缫丝坞</h1>
      <p>汤温环盆作业台，不是列表台账。</p>
      <form onSubmit={submit} autocomplete="off">
        <label>
          用户名
          <input name="username" autocomplete="off" value={username} onInput={(e) => setUsername(e.target.value)} />
        </label>
        <label>
          密码
          <input name="password" type="password" autocomplete="off" value={password} onInput={(e) => setPassword(e.target.value)} />
        </label>
        <p class="hint">已预填 admin / 123456，另有 worker / 123456</p>
        <button type="submit">登录</button>
      </form>
      {err && <p class="err">{err}</p>}
    </div>
  );
}

function Yard() {
  const [board, setBoard] = useState(null);
  const [band, setBand] = useState(null);
  const [picked, setPicked] = useState(null);
  const [temp, setTemp] = useState("40");
  const [opening, setOpening] = useState("55");
  const [err, setErr] = useState("");

  async function refresh() {
    const data = await api("/api/board");
    setBoard(data);
    api("/api/steam-band").then(setBand).catch(() => setBand(null));
    if (picked) {
      setPicked(data.basins.find((b) => b.id === picked.id) || data.basins[0]);
    }
  }

  useEffect(() => {
    refresh().catch((e) => setErr(e.message));
  }, []);

  if (!board) {
    return <div>{err || "装载环盆…"}</div>;
  }

  const n = board.basins.length;
  async function writeTemp() {
    setErr("");
    try {
      const row = await api(`/api/basins/${picked.id}/readings`, {
        method: "POST",
        body: JSON.stringify({ waterTempC: Number(temp), steamPct: Number(opening) }),
      });
      await refresh();
      setPicked(row);
    } catch (ex) {
      setErr(ex.message);
    }
  }
  async function setStatus(status) {
    setErr("");
    try {
      const row = await api(`/api/basins/${picked.id}/status`, {
        method: "POST",
        body: JSON.stringify({ status }),
      });
      await refresh();
      setPicked(row);
    } catch (ex) {
      setErr(ex.message);
    }
  }

  return (
    <div>
      <p class="sub">
        {board.filature} · {board.riverside} · 点盆登记汤温；已缫完须最近汤温 38～42℃
      </p>
      <div class="ring">
        {board.basins.map((b, i) => {
          const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
          const left = 50 + Math.cos(angle) * 38;
          const top = 50 + Math.sin(angle) * 38;
          return (
            <button
              key={b.id}
              class={`basin ${b.status}`}
              style={{ left: `${left}%`, top: `${top}%` }}
              onClick={() => setPicked(b)}
            >
              <strong>{b.code}</strong>
              <span>{STATUS_LABEL[b.status]}</span>
            </button>
          );
        })}
      </div>
      {picked && (
        <div class="drawer">
          <h3>
            {picked.code} · {STATUS_LABEL[picked.status]}
          </h3>
          <p>最近汤温：{picked.latestTempC ?? "无"} ℃ · 记录 {picked.readingCount} 次</p>
          {band && (
            <p class="hint">
              现行开度带 {band.lowerPct}%～{band.upperPct}%（含边界），出带整笔拒绝
            </p>
          )}
          <label>
            汤温 ℃
            <input value={temp} onInput={(e) => setTemp(e.target.value)} />
          </label>
          <label>
            蒸汽开度 %
            <input value={opening} onInput={(e) => setOpening(e.target.value)} />
          </label>
          <button onClick={writeTemp}>登记汤温</button>
          <div>
            <button onClick={() => setStatus("soaking")}>浸茧</button>
            <button onClick={() => setStatus("reeling")}>缫丝中</button>
            <button onClick={() => setStatus("reeled")}>已缫完</button>
          </div>
          {err && <p class="err">{err}</p>}
        </div>
      )}
    </div>
  );
}

function Steam() {
  const [me, setMe] = useState(null);
  const [band, setBand] = useState(null);
  const [lower, setLower] = useState("");
  const [upper, setUpper] = useState("");
  const [err, setErr] = useState("");
  const [ok, setOk] = useState("");

  async function refresh() {
    const data = await api("/api/steam-band");
    setBand(data);
    setLower(String(data.lowerPct));
    setUpper(String(data.upperPct));
  }

  useEffect(() => {
    api("/api/auth/me")
      .then(setMe)
      .catch(() => setMe({ role: "worker" }));
    refresh().catch((e) => setErr(e.message));
  }, []);

  async function save(e) {
    e.preventDefault();
    setErr("");
    setOk("");
    try {
      const data = await api("/api/steam-band", {
        method: "PUT",
        body: JSON.stringify({ lowerPct: Number(lower), upperPct: Number(upper) }),
      });
      setBand(data);
      setOk("已保存，登记汤温即刻按留下的这一版带验。");
    } catch (ex) {
      setErr(ex.message);
    }
  }

  const isAdmin = me && me.role === "admin";
  return (
    <div class="steam">
      <h2>蒸汽开度</h2>
      {band ? (
        <p>
          {band.filature} 现行带：下限 {band.lowerPct}% ～ 上限 {band.upperPct}%（含边界） · 更新人{" "}
          {band.updatedBy}
        </p>
      ) : (
        <p>{err || "装载开度带…"}</p>
      )}
      {me === null ? (
        <p>装载权限…</p>
      ) : isAdmin ? (
        <form onSubmit={save}>
          <label>
            下限百分
            <input value={lower} onInput={(e) => setLower(e.target.value)} />
          </label>
          <label>
            上限百分
            <input value={upper} onInput={(e) => setUpper(e.target.value)} />
          </label>
          <button type="submit">保存开度带</button>
        </form>
      ) : (
        <p class="hint">缫丝工只能查看现行带，改带请找管理员。</p>
      )}
      {ok && <p class="ok">{ok}</p>}
      {err && band && <p class="err">{err}</p>}
    </div>
  );
}

function App() {
  const [ready, setReady] = useState(Boolean(token()));
  const [page, setPage] = useState("yard");
  if (!ready) {
    return <Login onOk={() => setReady(true)} />;
  }
  return (
    <div class="yard">
      <div class="topbar">
        <div>
          <h1>江口缫丝坞</h1>
          <p>环盆作业台与蒸汽开度专页</p>
        </div>
        <nav class="nav">
          <button class={page === "yard" ? "on" : ""} onClick={() => setPage("yard")}>
            环盆作业台
          </button>
          <button class={page === "steam" ? "on" : ""} onClick={() => setPage("steam")}>
            蒸汽开度
          </button>
          <button
            onClick={() => {
              clearToken();
              location.reload();
            }}
          >
            退出
          </button>
        </nav>
      </div>
      {page === "yard" ? <Yard /> : <Steam />}
    </div>
  );
}

render(<App />, document.getElementById("app"));
