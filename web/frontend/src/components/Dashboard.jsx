import { useDeferredValue, useEffect, useMemo, useState } from "react";

import { accountsApi, mailApi, toolsApi } from "../api";

const STATUS_OPTIONS = [
  "not_registered",
  "registered",
  "plus",
  "banned",
  "invalid_password"
];

const STATUS_LABELS = {
  not_registered: "Не зарегистрирован",
  registered: "Registered",
  plus: "Plus",
  banned: "Banned",
  invalid_password: "Неверный пароль"
};

function statusClass(status) {
  return `status-${status}`;
}

function formatMessageTime(value) {
  if (!value) {
    return "";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  const now = new Date();
  const isSameDay =
    now.getFullYear() === date.getFullYear() &&
    now.getMonth() === date.getMonth() &&
    now.getDate() === date.getDate();

  if (isSameDay) {
    return new Intl.DateTimeFormat("ru-RU", {
      hour: "2-digit",
      minute: "2-digit"
    }).format(date);
  }

  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "short"
  }).format(date);
}

function formatAccountMeta(account) {
  if (!account) {
    return "";
  }

  return account.password_openai === account.password_mail
    ? "Один пароль для OpenAI и почты"
    : "Раздельные пароли OpenAI и почты";
}

async function copyText(value) {
  if (!value) {
    return;
  }
  await navigator.clipboard.writeText(value);
}

