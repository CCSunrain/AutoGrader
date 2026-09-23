import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api, setWorkspaceId } from "../api/client";
import type { Course, Me } from "../api/types";

export default function Dashboard() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", code: "", term: "" });
  const [joinCode, setJoinCode] = useState("");
  const [joinError, setJoinError] = useState("");
  const [createError, setCreateError] = useState("");

  const { data: me } = useQuery<Me>({
    queryKey: ["me"],
    queryFn: () => api.get<Me>("/auth/me"),
  });
  const isTeacher = me?.account_type !== "student";

  const { data: courses, isLoading } = useQuery<Course[]>({
    queryKey: ["courses"],
    queryFn: () => api.get<Course[]>("/courses/mine"),
  });

  const create = useMutation({
    mutationFn: (body: { name: string; code: string; term: string }) =>
      api.post<Course>("/courses", body, true),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["courses"] });
      setShowCreate(false);
      setForm({ name: "", code: "", term: "" });
      setCreateError("");
    },
    onError: (e) => setCreateError((e as Error).message),
  });

  const join = useMutation({
    mutationFn: (code: string) => api.post<Course>("/courses/join", { code }, true),
    onSuccess: (c) => {
      qc.invalidateQueries({ queryKey: ["courses"] });
      setJoinCode("");
      setJoinError("");
      setWorkspaceId(c.workspace_id);
      navigate(`/courses/${c.id}`);
    },
    onError: (e) => setJoinError((e as Error).message),
  });

  const editCourse = useMutation({
    mutationFn: (arg: { id: string; body: { name: string; code: string; term: string } }) =>
      api.patch<Course>(`/courses/${arg.id}`, arg.body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["courses"] }),
  });

  const deleteCourse = useMutation({
    mutationFn: (id: string) => api.del<void>(`/courses/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["courses"] }),
  });

  function handleEdit(c: Course) {
    const name = window.prompt("课程名称", c.name);
    if (name === null) return;
    const code = window.prompt("课程编号", c.code);
    if (code === null) return;
    const term = window.prompt("学期", c.term);
    editCourse.mutate({ id: c.id, body: { name, code, term: term ?? c.term } });
  }

  function handleDelete(c: Course) {
    if (window.confirm(`确认删除课程「${c.name}」？该课程下的作业、提交与评阅将一并删除，且不可恢复。`)) {
      deleteCourse.mutate(c.id);
    }
  }

  function enter(c: Course) {
    setWorkspaceId(c.workspace_id);
    navigate(`/courses/${c.id}`);
  }

  return (
    <div className="container">
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 20, flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 className="page-title">我的课程</h1>
          <div className="page-sub">{isTeacher ? "管理实验报告评阅的课程与作业" : "你已加入的课程"}</div>
        </div>
        {isTeacher ? (
          <button className="btn primary" onClick={() => setShowCreate((v) => !v)}>
            {showCreate ? "收起" : "新建课程"}
          </button>
        ) : (
          <div style={{ display: "flex", gap: 8 }}>
            <input
              className="input"
              style={{ width: 150 }}
              value={joinCode}
              onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
              placeholder="课程邀请码"
            />
            <button className="btn primary" onClick={() => join.mutate(joinCode)} disabled={!joinCode.trim() || join.isPending}>
              {join.isPending ? "加入中…" : "加入课程"}
            </button>
          </div>
        )}
      </div>

      {joinError && (
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
          {joinError}
        </div>
      )}

      {isTeacher && showCreate && (
        <div className="card rise" style={{ padding: 20, marginBottom: 20 }}>
          <div className="field">
            <label>课程名称</label>
            <input
              className="input"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="数据结构与算法"
            />
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            <div className="field" style={{ flex: 1 }}>
              <label>课程编号</label>
              <input
                className="input"
                value={form.code}
                onChange={(e) => setForm({ ...form, code: e.target.value })}
                placeholder="CS201"
              />
            </div>
            <div className="field" style={{ flex: 1 }}>
              <label>学期</label>
              <input
                className="input"
                value={form.term}
                onChange={(e) => setForm({ ...form, term: e.target.value })}
                placeholder="2026 秋"
              />
            </div>
          </div>
          <button className="btn primary" onClick={() => create.mutate(form)} disabled={create.isPending}>
            创建课程
          </button>
          {createError && (
            <div
              style={{
                background: "var(--red-soft)",
                color: "var(--red)",
                padding: "8px 12px",
                borderRadius: 6,
                marginTop: 12,
                fontSize: 13,
              }}
            >
              {createError}
            </div>
          )}
        </div>
      )}

      {isLoading ? (
        <div className="empty">加载中…</div>
      ) : !courses?.length ? (
        <div className="empty">
          {isTeacher ? "还没有课程，点击「新建课程」开始" : "还没有加入课程，输入邀请码加入"}
        </div>
      ) : (
        <div className="card-list">
          {courses.map((c, i) => (
            <div
              key={c.id}
              className="card-row rise"
              style={{ animationDelay: `${i * 0.05}s`, cursor: "pointer" }}
              onClick={() => enter(c)}
            >
              <div className="grow">
                <div className="card-title">{c.name}</div>
                <div className="card-meta">
                  {c.code}
                  {c.term ? ` · ${c.term}` : ""}
                  {isTeacher ? ` · 邀请码 ${c.join_code}` : ""}
                </div>
              </div>
              {isTeacher && (
                <>
                  <button
                    className="btn sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleEdit(c);
                    }}
                  >
                    编辑
                  </button>
                  <button
                    className="btn sm danger"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(c);
                    }}
                    disabled={deleteCourse.isPending}
                  >
                    删除
                  </button>
                </>
              )}
              <span className="faint">进入 →</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
