import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { api, clearToken } from "../api/client";
import type { User } from "../api/types";
import HelpGuide from "./HelpGuide";

export default function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const { data: user } = useQuery<User>({
    queryKey: ["me"],
    queryFn: () => api.get<User>("/auth/me"),
  });

  function logout() {
    clearToken();
    navigate("/login");
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link to="/" className="wordmark">
          AutoGrader<em>·</em>循证评阅
        </Link>
        <div className="spacer" />
        <HelpGuide />
        {user && <span className="user-chip">{user.username}</span>}
        <button className="btn sm" style={{ background: "transparent", color: "#cfc7b8", borderColor: "#3a3a3a" }} onClick={logout}>
          退出
        </button>
      </header>
      {children}
    </div>
  );
}
