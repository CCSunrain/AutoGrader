import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Course } from "../api/types";

export default function Dashboard() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", code: "", term: "" });

  const { data: courses, isLoading } = useQuery<Course[]>({
    queryKey: ["courses"],
    queryFn: () => api.get<Course[]>("/courses"),
  });

  const create = useMutation({
    mutationFn: (body: { name: string; code: string; term: string }) =>
      api.post<Course>("/courses", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["courses"] });
      setShowCreate(false);
      setForm({ name: "", code: "", term: "" });
    },
  });

  return (
    <div className="container">
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 20 }}>
        <div>
          <h1 className="page-title">我的课程</h1>
          <div className="page-sub">管理实验报告评阅的课程与作业</div>
        </div>
        <button className="btn primary" onClick={() => setShowCreate((v) => !v)}>
          {showCreate ? "收起" : "新建课程"}
        </button>
      </div>

      {showCreate && (
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
        </div>
      )}

      {isLoading ? (
        <div className="empty">加载中…</div>
      ) : !courses?.length ? (
        <div className="empty">还没有课程，点击「新建课程」开始</div>
      ) : (
        <div className="card-list">
          {courses.map((c, i) => (
            <Link
              key={c.id}
              to={`/courses/${c.id}`}
              className="card-row rise"
              style={{ animationDelay: `${i * 0.05}s` }}
            >
              <div className="grow">
                <div className="card-title">{c.name}</div>
                <div className="card-meta">
                  {c.code}
                  {c.term ? ` · ${c.term}` : ""}
                </div>
              </div>
              <span className="faint">进入 →</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
