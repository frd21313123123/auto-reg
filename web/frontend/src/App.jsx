import { Component, useEffect, useState } from "react";

import { authApi } from "./api";
import AuthView from "./components/AuthView";
import Dashboard from "./components/Dashboard";
import GeneratorPopup from "./components/GeneratorPopup";

const TOKEN_KEY = "auto_reg_web_token";
const USER_KEY = "auto_reg_web_user";

function readStoredToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function readStoredUser() {
  try {
    const rawValue = localStorage.getItem(USER_KEY);
    if (!rawValue) {
      return null;
    }

    const parsed = JSON.parse(rawValue);
    return parsed && typeof parsed === "object" ? parsed : null;
  } catch {
    return null;
  }
}

function writeStoredToken(token) {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    return false;
  }
  return true;
}

function writeStoredUser(user) {
  try {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  } catch {
    return false;
  }
  return true;
}

function clearStoredToken() {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    return false;
  }
  return true;
}

function clearStoredUser() {
  try {
    localStorage.removeItem(USER_KEY);
  } catch {
    return false;
  }
  return true;
}

function resolvePopupKind() {
  const params = new URLSearchParams(window.location.search);
  const popupKind = params.get("popup");
  return popupKind === "in" || popupKind === "sk" ? popupKind : null;
}

class AppErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="boot-loader">
          Интерфейс не загрузился. Обновите страницу. Если не поможет, очистите данные сайта.
        </div>
      );
    }

    return this.props.children;
  }
}

function AppContent() {
  const [token, setToken] = useState(() => readStoredToken());
  const [user, setUser] = useState(() => readStoredUser());
  const [checking, setChecking] = useState(true);
  const popupKind = resolvePopupKind();

  useEffect(() => {
    let active = true;

    async function validateToken() {
      if (!token) {
        if (active) {
          clearStoredUser();
          setUser(null);
          setChecking(false);
        }
        return;
      }

      try {
        const currentUser = await authApi.me(token);
        if (active) {
          writeStoredUser(currentUser);
          setUser(currentUser);
        }
      } catch (error) {
        if (!active) {
          return;
        }

        if (error?.status === 401) {
          clearStoredToken();
          clearStoredUser();
          setToken(null);
          setUser(null);
          return;
        }

        setUser((currentUser) => currentUser || readStoredUser());
      } finally {
        if (active) {
          setChecking(false);
        }
      }
    }

    validateToken();

    return () => {
      active = false;
    };
  }, [token]);

  const handleAuthSuccess = (nextToken, nextUser) => {
    writeStoredToken(nextToken);
    writeStoredUser(nextUser);
    setToken(nextToken);
    setUser(nextUser);
  };

  const handleLogout = () => {
    clearStoredToken();
    clearStoredUser();
    setToken(null);
    setUser(null);
  };

  if (checking) {
    return <div className="boot-loader">Проверка сессии...</div>;
  }

  if (!token || !user) {
    return <AuthView onAuthSuccess={handleAuthSuccess} />;
  }

  if (popupKind) {
    return <GeneratorPopup token={token} kind={popupKind} onLogout={handleLogout} />;
  }

  return <Dashboard token={token} user={user} onLogout={handleLogout} />;
}

export default function App() {
  return (
    <AppErrorBoundary>
      <AppContent />
    </AppErrorBoundary>
  );
}
