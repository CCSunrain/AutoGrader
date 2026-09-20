import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { Published } from "../api/types";

export default function StudentResult() {
  const { submissionId } = useParams();
  const { data, isLoading, error } = useQuery<Published>({
    queryKey: ["published", submissionId],
    queryFn: () => api.get<Published>(`/submissions/${submissionId}/published`),
  });

  if (isLoading) return <div className="empty">加载中…</div>;
  if (error) return <div className="empty">{(error as Error).message}</div>;
  if (!data) return <div className="empty">暂无已发布结果</div>;

  return (
    <div className="container" style={{ maxWidth: 760 }}>
      <h1 className="page-title">实验报告评阅结果</h1>
      <div className="page-sub">
        版本 v{data.version_no} · {new Date(data.published_at).toLocaleString("zh-CN")}
      </div>

      <div className="card" style={{ padding: 28, marginBottom: 16, textAlign: "center" }}>
        <div style={{ fontSize: 13, color: "var(--ink-soft)" }}>总分</div>
        <div style={{ fontFamily: "var(--serif)", fontSize: 52, fontWeight: 900, color: "var(--brand)", lineHeight: 1.1 }}>
          {data.score}
        </div>
        <div style={{ color: "var(--ink-soft)", fontSize: 14, marginTop: 8 }}>{data.feedback || "—"}</div>
      </div>

      <div className="card-list">
        {data.items.map((it, i) => (
          <div key={i} className="card-row rise" style={{ animationDelay: `${i * 0.05}s` }}>
            <div className="grow">
              <div className="card-title">{it.rubric_item_name}</div>
              {it.feedback && <div className="card-meta">{it.feedback}</div>}
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontFamily: "var(--serif)", fontSize: 20, fontWeight: 700 }}>{it.score} 分</div>
              <span className="badge supported">{it.final_band_level}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
