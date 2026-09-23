import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, setToken, setWorkspaceId } from "../api/client";
import type { TokenResponse } from "../api/types";

export default function Login() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [accountType, setAccountType] = useState<"teacher" | "student">("teacher");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit() {
    setError("");
    setLoading(true);
    try {
      const resp =
        mode === "login"
          ? await api.post<TokenResponse>("/auth/login", { email, password }, true)
          : await api.post<TokenResponse>("/auth/register", { email, username, password, account_type: accountType }, true);
      setToken(resp.access_token);
      setWorkspaceId(null);
      navigate("/");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-card rise">
        <div className="brand">AutoGrader</div>
        <div className="slogan">可检查 · 可修正 · 可回放的实验报告评阅</div>

        {error && (
          <div
            style={{
              background: "var(--red-soft)",
              color: "var(--red)",
              padding: "8px 12px",
              borderRadius: 6,
              marginBottom: 16,
              fontSize: 13,
            }}
          >
            {error}
          </div>
        )}

        {mode === "register" && (
          <>
            <div className="field">
              <label>姓名</label>
              <input
                className="input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="教师 / 学生姓名"
              />
            </div>
            <div className="field">
              <label>身份</label>
              <div className="band-pick">
                <button type="button" className={accountType === "teacher" ? "selected" : ""} onClick={() => setAccountType("teacher")}>
                  我是教师
                </button>
                <button type="button" className={accountType === "student" ? "selected" : ""} onClick={() => setAccountType("student")}>
                  我是学生
                </button>
              </div>
            </div>
          </>
        )}
        <div className="field">
          <label>邮箱</label>
          <input
            className="input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
        </div>
        <div className="field">
          <label>密码</label>
          <input
            className="input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="至少 8 位"
            onKeyDown={(e) => e.key === "Enter" && submit()}
          />
        </div>
        <button className="btn primary" style={{ width: "100%", justifyContent: "center" }} onClick={submit} disabled={loading}>
          {loading ? "请稍候…" : mode === "login" ? "登 录" : "注册并进入"}
        </button>

        <div style={{ textAlign: "center", marginTop: 18, fontSize: 13, color: "var(--ink-soft)" }}>
          {mode === "login" ? (
            <a onClick={() => setMode("register")} style={{ cursor: "pointer", color: "var(--brand)" }}>
              没有账号？注册
            </a>
          ) : (
            <a onClick={() => setMode("login")} style={{ cursor: "pointer", color: "var(--brand)" }}>
              已有账号？登录
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
