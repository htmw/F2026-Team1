const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export function assetUrl(path) {
  return path ? `${API_URL}${path}` : null;
}

async function request(path, options = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    credentials: "include",
    ...options,
  });

  if (res.status === 204) return null;

  const body = await res.json().catch(() => null);

  if (!res.ok) {
    const detail = Array.isArray(body?.detail)
      ? "Invalid request"
      : body?.detail;
    const error = new Error(detail ?? res.statusText);
    error.status = res.status;
    throw error;
  }

  return body;
}

export function apiGet(path) {
  return request(path);
}

export function apiPost(path, data) {
  return request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: data === undefined ? undefined : JSON.stringify(data),
  });
}

export function apiUpload(path, formData) {
  return request(path, { method: "POST", body: formData });
}

export function apiDelete(path) {
  return request(path, { method: "DELETE" });
}

// export async function devAutoLogin() {
//   if (!import.meta.env.DEV) return;

//   await apiPost("/auth/login", {
//     email: import.meta.env.VITE_DEV_EMAIL,
//     password: import.meta.env.VITE_DEV_PASSWORD,
//   }).catch(() => {});
// }
