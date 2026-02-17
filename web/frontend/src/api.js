function resolveApiBase() {
  const envBase = import.meta.env.VITE_API_URL;
  if (envBase && String(envBase).trim()) {
    return String(envBase).trim();
  }
  const hostname = (window.location.hostname || "").toLowerCase();
  if (hostname.endsWith(".github.io")) {
    return "";
  }
  const host = window.location.hostname || "127.0.0.1";
  return `http://${host}:8000/api`;
}

const API_BASE = resolveApiBase();

function buildUrl(path, query) {
  if (!API_BASE) {
    throw new Error(
      "API URL is not configured for this deployment. Set VITE_API_URL during build."
    );
  }
  const base = API_BASE.endsWith("/") ? API_BASE.slice(0, -1) : API_BASE;
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const baseAbsolute =
    base.startsWith("http://") || base.startsWith("https://")
      ? base
      : `${window.location.origin}${base.startsWith("/") ? "" : "/"}${base}`;
  const url = new URL(`${baseAbsolute}${normalizedPath}`);
  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value === undefined || value === null || value === "") {
        return;
      }
      url.searchParams.set(key, String(value));
    });
  }
  return url;
}

async function request(path, options = {}) {
  const { method = "GET", token, body, query } = options;
  const headers = {
    "Content-Type": "application/json"
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let requestUrl;
  try {
    requestUrl = buildUrl(path, query);
  } catch (error) {
    throw new Error(error.message || "API URL build failed");
  }
  let response;
  try {
    response = await fetch(requestUrl, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined
    });
  } catch (error) {
    throw new Error(
      `Cannot reach backend API (${requestUrl}). Ensure backend runs on port 8000 and restart frontend.`
    );
  }

  if (response.status === 204) {
    return null;
  }

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const message = payload?.detail || `Request failed (${response.status})`;
    throw new Error(message);
  }

  return payload;
}

export const authApi = {
  register: (data) => request("/auth/register", { method: "POST", body: data }),
  login: (data) => request("/auth/login", { method: "POST", body: data }),
  me: (token) => request("/auth/me", { token })
};

export const accountsApi = {
  list: (token) => request("/accounts", { token }),
  create: (token, data) => request("/accounts", { method: "POST", token, body: data }),
  createMailTm: (token, passwordLength = 12) =>
    request("/accounts/create-mailtm", {
      method: "POST",
      token,
      body: { password_length: passwordLength }
    }),
  importAccounts: (token, text) =>
    request("/accounts/import", {
      method: "POST",
      token,
      body: { text }
    }),
  updateStatus: (token, accountId, status) =>
    request(`/accounts/${accountId}/status`, {
      method: "PATCH",
      token,
      body: { status }
    }),
  removeMailbox: (token, accountId) =>
    request(`/accounts/${accountId}/mailbox`, {
      method: "DELETE",
      token
    }),
  remove: (token, accountId) =>
    request(`/accounts/${accountId}`, {
      method: "DELETE",
      token
    })
};

export const mailApi = {
  connect: (token, accountId) =>
    request(`/mail/accounts/${accountId}/connect`, {
      method: "POST",
      token
    }),
  messages: (token, accountId) => request(`/mail/accounts/${accountId}/messages`, { token }),
  messageDetail: (token, accountId, messageId, sender, subject) =>
    request(`/mail/accounts/${accountId}/messages/${messageId}`, {
      token,
      query: { sender, subject }
    }),
  banCheckBulk: (token, accountIds = null) =>
    request(`/mail/ban-check/bulk`, {
      method: "POST",
      token,
      body: {
        account_ids: accountIds,
        max_workers: 12
      }
    })
};

export const toolsApi = {
  randomPerson: (token) => request("/tools/random-person", { token }),
  generatorIn: (token) => request("/tools/generator/in", { token }),
  generatorSk: (token) => request("/tools/generator/sk", { token })
};

export { API_BASE };
