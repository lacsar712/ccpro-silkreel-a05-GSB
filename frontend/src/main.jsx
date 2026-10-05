import { render } from "preact";
import { useEffect, useState } from "preact/hooks";
import { api, clearToken, setToken, token } from "./api.js";
import "./app.css";

const STATUS_LABEL = { soaking: "浸茧", reeling: "缫丝中", reeled: "已缫完" };

function pct(v) {
  if (v === null || v === undefined) return "—";
  return Number.isInteger(v) ? String(v) : String(v);
}

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

function TopNav({ view, onNav, me }) {
  return (
    <div class="topbar">
      <div>
        <h1>江口缫丝坞</h1>
        <nav class="nav">
          <button
            class={view === "yard" ? "navbtn active" : "navbtn"}
            onClick={() => onNav("yard")}
          >
            环盆作业台
          </button>
          <button
            class={view === "steam" ? "navbtn active" : "navbtn"}
            onClick={() => onNav("steam")}
          >
            蒸汽开度
          </button>
        </nav>
      </div>
      <div class="who">
        <span>
          {me.username}（{me.role === "admin" ? "管理员" : "缫丝工"}）
        </span>
        <button
          onClick={() => {
            clearToken();
            location.reload();
          }}
        >
          退出
        </button>
      </div>
    </div>
  );
}

function Yard({ me }) {
  const [board, setBoard] = useState(null);
  const [picked, setPicked] = useState(null);
  const [temp, setTemp] = useState("40");
  const [steam, setSteam] = useState("55");
  const [err, setErr] = useState("");
  const [ok, setOk] = useState("");

  async function refresh() {
    const data = await api("/api/board");
    setBoard(data);
    setPicked((prev) =>
      prev ? data.basins.find((b) => b.id === prev.id) || data.basins[0] : prev
    );
  }

  useEffect(() => {
    refresh().catch((e) => setErr(e.message));
  }, []);

  if (!board) {
    return <div class="yard">{err || "装载环盆…"}</div>;
  }

  const band = board.steamBand;
  const n = board.basins.length;

  async function writeTemp() {
    setErr("");
    setOk("");
    try {
      const row = await api(`/api/basins/${picked.id}/readings`, {
        method: "POST",
        body: JSON.stringify({
          waterTempC: Number(temp),
          steamPct: Number(steam),
        }),
      });
      await refresh();
      setPicked(row);
      setOk("汤温已登记");
    } catch (ex) {
      // 出带：后端整笔拒绝，未写入任何汤温。
      setOk("");
      setErr(ex.message);
    }
  }

  async function setStatus(status) {
    setErr("");
    setOk("");
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
    <div class="yard">
      <p class="sub">{board.riverside} · 点盆登记汤温；登记时蒸汽开度须落在现行带内（含边界）</p>
      {band && (
        <p class="bandline">
          现行蒸汽开度带：<strong>{pct(band.minPct)}～{pct(band.maxPct)}%</strong>
          （更新人：{band.updatedBy || "—"}）
        </p>
      )}
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
              onClick={() => {
                setPicked(b);
                setErr("");
                setOk("");
              }}
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
            <p class="bandline">
              本坞开度带 {pct(band.minPct)}～{pct(band.maxPct)}%（含边界）
            </p>
          )}
          <label class="field">
            汤温 ℃
            <input value={temp} onInput={(e) => setTemp(e.target.value)} />
          </label>
          <label class="field">
            蒸汽开度 %
            <input value={steam} onInput={(e) => setSteam(e.target.value)} />
          </label>
          <button onClick={writeTemp}>登记汤温</button>
          <div>
            <button onClick={() => setStatus("soaking")}>浸茧</button>
            <button onClick={() => setStatus("reeling")}>缫丝中</button>
            <button onClick={() => setStatus("reeled")}>已缫完</button>
          </div>
          {ok && <p class="ok">{ok}</p>}
          {err && <p class="err">{err}</p>}
        </div>
      )}
    </div>
  );
}

function SteamPage({ me }) {
  const admin = me.role === "admin";
  const [bands, setBands] = useState(null);
  const [minPct, setMinPct] = useState("20");
  const [maxPct, setMaxPct] = useState("40");
  const [err, setErr] = useState("");
  const [ok, setOk] = useState("");

  async function refresh() {
    const data = await api("/api/steam-bands");
    setBands(data.bands);
    const first = data.bands[0];
    if (first) {
      setMinPct(pct(first.minPct));
      setMaxPct(pct(first.maxPct));
    }
  }

  useEffect(() => {
    refresh().catch((e) => setErr(e.message));
  }, []);

  if (!bands) {
    return <div class="yard">{err || "装载开度带…"}</div>;
  }

  const band = bands[0];

  async function save() {
    setErr("");
    setOk("");
    const lo = Number(minPct);
    const hi = Number(maxPct);
    if (Number.isNaN(lo) || Number.isNaN(hi)) {
      setErr("上下限必须是数字");
      return;
    }
    if (lo > hi) {
      setErr("下限不得大于上限");
      return;
    }
    try {
      await api(`/api/filatures/${band.filatureId}/steam-band`, {
        method: "PUT",
        body: JSON.stringify({ minPct: lo, maxPct: hi }),
      });
      await refresh();
      setOk("开度带已更新，全坞只此一版");
    } catch (ex) {
      setErr(ex.message);
    }
  }

  return (
    <div class="yard">
      <p class="sub">蒸汽开度专页 · 同一坞现行带最多一条；登记汤温时开度必须落在带内。</p>
      <div class="drawer bandcard">
        <h3>{band ? band.filatureName || "江口缫丝坞" : "江口缫丝坞"} · 现行蒸汽开度带</h3>
        {band ? (
          <p class="bandline">
            现行：<strong>{pct(band.minPct)}～{pct(band.maxPct)}%</strong> · 更新人：
            {band.updatedBy || "—"}
          </p>
        ) : (
          <p class="bandline">尚无开度带</p>
        )}
        <label class="field">
          下限百分 %
          <input
            value={minPct}
            disabled={!admin}
            onInput={(e) => setMinPct(e.target.value)}
          />
        </label>
        <label class="field">
          上限百分 %
          <input
            value={maxPct}
            disabled={!admin}
            onInput={(e) => setMaxPct(e.target.value)}
          />
        </label>
        {admin && band ? (
          <button onClick={save}>保存开度带</button>
        ) : admin ? (
          <p class="hint">尚无开度带，请联系系统初始化。</p>
        ) : (
          <p class="hint">缫丝工仅可查看，修改上下限须管理员。</p>
        )}
        {ok && <p class="ok">{ok}</p>}
        {err && <p class="err">{err}</p>}
      </div>
    </div>
  );
}

function Shell() {
  const [me, setMe] = useState(null);
  const [view, setView] = useState("yard");
  const [bootErr, setBootErr] = useState("");

  useEffect(() => {
    api("/api/auth/me")
      .then(setMe)
      .catch((e) => setBootErr(e.message));
  }, []);

  if (!me) {
    return <div class="yard">{bootErr || "登录中…"}</div>;
  }

  return (
    <div class="shell">
      <TopNav view={view} onNav={setView} me={me} />
      {view === "yard" ? <Yard me={me} /> : <SteamPage me={me} />}
    </div>
  );
}

function App() {
  const [ready, setReady] = useState(Boolean(token()));
  return ready ? <Shell /> : <Login onOk={() => setReady(true)} />;
}

render(<App />, document.getElementById("app"));
