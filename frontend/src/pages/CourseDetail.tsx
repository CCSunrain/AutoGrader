import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Assignment, AssignmentStats, Course, Review, Rubric, Submission } from "../api/types";

const SORTING_TEMPLATE = {
  title: "排序算法实验评分量表",
  description: "适用于排序算法实验报告",
  items: [
    {
      name: "算法实现正确性",
      description: "代码是否实现正确、可运行",
      max_score: 40,
      order_index: 0,
      bands: [
        { level: "优秀", score: 40, order_index: 0 },
        { level: "良好", score: 30, order_index: 1 },
        { level: "及格", score: 20, order_index: 2 },
        { level: "不及格", score: 0, order_index: 3 },
      ],
    },
    {
      name: "复杂度分析",
      description: "时间与空间复杂度分析是否正确",
      max_score: 30,
      order_index: 1,
      bands: [
        { level: "优秀", score: 30, order_index: 0 },
        { level: "良好", score: 20, order_index: 1 },
        { level: "及格", score: 10, order_index: 2 },
        { level: "不及格", score: 0, order_index: 3 },
      ],
    },
    {
      name: "实验数据与结论",
      description: "实验数据是否完整、结论是否合理",
      max_score: 30,
      order_index: 2,
      bands: [
        { level: "优秀", score: 30, order_index: 0 },
        { level: "良好", score: 20, order_index: 1 },
        { level: "及格", score: 10, order_index: 2 },
        { level: "不及格", score: 0, order_index: 3 },
      ],
    },
  ],
};

const SHORTEST_PATH_TEMPLATE = {
  title: "最短路径算法实验评分量表",
  description: "适用于最短路径算法实验报告",
  items: [
    {
      name: "算法实现正确性",
      description: "Dijkstra/Floyd 等算法实现是否正确",
      max_score: 40,
      order_index: 0,
      bands: [
        { level: "优秀", score: 40, order_index: 0 },
        { level: "良好", score: 30, order_index: 1 },
        { level: "及格", score: 20, order_index: 2 },
        { level: "不及格", score: 0, order_index: 3 },
      ],
    },
    {
      name: "复杂度分析",
      description: "时间与空间复杂度分析是否正确",
      max_score: 30,
      order_index: 1,
      bands: [
        { level: "优秀", score: 30, order_index: 0 },
        { level: "良好", score: 20, order_index: 1 },
        { level: "及格", score: 10, order_index: 2 },
        { level: "不及格", score: 0, order_index: 3 },
      ],
    },
    {
      name: "实验数据与结论",
      description: "测试图数据与最短路径结论是否合理",
      max_score: 30,
      order_index: 2,
      bands: [
        { level: "优秀", score: 30, order_index: 0 },
        { level: "良好", score: 20, order_index: 1 },
        { level: "及格", score: 10, order_index: 2 },
        { level: "不及格", score: 0, order_index: 3 },
      ],
    },
  ],
};

