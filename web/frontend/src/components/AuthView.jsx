import { useEffect, useRef, useState } from "react";

import { authApi } from "../api";

export default function AuthView({ onAuthSuccess }) {
  const rootRef = useRef(null);
  const [mode, setMode] = useState("register");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const isRegister = mode === "register";

  useEffect(() => {
    const html = document.documentElement;
    const { body } = document;

    html.classList.add("auth-screen-active");
    body.classList.add("auth-screen-active");

    window.scrollTo(0, 0);
    html.scrollTop = 0;
    body.scrollTop = 0;
    if (rootRef.current) {
      rootRef.current.scrollTop = 0;
    }

    return () => {
      html.classList.remove("auth-screen-active");
      body.classList.remove("auth-screen-active");
    };
  }, []);

  const handleModeChange = (nextMode) => {
    setMode(nextMode);
    setError("");
    setConfirmPassword("");
  };

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
    <div ref={rootRef} className="auth-root">
      <div className="auth-card">
        <section className="auth-hero">
          <div className="auth-brand-lockup">
            <div className="auth-hero-mark">A</div>
            <div>
              <p className="auth-eyebrow">Account Access</p>
              <h1>Экран регистрации для рабочего потока.</h1>
            </div>
          </div>

          <p className="auth-subtitle">
            Вход и создание аккаунта собраны в одной точке: без лишних шагов, с акцентом на массовую
            работу с временными почтами и регистрациями.
          </p>
        </section>

        <section className="auth-panel">
          <div className="auth-mobile-brand">
            <div className="auth-mobile-mark">A</div>
            <div>
              <p className="auth-eyebrow">Auto-reg</p>
              <strong>Рабочий аккаунт</strong>
            </div>
          </div>

          <div className="auth-panel-head">
            <span className="auth-badge">{isRegister ? "Регистрация" : "Вход"}</span>
            <h2>{isRegister ? "Создайте рабочий аккаунт" : "С возвращением"}</h2>
            <p>
              {isRegister
                ? "Задайте логин и пароль. После регистрации вход выполнится автоматически."
                : "Введите логин и пароль, чтобы открыть web-интерфейс и продолжить работу."}
            </p>
          </div>

          <div className="auth-switch">
            <button
              type="button"
              className={mode === "login" ? "active" : ""}
              onClick={() => handleModeChange("login")}
            >
              Вход
            </button>
            <button
              type="button"
              className={mode === "register" ? "active" : ""}
              onClick={() => handleModeChange("register")}
            >
              Регистрация
            </button>
          </div>

          <form onSubmit={handleSubmit} className="auth-form">
            <label className="auth-field">
              <span>Логин</span>
              <input
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                autoComplete="username"
                placeholder="Введите логин"
                minLength={3}
                required
              />
            </label>

            <label className="auth-field">
              <span>Пароль</span>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete={isRegister ? "new-password" : "current-password"}
                placeholder={isRegister ? "Не короче 6 символов" : "••••••••"}
                minLength={6}
                required
              />
            </label>

            {isRegister ? (
              <label className="auth-field">
                <span>Повтор пароля</span>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  autoComplete="new-password"
                  placeholder="Повторите пароль"
                  minLength={6}
                  required
                />
              </label>
            ) : null}

            <div className="auth-meta">
              <p className="auth-note">
                {isRegister
                  ? "Используйте латиницу и цифры, чтобы аккаунт было проще переиспользовать."
                  : "Один аккаунт хранит доступ к интерфейсу, а не к отдельной почте."}
              </p>
              <span className="auth-note-pill">{isRegister ? "Новый аккаунт" : "Web account"}</span>
            </div>

            {error ? (
              <div className="form-error" role="alert">
                {error}
              </div>
            ) : null}

            <button type="submit" className="auth-submit" disabled={busy}>
              {busy ? "Подождите..." : isRegister ? "Создать аккаунт" : "Войти в аккаунт"}
            </button>
          </form>

          <p className="auth-footer">
            {isRegister ? "Уже есть аккаунт?" : "Нет аккаунта?"}{" "}
            <button
              type="button"
              className="auth-footer-link"
              onClick={() => handleModeChange(isRegister ? "login" : "register")}
            >
              {isRegister ? "Войти" : "Зарегистрироваться"}
            </button>
          </p>
        </section>
      </div>
    </div>
  );
}
