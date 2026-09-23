import { useState } from "react";

interface BandDraft {
  level: string;
  score: number;
}

interface ItemDraft {
  name: string;
  description: string;
  max_score: number;
  bands: BandDraft[];
}

export interface RubricDraft {
  title: string;
  description: string;
  items: ItemDraft[];
}

function emptyItem(): ItemDraft {
  return {
    name: "",
    description: "",
    max_score: 10,
    bands: [
      { level: "优秀", score: 10 },
      { level: "及格", score: 0 },
    ],
  };
}

export default function RubricEditor({
  initial,
  onSave,
  onClose,
}: {
  initial?: RubricDraft;
  onSave: (draft: RubricDraft) => void;
  onClose: () => void;
}) {
  const [title, setTitle] = useState(initial?.title ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [items, setItems] = useState<ItemDraft[]>(initial?.items ?? [emptyItem()]);

  function updateItem(i: number, patch: Partial<ItemDraft>) {
    setItems((prev) => prev.map((it, idx) => (idx === i ? { ...it, ...patch } : it)));
  }

  function updateBand(i: number, b: number, patch: Partial<BandDraft>) {
    setItems((prev) =>
      prev.map((it, idx) =>
        idx === i
          ? { ...it, bands: it.bands.map((bd, j) => (j === b ? { ...bd, ...patch } : bd)) }
          : it
      )
    );
  }

  function submit() {
    const draft: RubricDraft = {
      title,
      description,
      items: items.map((it, i) => ({
        name: it.name,
        description: it.description,
        max_score: it.max_score,
        order_index: i,
        bands: it.bands.map((b, j) => ({ level: b.level, score: b.score, order_index: j })),
      })),
    };
    onSave(draft);
  }

  return (
    <div className="help-overlay" onClick={onClose}>
      <div className="help-panel" style={{ maxWidth: 760 }} onClick={(e) => e.stopPropagation()}>
        <header className="help-head">
          <h2>{initial ? "编辑评分量表" : "新建评分量表"}</h2>
          <button className="help-close" onClick={onClose} aria-label="关闭">
            ×
          </button>
        </header>

        <div className="help-body">
          <div className="field">
            <label>量表名称</label>
            <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="排序算法实验评分量表" />
          </div>
          <div className="field">
            <label>说明（可选）</label>
            <input className="input" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="适用于……" />
          </div>

          {items.map((it, i) => (
            <div key={i} className="suggestion-box" style={{ background: "var(--paper)" }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
                <span className="badge done">{i + 1}</span>
                <input
                  className="input"
                  style={{ flex: 1 }}
                  value={it.name}
                  onChange={(e) => updateItem(i, { name: e.target.value })}
                  placeholder="评分项名称（如：算法实现正确性）"
                />
                <label className="faint" style={{ fontSize: 12 }}>满分</label>
                <input
                  className="input"
                  style={{ width: 70 }}
                  type="number"
                  value={it.max_score}
                  onChange={(e) => updateItem(i, { max_score: Number(e.target.value) })}
                />
                <button className="btn sm danger" onClick={() => setItems((p) => p.filter((_, idx) => idx !== i))}>
                  删
                </button>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {it.bands.map((bd, b) => (
                  <div key={b} style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <span className="faint" style={{ fontSize: 12, minWidth: 40 }}>档位</span>
                    <input
                      className="input"
                      style={{ width: 120 }}
                      value={bd.level}
                      onChange={(e) => updateBand(i, b, { level: e.target.value })}
                      placeholder="优秀/良好/…"
                    />
                    <span className="faint" style={{ fontSize: 12 }}>分值</span>
                    <input
                      className="input"
                      style={{ width: 80 }}
                      type="number"
                      value={bd.score}
                      onChange={(e) => updateBand(i, b, { score: Number(e.target.value) })}
                    />
                    <button className="btn sm danger" onClick={() => updateItem(i, { bands: it.bands.filter((_, j) => j !== b) })}>
                      删
                    </button>
                  </div>
                ))}
              </div>

              <button className="btn sm" style={{ marginTop: 8 }} onClick={() => updateItem(i, { bands: [...it.bands, { level: "", score: 0 }] })}>
                + 添加档位
              </button>
            </div>
          ))}

          <button className="btn" onClick={() => setItems((p) => [...p, emptyItem()])}>
            + 添加评分项
          </button>

          <div style={{ marginTop: 20, display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <button className="btn" onClick={onClose}>取消</button>
            <button className="btn primary" onClick={submit} disabled={!title.trim() || items.some((it) => !it.name.trim() || it.bands.length === 0)}>
              保存
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