export default function CourseDetail() {
  const { courseId } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [tab, setTab] = useState<"assignments" | "rubrics">("assignments");
  const [showCreateAssignment, setShowCreateAssignment] = useState(false);
  const [assignmentForm, setAssignmentForm] = useState({ title: "", description: "" });

  const { data: course } = useQuery<Course>({
    queryKey: ["course", courseId],
    queryFn: () => api.get<Course>(`/courses/${courseId}`),
  });

  const { data: assignments } = useQuery<Assignment[]>({
    queryKey: ["assignments", courseId],
    queryFn: () => api.get<Assignment[]>(`/courses/${courseId}/assignments`),
  });

  const { data: rubrics } = useQuery<Rubric[]>({
    queryKey: ["rubrics"],
    queryFn: () => api.get<Rubric[]>("/rubrics"),
  });

  const createAssignment = useMutation({
    mutationFn: (body: { course_id: string; title: string; description: string }) =>
      api.post<Assignment>("/assignments", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["assignments", courseId] });
      setShowCreateAssignment(false);
      setAssignmentForm({ title: "", description: "" });
    },
  });

  const createRubric = useMutation({
    mutationFn: (body: unknown) => api.post<Rubric>("/rubrics", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rubrics"] }),
  });

  return (
    <div className="container">
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 12 }}>
        <div>
          <Link to="/" className="faint" style={{ fontSize: 13 }}>
            ← 返回课程
          </Link>
          <h1 className="page-title" style={{ marginTop: 4 }}>
            {course?.name}
          </h1>
          <div className="page-sub" style={{ marginBottom: 0 }}>
            {course?.code}
            {course?.term ? ` · ${course.term}` : ""}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className={tab === "assignments" ? "btn primary" : "btn"} onClick={() => setTab("assignments")}>
            作业
          </button>
          <button className={tab === "rubrics" ? "btn primary" : "btn"} onClick={() => setTab("rubrics")}>
            评分量表
          </button>
        </div>
      </div>

      {tab === "assignments" ? (
        <div>
          <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 14 }}>
            <button className="btn" onClick={() => setShowCreateAssignment((v) => !v)}>
              {showCreateAssignment ? "收起" : "新建作业"}
            </button>
          </div>

          {showCreateAssignment && (
            <div className="card rise" style={{ padding: 20, marginBottom: 16 }}>
              <div className="field">
                <label>作业标题</label>
                <input
                  className="input"
                  value={assignmentForm.title}
                  onChange={(e) => setAssignmentForm({ ...assignmentForm, title: e.target.value })}
                  placeholder="排序算法实验"
                />
              </div>
              <div className="field">
                <label>说明</label>
                <textarea
                  className="textarea"
                  rows={2}
                  value={assignmentForm.description}
                  onChange={(e) => setAssignmentForm({ ...assignmentForm, description: e.target.value })}
                  placeholder="实现并分析排序算法"
                />
              </div>
              <button
                className="btn primary"
                onClick={() => createAssignment.mutate({ course_id: courseId!, ...assignmentForm })}
                disabled={createAssignment.isPending}
              >
                创建作业
              </button>
            </div>
          )}

          {!assignments?.length ? (
            <div className="empty">还没有作业，点击「新建作业」开始</div>
          ) : (
            <div className="card-list">
              {assignments.map((a) => (
                <AssignmentCard key={a.id} assignment={a} rubrics={rubrics ?? []} onNavigate={navigate} />
              ))}
            </div>
          )}
        </div>
      ) : (
        <div>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginBottom: 14 }}>
            <button className="btn" onClick={() => createRubric.mutate(SHORTEST_PATH_TEMPLATE)} disabled={createRubric.isPending}>
              + 最短路径量表
            </button>
            <button className="btn primary" onClick={() => createRubric.mutate(SORTING_TEMPLATE)} disabled={createRubric.isPending}>
              + 排序实验量表
            </button>
          </div>
          {!rubrics?.length ? (
            <div className="empty">还没有量表，点击上方按钮从模板创建</div>
          ) : (
            <div className="card-list">
              {rubrics.map((r) => (
                <div key={r.id} className="card-row">
                  <div className="grow">
                    <div className="card-title">{r.title}</div>
                    <div className="card-meta">
                      版本 {r.versions.length} · {r.versions[0]?.items.length ?? 0} 个评分项
                      {r.versions[0]?.frozen_at ? " · 已冻结" : ""}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function AssignmentCard({
  assignment,
  rubrics,
  onNavigate,
}: {
  assignment: Assignment;
  rubrics: Rubric[];
  onNavigate: (path: string) => void;
}) {
  const qc = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const [showStats, setShowStats] = useState(false);
  const [studentId, setStudentId] = useState("stu-1");
  const [rubricVersionId, setRubricVersionId] = useState(rubrics[0]?.versions[0]?.id ?? "");
  const fileRef = { current: null as HTMLInputElement | null };

  const { data: submissions } = useQuery<Submission[]>({
    queryKey: ["submissions", assignment.id],
    queryFn: () => api.get<Submission[]>(`/assignments/${assignment.id}/submissions`),
    enabled: expanded,
  });

  const upload = useMutation({
    mutationFn: (file: File) =>
      api.upload<Submission>(`/assignments/${assignment.id}/submissions`, file, { student_id: studentId }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["submissions", assignment.id] }),
  });

  return (
    <div className="card-row" style={{ alignItems: "flex-start", flexDirection: "column", gap: 10 }}>
      <div style={{ display: "flex", alignItems: "center", width: "100%" }}>
        <div className="grow">
          <div className="card-title">{assignment.title}</div>
          <div className="card-meta">{assignment.description}</div>
        </div>
        <button className="btn sm" onClick={() => setShowStats((v) => !v)}>
          {showStats ? "隐藏统计" : "统计"}
        </button>
        <button className="btn sm" onClick={() => setExpanded((v) => !v)}>
          {expanded ? "收起" : "管理提交"}
        </button>
      </div>

      {showStats && <StatsBox assignmentId={assignment.id} />}

      {expanded && (
        <div style={{ width: "100%", borderTop: "1px solid var(--line)", paddingTop: 12 }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 12 }}>
            <input
              className="input"
              style={{ width: 140 }}
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
              placeholder="学生 ID"
            />
            <input
              type="file"
              accept=".pdf,.md,.markdown"
              style={{ display: "none" }}
              ref={(el) => (fileRef.current = el)}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) upload.mutate(f);
              }}
            />
            <button className="btn primary sm" onClick={() => fileRef.current?.click()} disabled={upload.isPending}>
              {upload.isPending ? "上传中…" : "上传报告"}
            </button>
          </div>

          {!submissions?.length ? (
            <div className="faint" style={{ fontSize: 13 }}>
              暂无提交
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {submissions.map((s) => {
                const latest = s.versions[s.versions.length - 1];
                return (
                  <div key={s.id} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13 }}>
                    <span className="mono faint">{s.student_id}</span>
                    <span>v{latest.version_no}</span>
                    <span className="faint">{latest.filename}</span>
                    <span className="grow" />
                    <button className="btn sm" onClick={() => onNavigate(`/submissions/${s.id}/result`)}>
                      结果
                    </button>
                    {s.versions.length >= 2 && (
                      <button
                        className="btn sm"
                        onClick={() => onNavigate(`/submissions/${s.id}/compare/${s.versions[0].id}/${latest.id}`)}
                      >
                        对比
                      </button>
                    )}
                    <ReviewButton
                      submission={s}
                      rubricVersionId={rubricVersionId}
                      onNavigate={onNavigate}
                    />
                  </div>
                );
              })}
            </div>
          )}

          <div style={{ marginTop: 12, display: "flex", gap: 8, alignItems: "center" }}>
            <label className="faint" style={{ fontSize: 12 }}>
              评阅量表：
            </label>
            <select className="select" style={{ width: 260 }} value={rubricVersionId} onChange={(e) => setRubricVersionId(e.target.value)}>
              {rubrics.flatMap((r) =>
                r.versions.map((v) => (
                  <option key={v.id} value={v.id}>
                    {r.title} v{v.version_no}
                  </option>
                ))
              )}
            </select>
          </div>
        </div>
      )}
    </div>
  );
}

