import { Component, useEffect, useState } from "react";

import { authApi } from "./api";
import AuthView from "./components/AuthView";
import Dashboard from "./components/Dashboard";
import GeneratorPopup from "./components/GeneratorPopup";

const TOKEN_KEY = "auto_reg_web_token";

function readStoredToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
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

function clearStoredToken() {
  try {
    localStorage.removeItem(TOKEN_KEY);
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
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);
  const popupKind = resolvePopupKind();

  useEffect(() => {
    let active = true;

    async function validateToken() {
      if (!token) {
        if (active) {
          setUser(null);
          setChecking(false);
        }
        return;
      }

      try {
        const currentUser = await authApi.me(token);
        if (active) {
          setUser(currentUser);
        }
      } catch {
        clearStoredToken();
        if (active) {
          setToken(null);
          setUser(null);
        }
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
    setToken(nextToken);
    setUser(nextUser);
  };

  const handleLogout = () => {
    clearStoredToken();
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
