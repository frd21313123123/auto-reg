import { useState } from "react";

import { authApi } from "../api";
import ParallaxDotsBackground from "./ParallaxDotsBackground";

export default function AuthView({ onAuthSuccess }) {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const isRegister = mode === "register";

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    if (isRegister && password !== confirmPassword) {
      setError("Пароли не совпадают");
      return;
    }

    try {
      setBusy(true);
      const cleanUsername = username.trim().toLowerCase();

      if (isRegister) {
        await authApi.register({ username: cleanUsername, password });
      }

      const loginResult = await authApi.login({
        username: cleanUsername,
        password
      });
      onAuthSuccess(loginResult.access_token, loginResult.user);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-root auth-dark">
      <ParallaxDotsBackground />
      <div className="auth-card">
        <h1>Auto-reg Web</h1>
        <p className="auth-subtitle">Браузерная версия Mail.tm инструмента</p>

        <div className="auth-switch">
          <button
            type="button"
            className={mode === "login" ? "active" : ""}
            onClick={() => setMode("login")}
          >
            Вход
          </button>
          <button
            type="button"
            className={mode === "register" ? "active" : ""}
            onClick={() => setMode("register")}
          >
            Регистрация
          </button>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <label>
            Логин
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              minLength={3}
              required
              autoComplete="username"
            />
          </label>

          <label>
            Пароль
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              minLength={6}
              required
              autoComplete={isRegister ? "new-password" : "current-password"}
            />
          </label>

          {isRegister ? (
            <label>
              Повтор пароля
              <input
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                minLength={6}
                required
                autoComplete="new-password"
              />
            </label>
          ) : null}

          {error ? <div className="form-error">{error}</div> : null}

          <button type="submit" className="auth-submit-btn" disabled={busy}>
            {busy ? "Подождите..." : isRegister ? "Создать аккаунт" : "Войти"}
          </button>
        </form>
      </div>
    </div>
  );
}
