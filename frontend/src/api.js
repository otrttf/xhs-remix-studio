const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000/api";
export const ASSET_BASE = API_BASE.replace("/api", "/assets");

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "请求失败");
  }
  return data;
}

export const api = {
  health: () => request("/health"),
  collect: (payload) => request("/collect", { method: "POST", body: JSON.stringify(payload) }),
  notes: () => request("/notes"),
  personas: () => request("/personas"),
  createPersona: (payload) => request("/personas", { method: "POST", body: JSON.stringify(payload) }),
  updatePersona: (id, payload) => request(`/personas/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  addRule: (personaId, payload) => request(`/personas/${personaId}/rules`, { method: "POST", body: JSON.stringify(payload) }),
  deleteRule: (ruleId) => request(`/persona-rules/${ruleId}`, { method: "DELETE" }),
  generateDraft: (payload) => request("/drafts/generate", { method: "POST", body: JSON.stringify(payload) }),
  drafts: () => request("/drafts"),
  saveDraft: (id, payload) => request(`/drafts/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  suggestRules: (id) => request(`/drafts/${id}/suggest-rules`, { method: "POST" }),
  exportDraft: (id) => request(`/export/drafts/${id}.md`),
  exportDraftLocal: (id) => request(`/export/drafts/${id}/local`, { method: "POST" }),
};
