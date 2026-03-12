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
    const apiError = new Error(error.message || "API URL build failed");
    apiError.code = "API_URL_ERROR";
    throw apiError;
  }
  let response;
  try {
    response = await fetch(requestUrl, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined
    });
  } catch (error) {
    const apiError = new Error(
      `Cannot reach backend API (${requestUrl}). Ensure backend runs on port 8000 and restart frontend.`
    );
    apiError.code = "NETWORK_ERROR";
    throw apiError;
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
    const apiError = new Error(message);
    apiError.status = response.status;
    apiError.code = payload?.code || "HTTP_ERROR";
    throw apiError;
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
  listFolders: (token) => request("/accounts/folders", { token }),
  createFolder: (token, name) =>
    request("/accounts/folders", {
      method: "POST",
      token,
      body: { name }
    }),
  create: (token, data) => request("/accounts", { method: "POST", token, body: data }),
  createMailTm: (token, passwordLength = 12, folderId = null) =>
    request("/accounts/create-mailtm", {
      method: "POST",
      token,
      body: {
        password_length: passwordLength,
        folder_id: folderId
      }
    }),
  importAccounts: (token, text, folderId = null) =>
    request("/accounts/import", {
      method: "POST",
      token,
      body: {
        text,
        folder_id: folderId
      }
    }),
  updateStatus: (token, accountId, status) =>
    request(`/accounts/${accountId}/status`, {
      method: "PATCH",
      token,
      body: { status }
    }),
  moveBulk: (token, accountIds, folderId = null) =>
    request("/accounts/bulk-move", {
      method: "POST",
      token,
      body: {
        account_ids: accountIds,
        folder_id: folderId
      }
    }),
  bulkDelete: (token, accountIds) =>
    request("/accounts/bulk-delete", {
      method: "POST",
      token,
      body: { account_ids: accountIds }
    }),
  deleteAll: (token, payload) =>
    request("/accounts/delete-all", {
      method: "POST",
      token,
      body: payload
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
  banCheckOne: (token, accountId) =>
    request(`/mail/accounts/${accountId}/ban-check`, {
      method: "POST",
      token
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
