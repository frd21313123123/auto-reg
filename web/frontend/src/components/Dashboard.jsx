import { useEffect, useMemo, useState } from "react";

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
    }

    applyStatus(`Писем: ${inbox.length}`);
  };

  const openMessage = async (message) => {
    if (!selectedAccount) {
      return;
    }

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
      <aside className="left-panel">
        <div className="panel-header">
          <div>
            <h2>Mail.tm</h2>
            <p>{user.username}</p>
          </div>
          <div className="header-actions">
            <button type="button" onClick={() => setTheme(theme === "light" ? "dark" : "light")}>Тема</button>
            <button type="button" onClick={onLogout}>Выход</button>
          </div>
        </div>

        <div className="button-row">
          <button type="button" onClick={createMailTm} disabled={busy}>+ Создать mail.tm</button>
          <button type="button" onClick={banCheckAll} disabled={busy}>Ban чек всех</button>
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
          <button type="submit" disabled={busy}>Добавить вручную</button>
        </form>

        <textarea
          className="import-textarea"
          placeholder="Вставьте аккаунты: email / pass;pass / status"
          value={importText}
          onChange={(event) => setImportText(event.target.value)}
        />
        <button type="button" onClick={importAccounts} disabled={busy || !importText.trim()}>
          Импорт из текста
        </button>

        <div className="account-list">
          {accounts.map((account) => (
            <button
              key={account.id}
              type="button"
              className={`account-item ${statusClass(account.status)} ${
                account.id === selectedAccountId ? "active" : ""
              }`}
              onClick={() => setSelectedAccountId(account.id)}
            >
              <span>{account.email}</span>
              <small>{STATUS_LABELS[account.status] || account.status}</small>
            </button>
          ))}
        </div>

        <div className="button-grid">
          <button type="button" onClick={() => copyAccountField("email")} disabled={!selectedAccount}>Copy email</button>
          <button type="button" onClick={() => copyAccountField("openai")} disabled={!selectedAccount}>Copy openai</button>
          <button type="button" onClick={() => copyAccountField("mail")} disabled={!selectedAccount}>Copy mail</button>
          <button type="button" onClick={() => copyAccountField("full")} disabled={!selectedAccount}>Copy full</button>
        </div>

        <div className="button-grid status-grid">
          {STATUS_OPTIONS.map((status) => (
            <button
              type="button"
              key={status}
              onClick={() => setSelectedStatus(status)}
              disabled={!selectedAccount || busy}
            >
              {STATUS_LABELS[status]}
            </button>
          ))}
        </div>

        <div className="button-row">
          <button type="button" onClick={banCheckOne} disabled={!selectedAccount || busy}>Ban чек</button>
          <button type="button" onClick={deleteSelectedAccount} disabled={!selectedAccount || busy}>Удалить</button>
        </div>

        <section className="generator-block">
          <h3>Random person</h3>
          <div className="kv-row">
            <span>Name</span>
            <code>{randomPerson.name}</code>
            <button type="button" onClick={() => copyText(randomPerson.name)}>Copy</button>
          </div>
          <div className="kv-row">
            <span>Birthdate</span>
            <code>{randomPerson.birthdate}</code>
            <button type="button" onClick={() => copyText(randomPerson.birthdate)}>Copy</button>
          </div>
          <button type="button" onClick={regenerateRandomPerson}>Обновить</button>
        </section>

        <section className="generator-block compact">
          <h3>IN Generator</h3>
          {inData ? (
            <>
              <div className="mini-grid">
                <button type="button" onClick={() => copyText(inData.card)}>Card</button>
                <button type="button" onClick={() => copyText(inData.exp)}>Exp</button>
                <button type="button" onClick={() => copyText(inData.cvv)}>CVV</button>
                <button type="button" onClick={() => copyText(inData.name)}>Name</button>
                <button type="button" onClick={() => copyText(inData.city)}>City</button>
                <button type="button" onClick={() => copyText(inData.postcode)}>Postcode</button>
              </div>
              <button type="button" onClick={regenerateIn}>Новые IN данные</button>
            </>
          ) : null}
        </section>

        <section className="generator-block compact">
          <h3>SK Generator</h3>
          {skData ? (
            <>
              <div className="mini-grid">
                <button type="button" onClick={() => copyText(skData.card)}>Card</button>
                <button type="button" onClick={() => copyText(skData.exp)}>Exp</button>
                <button type="button" onClick={() => copyText(skData.cvv)}>CVV</button>
                <button type="button" onClick={() => copyText(skData.name)}>Name</button>
                <button type="button" onClick={() => copyText(skData.city)}>City</button>
                <button type="button" onClick={() => copyText(skData.postcode)}>Postcode</button>
              </div>
              <button type="button" onClick={regenerateSk}>Новые SK данные</button>
            </>
          ) : null}
        </section>
      </aside>

      <main className="right-panel">
        <header className="mail-header">
          <div>
            <h2>{selectedAccount ? selectedAccount.email : "Выберите аккаунт"}</h2>
            <p>{selectedAccount ? `Статус: ${STATUS_LABELS[selectedAccount.status]}` : ""}</p>
          </div>
          <button type="button" onClick={manualRefresh} disabled={!selectedAccount || busy}>Обновить inbox</button>
        </header>

        <div className="mail-grid">
          <section className="message-list">
            <table>
              <thead>
                <tr>
                  <th>От</th>
                  <th>Тема</th>
                  <th>Время</th>
                </tr>
              </thead>
              <tbody>
                {messages.map((message) => (
                  <tr key={message.id} onClick={() => openMessage(message)}>
                    <td>{message.sender}</td>
                    <td>{message.subject}</td>
                    <td>{message.created_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!messages.length ? <div className="empty-state">Писем пока нет</div> : null}
          </section>

          <section className="message-viewer">
            {messageDetail ? (
              <>
                <div className="message-meta">
                  <p><strong>От:</strong> {messageDetail.sender}</p>
                  <p><strong>Тема:</strong> {messageDetail.subject}</p>
                  {messageDetail.code ? (
                    <button type="button" onClick={copyCode}>
                      Скопировать код {messageDetail.code}
                    </button>
                  ) : null}
                </div>
                <pre>{messageDetail.text}</pre>
              </>
            ) : (
              <div className="empty-state">Выберите письмо для просмотра</div>
            )}
          </section>
        </div>
      </main>

      <footer className="status-bar">{statusMessage}</footer>
    </div>
  );
}