export default function Dashboard({ token, user, onLogout }) {
  const [theme, setTheme] = useState("light");
  const [statusMessage, setStatusMessage] = useState("Готово");

  const [accounts, setAccounts] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [messageDetail, setMessageDetail] = useState(null);
  const [activeMessageId, setActiveMessageId] = useState(null);

  const [searchQuery, setSearchQuery] = useState("");
  const deferredSearchQuery = useDeferredValue(searchQuery.trim().toLowerCase());

  const [importText, setImportText] = useState("");
  const [manualEmail, setManualEmail] = useState("");
  const [manualPasswordOpenai, setManualPasswordOpenai] = useState("");
  const [manualPasswordMail, setManualPasswordMail] = useState("");

  const [randomPerson, setRandomPerson] = useState({ name: "", birthdate: "" });
  const [inData, setInData] = useState(null);
  const [skData, setSkData] = useState(null);

  const [busy, setBusy] = useState(false);

  const selectedAccount = useMemo(
    () => accounts.find((item) => item.id === selectedAccountId) || null,
    [accounts, selectedAccountId]
  );

  const filteredAccounts = useMemo(() => {
    if (!deferredSearchQuery) {
      return accounts;
    }

    return accounts.filter((account) => {
      const haystack = [
        account.email,
        account.status,
        STATUS_LABELS[account.status] || account.status
      ]
        .join(" ")
        .toLowerCase();

      return haystack.includes(deferredSearchQuery);
    });
  }, [accounts, deferredSearchQuery]);

  const filteredMessages = useMemo(() => {
    if (!deferredSearchQuery) {
      return messages;
    }

    return messages.filter((message) => {
      const haystack = [message.sender, message.subject, message.created_at]
        .join(" ")
        .toLowerCase();

      return haystack.includes(deferredSearchQuery);
    });
  }, [messages, deferredSearchQuery]);

  const accountStats = useMemo(() => {
    const stats = {
      total: accounts.length,
      registered: 0,
      plus: 0,
      banned: 0
    };

    accounts.forEach((account) => {
      if (account.status === "registered") {
        stats.registered += 1;
      }
      if (account.status === "plus") {
        stats.plus += 1;
      }
      if (account.status === "banned") {
        stats.banned += 1;
      }
    });

    return stats;
  }, [accounts]);

  const applyStatus = (message) => {
    setStatusMessage(message);
  };

  const withBusy = async (operation, loadingText = "Загрузка...") => {
    setBusy(true);
    applyStatus(loadingText);
    try {
      await operation();
    } catch (error) {
      applyStatus(`Ошибка: ${error.message}`);
    } finally {
      setBusy(false);
    }
  };

  const loadAccounts = async (nextSelectedId = null) => {
    const response = await accountsApi.list(token);
    setAccounts(response);

    if (!response.length) {
      setSelectedAccountId(null);
      setMessages([]);
      setMessageDetail(null);
      setActiveMessageId(null);
      return;
    }

    const desiredId = nextSelectedId ?? selectedAccountId;
    const hasDesired = response.some((item) => item.id === desiredId);
    setSelectedAccountId(hasDesired ? desiredId : response[0].id);
  };

  const loadRandomPerson = async () => {
    const person = await toolsApi.randomPerson(token);
    setRandomPerson(person);
  };

  const connectSelected = async () => {
    if (!selectedAccount) {
      return;
    }
    await mailApi.connect(token, selectedAccount.id);
  };

  const refreshMessages = async () => {
    if (!selectedAccount) {
      return;
    }
    const inbox = await mailApi.messages(token, selectedAccount.id);
    setMessages(inbox);

    if (!inbox.length) {
      setMessageDetail(null);
      setActiveMessageId(null);
    } else if (activeMessageId && !inbox.some((item) => item.id === activeMessageId)) {
      setMessageDetail(null);
      setActiveMessageId(null);
    }

    applyStatus(`Писем: ${inbox.length}`);
  };

  const openMessage = async (message) => {
    if (!selectedAccount) {
      return;
    }

    setActiveMessageId(message.id);

    const detail = await mailApi.messageDetail(
      token,
      selectedAccount.id,
      message.id,
      message.sender,
      message.subject
    );
    setMessageDetail(detail);
  };

  useEffect(() => {
    withBusy(async () => {
      await loadAccounts();
      await loadRandomPerson();
      setInData(await toolsApi.generatorIn(token));
      setSkData(await toolsApi.generatorSk(token));
      applyStatus("Готово");
    }, "Инициализация...");
  }, []);

  useEffect(() => {
    if (!selectedAccountId) {
      return;
    }
    setActiveMessageId(null);
    setMessageDetail(null);
    withBusy(async () => {
      await connectSelected();
      await refreshMessages();
    }, "Подключение к почте...");
  }, [selectedAccountId]);

  const createMailTm = () =>
    withBusy(async () => {
      const created = await accountsApi.createMailTm(token, 12);
      await loadAccounts(created.id);
      applyStatus(`Создан аккаунт ${created.email}`);
    }, "Создание аккаунта...");

  const addManualAccount = (event) => {
    event.preventDefault();

    withBusy(async () => {
      const payload = {
        email: manualEmail,
        password_openai: manualPasswordOpenai,
        password_mail: manualPasswordMail || manualPasswordOpenai,
        status: "not_registered"
      };
      const created = await accountsApi.create(token, payload);
      setManualEmail("");
      setManualPasswordOpenai("");
      setManualPasswordMail("");
      await loadAccounts(created.id);
      applyStatus(`Добавлен ${created.email}`);
    }, "Добавление аккаунта...");
  };

  const importAccounts = () =>
    withBusy(async () => {
      const result = await accountsApi.importAccounts(token, importText);
      await loadAccounts();
      applyStatus(
        `Импорт: добавлено ${result.added}, дубли ${result.duplicates}, пропущено ${result.skipped}`
      );
      setImportText("");
    }, "Импорт аккаунтов...");

  const setSelectedStatus = (status) => {
    if (!selectedAccount) {
      return;
    }

    withBusy(async () => {
      await accountsApi.updateStatus(token, selectedAccount.id, status);
      await loadAccounts(selectedAccount.id);
      applyStatus(`Статус изменен: ${status}`);
    }, "Обновление статуса...");
  };

  const deleteSelectedAccount = () => {
    if (!selectedAccount) {
      return;
    }

    if (!window.confirm(`Удалить ${selectedAccount.email}?`)) {
      return;
    }

    withBusy(async () => {
      await accountsApi.remove(token, selectedAccount.id);
      await loadAccounts();
      applyStatus("Аккаунт удален");
    }, "Удаление аккаунта...");
  };

  const banCheckOne = () => {
    if (!selectedAccount) {
      return;
    }

    withBusy(async () => {
      const result = await mailApi.banCheckOne(token, selectedAccount.id);
      await loadAccounts(selectedAccount.id);
      applyStatus(`Ban check: ${result.result}`);
    }, "Проверка аккаунта...");
  };

  const banCheckAll = () =>
    withBusy(async () => {
      const response = await mailApi.banCheckBulk(token, null);
      await loadAccounts(selectedAccountId);
      applyStatus(
        `Проверено ${response.checked}. Banned: ${response.banned}, invalid_password: ${response.invalid_password}, errors: ${response.errors}`
      );
    }, "Массовая проверка...");

  const manualRefresh = () =>
    withBusy(async () => {
      await refreshMessages();
      applyStatus("Inbox обновлен");
    }, "Обновление inbox...");

  const regenerateRandomPerson = () =>
    withBusy(async () => {
      await loadRandomPerson();
      applyStatus("Случайные данные обновлены");
    }, "Генерация данных...");

  const regenerateIn = () =>
    withBusy(async () => {
      setInData(await toolsApi.generatorIn(token));
      applyStatus("IN-генератор обновлен");
    }, "Генерация IN данных...");

  const regenerateSk = () =>
    withBusy(async () => {
      setSkData(await toolsApi.generatorSk(token));
      applyStatus("SK-генератор обновлен");
    }, "Генерация SK данных...");

  const copyAccountField = async (field) => {
    if (!selectedAccount) {
      return;
    }

    let value = "";
    if (field === "email") {
      value = selectedAccount.email;
    }
    if (field === "openai") {
      value = selectedAccount.password_openai;
    }
    if (field === "mail") {
      value = selectedAccount.password_mail;
    }
    if (field === "full") {
      if (selectedAccount.password_openai !== selectedAccount.password_mail) {
        value = `${selectedAccount.email}:${selectedAccount.password_openai};${selectedAccount.password_mail}`;
      } else {
        value = `${selectedAccount.email}:${selectedAccount.password_openai}`;
      }
    }

    await copyText(value);
    applyStatus(`Скопировано: ${field}`);
  };

  const copyCode = async () => {
    if (!messageDetail?.code) {
      return;
    }
    await copyText(messageDetail.code);
    applyStatus(`Код ${messageDetail.code} скопирован`);
  };

  return (
    <div className={`dashboard theme-${theme}`}>
      <header className="app-topbar">
        <div className="brand-lockup">
          <div className="brand-mark">M</div>
          <div>
            <strong>Mail.tm Workspace</strong>
            <span>Почтовая консоль регистрации</span>
          </div>
        </div>

        <label className="search-shell">
          <span>Поиск</span>
          <input
            type="search"
            placeholder="Ищите аккаунты, статусы и письма"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
          />
        </label>

        <div className="topbar-actions">
          <div className="user-chip">
            <span className="user-chip-label">Профиль</span>
            <strong>{user.username}</strong>
          </div>
          <button
            type="button"
            className="ghost-button"
            onClick={() => setTheme(theme === "light" ? "dark" : "light")}
          >
            {theme === "light" ? "Темная тема" : "Светлая тема"}
          </button>
          <button type="button" className="ghost-button" onClick={onLogout}>
            Выйти
          </button>
        </div>
      </header>

      <div className="workspace-layout">
        <aside className="workspace-sidebar">
          <button type="button" className="compose-button" onClick={createMailTm} disabled={busy}>
            Создать mail.tm
          </button>

          <section className="sidebar-card">
            <div className="card-heading">
              <div>
                <p className="eyebrow">Навигация</p>
                <h2>Почтовые ящики</h2>
              </div>
              <span className="count-pill">{filteredAccounts.length}</span>
            </div>

            <div className="account-list gmail-list">
              {filteredAccounts.map((account) => (
                <button
                  key={account.id}
                  type="button"
                  className={`account-item account-nav-item ${statusClass(account.status)} ${
                    account.id === selectedAccountId ? "active" : ""
                  }`}
                  onClick={() => setSelectedAccountId(account.id)}
                >
                  <div className="account-nav-top">
                    <span className="account-email">{account.email}</span>
                    <span className={`status-pill status-pill-${account.status}`}>
                      {STATUS_LABELS[account.status] || account.status}
                    </span>
                  </div>
                  <small>{formatAccountMeta(account)}</small>
                </button>
              ))}

              {!filteredAccounts.length ? (
                <div className="empty-state compact">Ничего не найдено по текущему поиску.</div>
              ) : null}
            </div>
          </section>

          <section className="sidebar-card">
            <div className="card-heading">
              <div>
                <p className="eyebrow">Импорт</p>
                <h2>Добавление аккаунтов</h2>
              </div>
            </div>

            <form className="manual-form" onSubmit={addManualAccount}>
              <input
                placeholder="email"
                value={manualEmail}
                onChange={(event) => setManualEmail(event.target.value)}
                required
              />
              <input
                placeholder="пароль openai"
                value={manualPasswordOpenai}
                onChange={(event) => setManualPasswordOpenai(event.target.value)}
                required
              />
              <input
                placeholder="пароль почты (опц.)"
                value={manualPasswordMail}
                onChange={(event) => setManualPasswordMail(event.target.value)}
              />
              <button type="submit" disabled={busy}>
                Добавить вручную
              </button>
            </form>

            <textarea
              className="import-textarea"
              placeholder="Вставьте аккаунты: email / pass или pass;pass / status"
              value={importText}
              onChange={(event) => setImportText(event.target.value)}
            />
            <button type="button" onClick={importAccounts} disabled={busy || !importText.trim()}>
              Импорт из текста
            </button>
          </section>
        </aside>

        <main className="mail-column">
          <section className="hero-card">
            <div>
              <p className="eyebrow">Inbox workspace</p>
              <h1>{selectedAccount ? selectedAccount.email : "Выберите аккаунт"}</h1>
              <p className="hero-subtitle">
                {selectedAccount
                  ? `${STATUS_LABELS[selectedAccount.status]} · ${formatAccountMeta(selectedAccount)}`
                  : "Слева находятся временные почты, а справа инструменты регистрации и чтения писем."}
              </p>
            </div>

            <div className="hero-actions">
              <button type="button" onClick={manualRefresh} disabled={!selectedAccount || busy}>
                Обновить inbox
              </button>
              <button type="button" onClick={banCheckOne} disabled={!selectedAccount || busy}>
                Ban чек
              </button>
              <button type="button" onClick={deleteSelectedAccount} disabled={!selectedAccount || busy}>
                Удалить
              </button>
            </div>
          </section>

          <section className="toolbar-card">
            <div className="stat-strip">
              <article className="stat-card">
                <span>Всего</span>
                <strong>{accountStats.total}</strong>
              </article>
              <article className="stat-card">
                <span>Registered</span>
                <strong>{accountStats.registered}</strong>
              </article>
              <article className="stat-card">
                <span>Plus</span>
                <strong>{accountStats.plus}</strong>
              </article>
              <article className="stat-card">
                <span>Banned</span>
                <strong>{accountStats.banned}</strong>
              </article>
            </div>

            <div className="action-clusters">
              <div className="button-grid compact-grid">
                <button
                  type="button"
                  onClick={() => copyAccountField("email")}
                  disabled={!selectedAccount}
                >
                  Copy email
                </button>
                <button
                  type="button"
                  onClick={() => copyAccountField("openai")}
                  disabled={!selectedAccount}
                >
                  Copy openai
                </button>
                <button
                  type="button"
                  onClick={() => copyAccountField("mail")}
                  disabled={!selectedAccount}
                >
                  Copy mail
                </button>
                <button
                  type="button"
                  onClick={() => copyAccountField("full")}
                  disabled={!selectedAccount}
                >
                  Copy full
                </button>
              </div>

              <div className="status-actions">
                {STATUS_OPTIONS.map((status) => (
                  <button
                    type="button"
                    key={status}
                    className={`status-switch status-switch-${status}`}
                    onClick={() => setSelectedStatus(status)}
                    disabled={!selectedAccount || busy}
                  >
                    {STATUS_LABELS[status]}
                  </button>
                ))}
              </div>
            </div>
          </section>

          <section className="mail-list-card">
            <div className="card-heading border-bottom">
              <div>
                <p className="eyebrow">Письма</p>
                <h2>Лента inbox</h2>
              </div>
              <span className="count-pill">{filteredMessages.length}</span>
            </div>

            <div className="message-stack">
              {filteredMessages.map((message) => (
                <button
                  key={message.id}
                  type="button"
                  className={`message-row ${activeMessageId === message.id ? "active" : ""}`}
                  onClick={() => openMessage(message)}
                >
                  <div className="message-row-main">
                    <strong>{message.sender || "Без отправителя"}</strong>
                    <span>{message.subject || "Без темы"}</span>
                  </div>
                  <span className="message-row-time">{formatMessageTime(message.created_at)}</span>
                </button>
              ))}

              {!filteredMessages.length ? (
                <div className="empty-state">
                  {selectedAccount
                    ? "В этой почте пока нет писем."
                    : "Выберите аккаунт слева, чтобы подключиться и загрузить inbox."}
                </div>
              ) : null}
            </div>
          </section>
        </main>

        <aside className="inspector-column">
          <section className="viewer-card">
            <div className="card-heading border-bottom">
              <div>
                <p className="eyebrow">Просмотр</p>
                <h2>{messageDetail ? messageDetail.subject : "Чтение письма"}</h2>
              </div>
              {messageDetail?.code ? (
                <button type="button" className="primary-inline" onClick={copyCode}>
                  Скопировать код {messageDetail.code}
                </button>
              ) : null}
            </div>

            {messageDetail ? (
              <div className="message-detail-shell">
                <div className="message-meta">
                  <p>
                    <strong>От:</strong> {messageDetail.sender}
                  </p>
                  <p>
                    <strong>Тема:</strong> {messageDetail.subject}
                  </p>
                </div>
                <pre>{messageDetail.text}</pre>
              </div>
            ) : (
              <div className="empty-state">
                Откройте письмо из центральной колонки. Здесь будет детальный просмотр и код
                подтверждения.
              </div>
            )}
          </section>

          <section className="toolkit-card">
            <div className="card-heading">
              <div>
                <p className="eyebrow">Локальные особенности</p>
                <h2>Инструменты регистрации</h2>
              </div>
            </div>

            <div className="generator-block">
              <div className="generator-header">
                <h3>Random person</h3>
                <button type="button" onClick={regenerateRandomPerson}>
                  Обновить
                </button>
              </div>
              <div className="kv-row">
                <span>Name</span>
                <code>{randomPerson.name || "-"}</code>
                <button type="button" onClick={() => copyText(randomPerson.name)}>
                  Copy
                </button>
              </div>
              <div className="kv-row">
                <span>Birthdate</span>
                <code>{randomPerson.birthdate || "-"}</code>
                <button type="button" onClick={() => copyText(randomPerson.birthdate)}>
                  Copy
                </button>
              </div>
            </div>

            <div className="generator-block compact">
              <div className="generator-header">
                <h3>IN Generator</h3>
                <button type="button" onClick={regenerateIn}>
                  Обновить
                </button>
              </div>
              {inData ? (
                <div className="mini-grid">
                  <button type="button" onClick={() => copyText(inData.card)}>
                    Card
                  </button>
                  <button type="button" onClick={() => copyText(inData.exp)}>
                    Exp
                  </button>
                  <button type="button" onClick={() => copyText(inData.cvv)}>
                    CVV
                  </button>
                  <button type="button" onClick={() => copyText(inData.name)}>
                    Name
                  </button>
                  <button type="button" onClick={() => copyText(inData.city)}>
                    City
                  </button>
                  <button type="button" onClick={() => copyText(inData.postcode)}>
                    Postcode
                  </button>
                </div>
              ) : (
                <div className="empty-state compact">Данные генератора пока не загружены.</div>
              )}
            </div>

            <div className="generator-block compact">
              <div className="generator-header">
                <h3>SK Generator</h3>
                <button type="button" onClick={regenerateSk}>
                  Обновить
                </button>
              </div>
              {skData ? (
                <div className="mini-grid">
                  <button type="button" onClick={() => copyText(skData.card)}>
                    Card
                  </button>
                  <button type="button" onClick={() => copyText(skData.exp)}>
                    Exp
                  </button>
                  <button type="button" onClick={() => copyText(skData.cvv)}>
                    CVV
                  </button>
                  <button type="button" onClick={() => copyText(skData.name)}>
                    Name
                  </button>
                  <button type="button" onClick={() => copyText(skData.city)}>
                    City
                  </button>
                  <button type="button" onClick={() => copyText(skData.postcode)}>
                    Postcode
                  </button>
                </div>
              ) : (
                <div className="empty-state compact">Данные генератора пока не загружены.</div>
              )}
            </div>

            <div className="generator-block compact">
              <div className="generator-header">
                <h3>Массовые действия</h3>
              </div>
              <div className="button-grid compact-grid">
                <button type="button" onClick={banCheckAll} disabled={busy}>
                  Ban чек всех
                </button>
                <button type="button" onClick={createMailTm} disabled={busy}>
                  Создать mail.tm
                </button>
              </div>
            </div>
          </section>
        </aside>
      </div>

      <footer className="status-bar">{statusMessage}</footer>
    </div>
  );
}
