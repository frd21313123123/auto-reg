import { useState } from "react";

import { authApi } from "../api";

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
    <div className="auth-root">
      <div className="auth-card">
        <section className="auth-hero">
          <div className="auth-hero-mark">M</div>
          <div>
            <h1>Mail.tm Web Workspace</h1>
            <p className="auth-subtitle">
              Gmail-подобный интерфейс для временных почт, массовой регистрации и
              вспомогательных генераторов.
            </p>
          </div>

          <div className="auth-feature-list">
            <div className="auth-feature">
              <strong>Inbox и чтение писем</strong>
              <span>API mail.tm и fallback на IMAP в одном рабочем пространстве.</span>
            </div>
            <div className="auth-feature">
              <strong>Локальные инструменты</strong>
              <span>Ban-check, генераторы данных и быстрый импорт аккаунтов рядом с inbox.</span>
            </div>
            <div className="auth-feature">
              <strong>Поток под регистрацию</strong>
              <span>Интерфейс собран под массовую работу с временными почтами, а не под обычный email.</span>
            </div>
          </div>
        </section>

        <section className="auth-panel">
          <div className="auth-panel-head">
            <h2>{isRegister ? "Создайте workspace" : "Войдите в workspace"}</h2>
            <p>Один аккаунт открывает весь web-интерфейс управления временными почтами.</p>
          </div>

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
                autoComplete="username"
                minLength={3}
                required
              />
            </label>

            <label>
              Пароль
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete={isRegister ? "new-password" : "current-password"}
                minLength={6}
                required
              />
            </label>

            {isRegister ? (
              <label>
                Повтор пароля
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  autoComplete="new-password"
                  minLength={6}
                  required
                />
              </label>
            ) : null}

            {error ? <div className="form-error">{error}</div> : null}

            <button type="submit" className="auth-submit" disabled={busy}>
              {busy ? "Подождите..." : isRegister ? "Создать аккаунт" : "Войти"}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
