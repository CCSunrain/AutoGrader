import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Evidence, ParsedDocument, Review, RubricVersion } from "../api/types";
import HelpGuide from "../components/HelpGuide";

const STATE_LABEL: Record<string, string> = {
  supported: "有证据支持",
  missing: "内容缺失",
  uncertain: "无法确定",
};

function highlight(text: string, evidences: Evidence[]) {
  if (!evidences.length) return text;
  const sorted = [...evidences].sort((a, b) => a.start_offset - b.start_offset);
  const parts: React.ReactNode[] = [];
  let last = 0;
  for (const ev of sorted) {
    if (ev.start_offset < last) continue;
    if (ev.start_offset > last) parts.push(text.slice(last, ev.start_offset));
    parts.push(
      <mark key={ev.id} title={`页 ${ev.page ?? "?"}`}>
        {text.slice(ev.start_offset, ev.end_offset)}
      </mark>
    );
    last = ev.end_offset;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

export default function ReviewDesk() {
  const { reviewId } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState("");
  const [publishFeedback, setPublishFeedback] = useState("");

  const { data: review } = useQuery<Review>({
    queryKey: ["review", reviewId],
    queryFn: () => api.get<Review>(`/reviews/${reviewId}`),
    refetchInterval: (q) => {
      const r = q.state.data;
      return r && (r.status === "pending" || r.status === "running") ? 2000 : false;
    },
  });

  const { data: parsed } = useQuery<ParsedDocument>({
    queryKey: ["parsed", review?.submission_version_id],
    queryFn: () => api.get<ParsedDocument>(`/submission-versions/${review!.submission_version_id}/parsed`),
    enabled: !!review?.submission_version_id,
  });

  const { data: rubricVersion } = useQuery<RubricVersion>({
    queryKey: ["rubric-version", review?.rubric_version_id],
    queryFn: () => api.get<RubricVersion>(`/rubric-versions/${review!.rubric_version_id}`),
    enabled: !!review?.rubric_version_id,
  });

  useEffect(() => {
    if (!selectedId && review?.items?.length) setSelectedId(review.items[0].id);
  }, [review, selectedId]);

  const decision = useMutation({
    mutationFn: (body: { final_band_id: string; feedback: string }) =>
      api.post<Review>(`/review-items/${selected!.id}/decision`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["review", reviewId] });
      setFeedback("");
    },
  });

  const publish = useMutation({
    mutationFn: (body: { feedback: string }) => api.post<Review>(`/reviews/${reviewId}/publish`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["review", reviewId] }),
  });

  const startRevision = useMutation({
    mutationFn: () =>
      api.post<Review>(`/submission-versions/${review!.submission_version_id}/reviews`, {
        rubric_version_id: review!.rubric_version_id,
      }),
    onSuccess: (r) => navigate(`/reviews/${r.id}`),
  });

  if (!review) return <div className="empty">加载中…</div>;

  const selected = review.items.find((i) => i.id === selectedId) ?? review.items[0];
  const rubricItem = rubricVersion?.items.find((i) => i.id === selected?.rubric_item_id);
  const busy = review.status === "pending" || review.status === "running";

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          gap: 14,
          padding: "10px 20px",
          background: "var(--brand-ink)",
          color: "#f3efe5",
        }}
      >
        <Link to="/" style={{ color: "#cfc7b8", fontSize: 13 }}>
          ← 返回
        </Link>
        <span style={{ fontFamily: "var(--serif)", fontWeight: 700 }}>三栏评阅台</span>
        <span className={review.status === "published" ? "badge published" : "badge done"}>
          {busy ? "评阅中…" : review.status === "published" ? "已发布" : "已完成"}
        </span>
        {!busy && (
          <span className="faint" style={{ color: "#a69d8c", fontSize: 12 }}>
            model {review.model} · prompt {review.prompt_version} · rules {review.rules_version}
          </span>
        )}
        <div className="spacer" style={{ flex: 1 }} />
        <HelpGuide />
        {review.status !== "published" && (
          <button
            className="btn sm"
            style={{ background: "var(--amber)", borderColor: "var(--amber)", color: "#26221c" }}
            onClick={() => publish.mutate({ feedback: publishFeedback })}
            disabled={busy || publish.isPending}
          >
            发布成绩
          </button>
        )}
        {review.status === "published" && (
          <button
            className="btn sm"
            style={{ background: "var(--amber)", borderColor: "var(--amber)", color: "#26221c" }}
            onClick={() => startRevision.mutate()}
            disabled={startRevision.isPending}
          >
            发起修订
          </button>
        )}
      </header>

      <div className="desk" style={{ flex: 1, height: "auto" }}>
        {/* 左栏：评分项清单 */}
        <div className="desk-col">
          <div className="desk-col-head">
            <span>评分项</span>
            <span className="faint" style={{ fontSize: 11 }}>
              {review.items.filter((i) => i.decision).length}/{review.items.length} 已复核
            </span>
          </div>
          <div className="desk-col-body">
            {review.contradictions.length > 0 && (
              <div
                style={{
                  border: "1px solid var(--red-soft)",
                  background: "var(--red-soft)",
                  borderRadius: 6,
                  padding: 8,
                  fontSize: 12,
                  marginBottom: 12,
                }}
              >
                <b style={{ color: "var(--red)" }}>⚠ 检测到数值矛盾</b>
                {review.contradictions.map((c, i) => (
                  <div key={i} style={{ marginTop: 4, color: "var(--ink-soft)" }}>
                    {(c.message as string) ?? ""}
                  </div>
                ))}
              </div>
            )}
            {review.items.map((item) => (
              <div
                key={item.id}
                className={`criterion-item ${item.id === selected?.id ? "active" : ""}`}
                onClick={() => setSelectedId(item.id)}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span className="name">
                    {item.order_index + 1}. {rubricItemName(rubricVersion, item.rubric_item_id)}
                  </span>
                  <span className={`badge ${item.evidence_state}`}>{STATE_LABEL[item.evidence_state]}</span>
                </div>
                <div className="meta">
                  {item.decision ? `已定档` : "未复核"}
                  {item.needs_review ? " · 待复核" : ""}
                </div>
                {(item.review_flags ?? []).includes("model_conflict") && (
                  <div style={{ fontSize: 12, color: "var(--red)", marginTop: 4 }}>
                    ⚠ 模型两次判断不一致，建议人工确认
                  </div>
                )}
                {(item.review_flags ?? [])
                  .filter((f) => f.startsWith("contradiction:"))
                  .map((f) => (
                    <div key={f} style={{ fontSize: 12, color: "var(--red)", marginTop: 4 }}>
                      ⚠ {f.slice("contradiction:".length)}
                    </div>
                  ))}
              </div>
            ))}
          </div>
        </div>

        {/* 中栏：原文 + 证据高亮 */}
        <div className="desk-col">
          <div className="desk-col-head">
            <span>报告原文</span>
            <span className="faint" style={{ fontSize: 11 }}>
              {parsed?.status === "done" ? parsed.parser_version : "解析中…"}
            </span>
          </div>
          <div className="desk-col-body">
            {parsed?.raw_text ? (
              <div className="report-body">{highlight(parsed.raw_text, selected?.evidences ?? [])}</div>
            ) : (
              <div className="empty">解析中…</div>
            )}
          </div>
        </div>

        {/* 右栏：建议 + 人工决定 */}
        <div className="desk-col">
          <div className="desk-col-head">
            <span>模型建议 · 人工决定</span>
          </div>
          <div className="desk-col-body">
            {busy ? (
              <div className="empty">模型评阅中，请稍候…</div>
            ) : (
              selected && (
                <>
                  <div className="suggestion-box">
                    <div className="label">模型建议</div>
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <span className={`badge ${selected.evidence_state}`}>{STATE_LABEL[selected.evidence_state]}</span>
                      {selected.needs_review && <span className="badge needs_review">待复核</span>}
                    </div>
                    <div style={{ marginTop: 8, fontSize: 13, color: "var(--ink-soft)" }}>
                      {selected.explanation || "（无说明）"}
                    </div>
                    <div style={{ marginTop: 6, fontSize: 12, color: "var(--ink-faint)" }}>
                      置信度 {(selected.confidence * 100).toFixed(0)}%
                    </div>
                  </div>

                  {selected.evidences.length > 0 && (
                    <div className="suggestion-box">
                      <div className="label">原文证据</div>
                      {selected.evidences.map((ev) => (
                        <div key={ev.id} className="evidence-chip">
                          “{ev.quote}”
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="suggestion-box">
                    <div className="label">人工决定</div>
                    <div className="band-pick">
                      {rubricItem?.bands.map((b) => (
                        <button
                          key={b.id}
                          className={selected.decision?.final_band_id === b.id ? "selected" : ""}
                          onClick={() => {
                            if (review.status === "published") return;
                            decision.mutate({ final_band_id: b.id, feedback });
                          }}
                        >
                          {b.level}（{b.score}分）
                        </button>
                      ))}
                    </div>
                    <textarea
                      className="textarea"
                      rows={2}
                      placeholder="反馈（可选）"
                      value={feedback}
                      onChange={(e) => setFeedback(e.target.value)}
                    />
                    <div style={{ marginTop: 8 }}>
                      <button
                        className="btn primary sm"
                        onClick={() => {
                          const bid = selected.decision?.final_band_id ?? rubricItem?.bands[0]?.id;
                          if (bid) decision.mutate({ final_band_id: bid, feedback });
                        }}
                        disabled={review.status === "published"}
                      >
                        保存决定
                      </button>
                    </div>
                  </div>

                  {review.status === "published" && review.publish && (
                    <div className="suggestion-box" style={{ borderColor: "var(--brand)" }}>
                      <div className="label">已发布成绩</div>
                      <div style={{ fontFamily: "var(--serif)", fontSize: 28, fontWeight: 900, color: "var(--brand)" }}>
                        {review.publish.score} 分
                      </div>
                      <div style={{ fontSize: 13, color: "var(--ink-soft)" }}>{review.publish.feedback}</div>
                    </div>
                  )}
                </>
              )
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function rubricItemName(rubricVersion: RubricVersion | undefined, itemId: string): string {
  return rubricVersion?.items.find((i) => i.id === itemId)?.name ?? itemId.slice(0, 8);
}
