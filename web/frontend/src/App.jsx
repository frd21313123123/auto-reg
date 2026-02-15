import { useEffect, useState } from "react";

import { authApi } from "./api";
import AuthView from "./components/AuthView";
import Dashboard from "./components/Dashboard";

const TOKEN_KEY = "auto_reg_web_token";

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);

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
        localStorage.removeItem(TOKEN_KEY);
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
    localStorage.setItem(TOKEN_KEY, nextToken);
    setToken(nextToken);
    setUser(nextUser);
  };

  const handleLogout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  };

  if (checking) {
    return <div className="boot-loader">Проверка сессии...</div>;
  }

  if (!token || !user) {
    return <AuthView onAuthSuccess={handleAuthSuccess} />;
  }

  return <Dashboard token={token} user={user} onLogout={handleLogout} />;
}
