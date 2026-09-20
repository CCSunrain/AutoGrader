import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { VersionCompare, VersionSummary } from "../api/types";

export default function VersionComparePage() {
  const { submissionId, fromVersionId, toVersionId } = useParams();
  const { data, isLoading } = useQuery<VersionCompare>({
    queryKey: ["compare", submissionId, fromVersionId, toVersionId],
    queryFn: () => api.get<VersionCompare>(
      `/submissions/${submissionId}/compare/${fromVersionId}/${toVersionId}`
    ),
  });

  if (isLoading) return <div className="empty">加载中…</div>;
  if (!data) return <div className="empty">无数据</div>;

  const delta = data.score_delta;
  return (
    <div className="container">
      <Link to="/" className="faint" style={{ fontSize: 13 }}>
        ← 返回
      </Link>
      <h1 className="page-title" style={{ marginTop: 4 }}>版本对比</h1>
      <div className="page-sub">
        v{data.from_version.version_no} → v{data.to_version.version_no}
        {delta !== null && (
          <span style={{ color: delta >= 0 ? "var(--green)" : "var(--red)", fontWeight: 700 }}>
            {"  ·  分数变化 "}
            {delta >= 0 ? "+" : ""}
            {delta}
          </span>
        )}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <VersionPane label={`v${data.from_version.version_no}`} summary={data.from_version} />
        <VersionPane label={`v${data.to_version.version_no}`} summary={data.to_version} />
      </div>
    </div>
  );
}

function VersionPane({ label, summary }: { label: string; summary: VersionSummary }) {
  return (
    <div className="card" style={{ padding: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <b style={{ fontFamily: "var(--serif)" }}>{label}</b>
        {summary.score !== null ? (
          <span style={{ fontFamily: "var(--serif)", fontWeight: 900, fontSize: 20, color: "var(--brand)" }}>
            {summary.score} 分
          </span>
        ) : (
          <span className="badge missing">未发布</span>
        )}
      </div>
      {summary.feedback && (
        <div className="faint" style={{ fontSize: 13, marginBottom: 8 }}>
          {summary.feedback}
        </div>
      )}
      <div className="report-body" style={{ whiteSpace: "pre-wrap", fontSize: 13 }}>
        {summary.raw_text || "（未解析）"}
      </div>
    </div>
  );
}