function ReviewButton({
  submission,
  rubricVersionId,
  onNavigate,
}: {
  submission: Submission;
  rubricVersionId: string;
  onNavigate: (path: string) => void;
}) {
  const qc = useQueryClient();
  const version = submission.versions[submission.versions.length - 1];

  const { data: reviews } = useQuery<Review[]>({
    queryKey: ["reviews", version.id],
    queryFn: () => api.get<Review[]>(`/submission-versions/${version.id}/reviews`),
  });

  const startReview = useMutation({
    mutationFn: () => api.post<Review>(`/submission-versions/${version.id}/reviews`, { rubric_version_id: rubricVersionId }),
    onSuccess: (r) => onNavigate(`/reviews/${r.id}`),
  });

  const latest = reviews?.[0];
  if (latest) {
    return (
      <button className="btn sm" onClick={() => onNavigate(`/reviews/${latest.id}`)}>
        评阅台{latest.status === "published" ? " · 已发布" : ""}
      </button>
    );
  }
  return (
    <button className="btn sm primary" onClick={() => startReview.mutate()} disabled={!rubricVersionId}>
      发起评阅
    </button>
  );
}

function StatsBox({ assignmentId }: { assignmentId: string }) {
  const { data, isLoading } = useQuery<AssignmentStats>({
    queryKey: ["stats", assignmentId],
    queryFn: () => api.get<AssignmentStats>(`/assignments/${assignmentId}/stats`),
  });

  if (isLoading) return <div className="faint" style={{ fontSize: 13, padding: "8px 0" }}>统计加载中…</div>;
  if (!data) return null;

  return (
    <div style={{ width: "100%", borderTop: "1px solid var(--line)", paddingTop: 12, fontSize: 13 }}>
      <div style={{ display: "flex", gap: 28, marginBottom: 10 }}>
        <div>
          <span className="faint">已发布 </span>
          <b>{data.published_count}</b> 份
        </div>
        {data.avg_score !== null && (
          <div>
            <span className="faint">平均分 </span>
            <b style={{ fontFamily: "var(--serif)" }}>{data.avg_score}</b>
          </div>
        )}
        {data.max_score !== null && (
          <div>
            <span className="faint">最高 </span>
            <b>{data.max_score}</b>
          </div>
        )}
        {data.min_score !== null && (
          <div>
            <span className="faint">最低 </span>
            <b>{data.min_score}</b>
          </div>
        )}
      </div>
      {data.item_avg.length > 0 && (
        <div>
          <div className="faint" style={{ marginBottom: 6 }}>各评分项平均分（满分）</div>
          {data.item_avg.map((it) => (
            <div key={it.rubric_item_name} style={{ display: "flex", gap: 8, marginBottom: 4 }}>
              <span style={{ minWidth: 140 }}>{it.rubric_item_name}</span>
              <span className="mono">
                {it.avg_score} / {it.max_score}
              </span>
              <div
                style={{
                  width: 160,
                  height: 6,
                  background: "var(--paper-deep)",
                  borderRadius: 3,
                  overflow: "hidden",
                  alignSelf: "center",
                }}
              >
                <div
                  style={{
                    width: `${(it.avg_score / it.max_score) * 100}%`,
                    height: "100%",
                    background: "var(--brand)",
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
