import { useEffect, useState } from "react";
import { onApiError } from "../api/client";

interface Toast {
  id: number;
  msg: string;
}

let nextId = 0;

/** 全局错误提示：订阅写操作失败事件，在右上角弹出可自动消失的提示。 */
export default function ToastHost() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    const off = onApiError((msg) => {
      const id = ++nextId;
      setToasts((prev) => [...prev, { id, msg }]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 4500);
    });
    return off;
  }, []);

  if (!toasts.length) return null;

  return (
    <div className="toast-host">
      {toasts.map((t) => (
        <div key={t.id} className="toast toast-error" role="alert">
          <span className="toast-icon">⚠</span>
          <span className="toast-msg">{t.msg}</span>
          <button
            className="toast-close"
            aria-label="关闭"
            onClick={() => setToasts((prev) => prev.filter((x) => x.id !== t.id))}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
