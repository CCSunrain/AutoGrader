const TOKEN_KEY = "autograder_token";
const WORKSPACE_KEY = "autograder_workspace";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

let _workspaceId: string | null = null;

export function getWorkspaceId(): string | null {
  if (_workspaceId === null) {
    _workspaceId = localStorage.getItem(WORKSPACE_KEY) || "";
  }
  return _workspaceId || null;
}

export function setWorkspaceId(id: string | null) {
  _workspaceId = id;
  if (id) localStorage.setItem(WORKSPACE_KEY, id);
  else localStorage.removeItem(WORKSPACE_KEY);
}

// ---- 全局错误通知（用于写操作失败时弹出提示，避免静默失败）----
type ApiErrorListener = (msg: string) => void;
const errorListeners: ApiErrorListener[] = [];

export function onApiError(listener: ApiErrorListener): () => void {
  errorListeners.push(listener);
  return () => {
    const i = errorListeners.indexOf(listener);
    if (i >= 0) errorListeners.splice(i, 1);
  };
}

function emitApiError(msg: string) {
  errorListeners.forEach((l) => l(msg));
}

type RequestOptions = RequestInit & { silent?: boolean };

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { silent, ...init } = options;
  const token = getToken();
  const ws = getWorkspaceId();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init.headers as Record<string, string>) || {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (ws) headers["X-Workspace-Id"] = ws;

  const res = await fetch(`/api${path}`, { ...init, headers });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    let msg = text;
    try {
      const j = JSON.parse(text);
      msg = j.detail || j.message || text;
    } catch {
      /* keep raw text */
    }
    const errMsg = msg || `HTTP ${res.status}`;
    // 写操作（非 GET）失败时全局提示；GET 属于后台查询，轮询失败不应打扰用户
    const method = (init.method || "GET").toUpperCase();
    if (!silent && method !== "GET") emitApiError(errMsg);
    throw new Error(errMsg);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown, silent?: boolean) =>
    request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body), silent }),
  patch: <T>(path: string, body?: unknown, silent?: boolean) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body), silent }),
  put: <T>(path: string, body?: unknown, silent?: boolean) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body), silent }),
  del: <T>(path: string, silent?: boolean) => request<T>(path, { method: "DELETE", silent }),
  upload: async <T>(path: string, file: File, extra: Record<string, string> = {}, silent?: boolean): Promise<T> => {
    const token = getToken();
    const ws = getWorkspaceId();
    const fd = new FormData();
    fd.append("file", file);
    Object.entries(extra).forEach(([k, v]) => fd.append(k, v));
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (ws) headers["X-Workspace-Id"] = ws;
    const res = await fetch(`/api${path}`, {
      method: "POST",
      headers,
      body: fd,
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      let msg = text;
      try {
        const j = JSON.parse(text);
        msg = j.detail || j.message || text;
      } catch {
        /* keep raw text */
      }
      const errMsg = msg || `HTTP ${res.status}`;
      if (!silent) emitApiError(errMsg);
      throw new Error(errMsg);
    }
    return res.json() as Promise<T>;
  },
};
