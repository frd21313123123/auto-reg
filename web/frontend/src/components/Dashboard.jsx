import { useEffect, useMemo, useRef, useState } from "react";

import { accountsApi, mailApi, toolsApi } from "../api";

const STATUS_OPTIONS = [
  "not_registered",
  "registered",
  "plus",
  "busnis",
  "banned",
  "invalid_password"
];

const STATUS_LABELS = {
  not_registered: "Не зарегистрирован",
  registered: "Зарегистрирован",
  plus: "Plus",
  busnis: "Busnis",
  banned: "Banned",
  invalid_password: "Неверный пароль"
};

const STATUS_SHORT_LABELS = {
  not_registered: "Не рег",
  registered: "Рег",
  plus: "Plus",
  busnis: "Busnis",
  banned: "Бан",
  invalid_password: "Пароль"
};

const GENERATOR_HOTKEYS_STORAGE_KEY = "auto_reg_generator_hotkeys";
const SIDEBAR_GENERATOR_VISIBILITY_KEY = "auto_reg_sidebar_generator_visible";

const GENERATOR_CYCLE_ORDER = ["card", "exp_date", "cvv", "name", "city", "street", "postcode"];

const GENERATOR_FIELDS = [
  { action: "card", dataKey: "card", label: "Номер карты:" },
  { action: "exp_date", dataKey: "exp", label: "Expiration Date:" },
  { action: "cvv", dataKey: "cvv", label: "CVV:" },
  { action: "name", dataKey: "name", label: "Имя (Name):" },
  { action: "city", dataKey: "city", label: "Город (City):" },
  { action: "street", dataKey: "street", label: "Улица (Street):" },
  { action: "postcode", dataKey: "postcode", label: "Индекс (Postcode):" },
  { action: "address_en", dataKey: "address_en", label: "Address (English):" }
];

const HOTKEY_FIELDS = [
  { key: "sk_cycle", label: "Следующее поле" },
  { key: "sk_close", label: "Закрыть окно" },
  { key: "card", label: "Копировать карту" },
  { key: "exp_date", label: "Копировать Exp" },
  { key: "cvv", label: "Копировать CVV" },
  { key: "name", label: "Копировать имя" },
  { key: "city", label: "Копировать город" },
  { key: "street", label: "Копировать улицу" },
  { key: "postcode", label: "Копировать индекс" }
];

const DEFAULT_GENERATOR_HOTKEYS = {
  sk_cycle: "6",
  sk_close: "esc",
  card: "ctrl+1",
  exp_date: "ctrl+4",
  cvv: "ctrl+5",
  name: "ctrl+2",
  city: "ctrl+3",
  street: "ctrl+6",
  postcode: "ctrl+7"
};

function normalizeHotkeyValue(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "")
    .replace(/control/g, "ctrl")
    .replace(/escape/g, "esc");
}

function normalizeHotkeyMap(value) {
  const merged = { ...DEFAULT_GENERATOR_HOTKEYS };
  if (!value || typeof value !== "object") {
    return merged;
  }

  for (const field of HOTKEY_FIELDS) {
    if (typeof value[field.key] === "string") {
      const normalized = normalizeHotkeyValue(value[field.key]);
      merged[field.key] = normalized;
    }
  }

  return merged;
}

function loadGeneratorHotkeys() {
  try {
    const raw = localStorage.getItem(GENERATOR_HOTKEYS_STORAGE_KEY);
    if (!raw) {
      return { ...DEFAULT_GENERATOR_HOTKEYS };
    }
    return normalizeHotkeyMap(JSON.parse(raw));
  } catch {
    return { ...DEFAULT_GENERATOR_HOTKEYS };
  }
}

function eventToHotkey(event) {
  const key = String(event.key || "").toLowerCase();
  if (!key || key === "control" || key === "shift" || key === "alt" || key === "meta") {
    return "";
  }

  const normalizedKey = key === "escape" ? "esc" : key === " " ? "space" : key;
  const parts = [];
  if (event.ctrlKey) {
    parts.push("ctrl");
  }
  if (event.altKey) {
    parts.push("alt");
  }
  if (event.shiftKey) {
    parts.push("shift");
  }
  parts.push(normalizedKey);
  return parts.join("+");
}

function hotkeyHintText(hotkeys) {
  const value = (key) => hotkeys[key] || "-";
  return (
    `Горячие клавиши: Следующее=${value("sk_cycle")}, ` +
    `Закрыть=${value("sk_close")}, ` +
    `Карта=${value("card")}, ` +
    `Имя=${value("name")}, ` +
    `Город=${value("city")}`
  );
}

function statusClass(status) {
  return `status-${status}`;
}

function toLocalDateTime(value) {
  if (!value) {
    return "";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return String(value);
  }

  return parsed.toLocaleString();
}

function escapeCsvValue(value) {
  const text = String(value ?? "");
  if (text.includes('"') || text.includes(";") || text.includes("\n")) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

async function copyText(value) {
  if (!value) {
    return;
  }
  await navigator.clipboard.writeText(value);
}

function DarkParallaxDotsBackground() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return undefined;
    }

    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return undefined;
    }

    const spacing = 22;
    const radius = 1;
    const color = "rgba(255,255,255,0.08)";
    const parallaxStrength = 25;
    const smoothness = 0.08;

    let mouseX = 0;
    let mouseY = 0;
    let offsetX = 0;
    let offsetY = 0;
    let targetOffsetX = 0;
    let targetOffsetY = 0;
    let cols = 0;
    let rows = 0;
    let frameId = 0;

    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      cols = Math.ceil(canvas.width / spacing) + 2;
      rows = Math.ceil(canvas.height / spacing) + 2;
    };

    const updateParallax = () => {
      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;

      targetOffsetX = ((mouseX - centerX) / centerX) * parallaxStrength;
      targetOffsetY = ((mouseY - centerY) / centerY) * parallaxStrength;

      offsetX += (targetOffsetX - offsetX) * smoothness;
      offsetY += (targetOffsetY - offsetY) * smoothness;
    };

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = color;

      const startX = -spacing + offsetX;
      const startY = -spacing + offsetY;

      for (let i = 0; i < cols; i += 1) {
        for (let j = 0; j < rows; j += 1) {
          const x = startX + i * spacing;
          const y = startY + j * spacing;
          ctx.beginPath();
          ctx.arc(x, y, radius, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    };

    const animate = () => {
      updateParallax();
      draw();
      frameId = window.requestAnimationFrame(animate);
    };

    const handleMouseMove = (event) => {
      mouseX = event.clientX;
      mouseY = event.clientY;
    };

    window.addEventListener("mousemove", handleMouseMove, { passive: true });
    window.addEventListener("resize", resizeCanvas);

    resizeCanvas();
    animate();

    return () => {
      window.cancelAnimationFrame(frameId);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("resize", resizeCanvas);
    };
  }, []);

  return <canvas className="parallax-dots-bg" ref={canvasRef} aria-hidden="true" />;
}

function GeneratorPanel({
  title,
  data,
  busy,
  activeAction,
  hotkeys,
  onClose,
  onGenerate,
  onSettings,
  onCopy
}) {
  return (
    <div className="generator-overlay" onClick={onClose}>
      <section className="generator-modal" onClick={(event) => event.stopPropagation()}>
        <header className="generator-modal-header">
          <h3>{title}</h3>
          <button type="button" className="generator-close-btn" onClick={onClose} aria-label="Закрыть">
            ×
          </button>
        </header>

        <div className="generator-modal-body">
          {GENERATOR_FIELDS.map((field) => (
            <div className={`generator-field ${activeAction === field.action ? "active" : ""}`} key={field.action}>
              <div className="generator-field-label">{field.label}</div>
              <div className={`generator-field-input-row ${activeAction === field.action ? "highlight" : ""}`}>
                <input value={data?.[field.dataKey] || ""} readOnly />
                <button type="button" onClick={() => onCopy(field.action)}>
                  Copy
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="generator-modal-actions">
          <button type="button" className="primary-btn" onClick={onGenerate} disabled={busy}>
            Сгенерировать
          </button>
          <button type="button" onClick={onSettings}>
            Настройки
          </button>
        </div>

        <div className="generator-hotkeys">
          {hotkeyHintText(hotkeys)}
        </div>
      </section>
    </div>
  );
}

function HotkeySettingsModal({
  draftHotkeys,
  recordingHotkeyKey,
  onClose,
  onSave,
  onReset,
  onStartRecord,
  onClearHotkey
}) {
  return (
    <div className="hotkeys-overlay" onClick={onClose}>
      <section className="hotkeys-modal" onClick={(event) => event.stopPropagation()}>
        <header className="hotkeys-header">
          <h3>Настройки горячих клавиш</h3>
          <button type="button" className="hotkeys-close-btn" onClick={onClose} aria-label="Закрыть">
            ×
          </button>
        </header>

        <form className="hotkeys-form" onSubmit={onSave}>
          {HOTKEY_FIELDS.map((field) => (
            <label className="hotkeys-row" key={field.key}>
              <span>{field.label}</span>
              <div className="hotkeys-input-row">
                <input value={draftHotkeys[field.key]} readOnly placeholder={DEFAULT_GENERATOR_HOTKEYS[field.key]} />
                <button
                  type="button"
                  className={`hotkeys-record-btn ${recordingHotkeyKey === field.key ? "active" : ""}`}
                  onClick={() => onStartRecord(field.key)}
                >
                  {recordingHotkeyKey === field.key ? "Нажмите..." : "Записать"}
                </button>
                <button type="button" onClick={() => onClearHotkey(field.key)}>
                  Очистить
                </button>
              </div>
            </label>
          ))}

          <div className="hotkeys-actions">
            <button type="submit" className="primary-btn">
              Сохранить
            </button>
            <button type="button" onClick={onReset}>
              Сбросить
            </button>
            <button type="button" onClick={onClose}>
              Закрыть
            </button>
          </div>
        </form>
      </section>
    </div>
  );
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
  const [showImportPanel, setShowImportPanel] = useState(false);
  const [showInPanel, setShowInPanel] = useState(false);
  const [showSkPanel, setShowSkPanel] = useState(false);
  const [showSidebarGenerator, setShowSidebarGenerator] = useState(() => {
    try {
      const raw = localStorage.getItem(SIDEBAR_GENERATOR_VISIBILITY_KEY);
      if (raw === null) {
        return true;
      }
      return raw === "1";
    } catch {
      return true;
    }
  });
  const [showGeneratorHotkeys, setShowGeneratorHotkeys] = useState(false);
  const [generatorHotkeys, setGeneratorHotkeys] = useState(() => loadGeneratorHotkeys());
  const [draftHotkeys, setDraftHotkeys] = useState(() => loadGeneratorHotkeys());
  const [recordingHotkeyKey, setRecordingHotkeyKey] = useState(null);
  const [skActiveAction, setSkActiveAction] = useState(null);
  const [inActiveAction, setInActiveAction] = useState(null);
  const [skCycleIndex, setSkCycleIndex] = useState(0);
  const [inCycleIndex, setInCycleIndex] = useState(0);
  const [pendingSkInitialCycle, setPendingSkInitialCycle] = useState(false);

  const selectedAccount = useMemo(
    () => accounts.find((item) => item.id === selectedAccountId) || null,
    [accounts, selectedAccountId]
  );

  const applyStatus = (message) => {
    setStatusMessage(message);
  };

  const getGeneratorData = (generatorType) => {
    if (generatorType === "sk") {
      return skData;
    }
    return inData;
  };

  const setGeneratorActiveAction = (generatorType, action) => {
    if (generatorType === "sk") {
      setSkActiveAction(action);
      return;
    }
    setInActiveAction(action);
  };

  const closeSkGenerator = () => {
    setShowSkPanel(false);
    setPendingSkInitialCycle(false);
    setSkCycleIndex(0);
    setSkActiveAction(null);
  };

  const closeInGenerator = () => {
    setShowInPanel(false);
    setInCycleIndex(0);
    setInActiveAction(null);
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
    setMessageDetail({
      ...detail,
      id: message.id,
      sender: detail.sender || message.sender,
      subject: detail.subject || message.subject
    });
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

  useEffect(() => {
    localStorage.setItem(
      GENERATOR_HOTKEYS_STORAGE_KEY,
      JSON.stringify(normalizeHotkeyMap(generatorHotkeys))
    );
  }, [generatorHotkeys]);

  useEffect(() => {
    localStorage.setItem(
      SIDEBAR_GENERATOR_VISIBILITY_KEY,
      showSidebarGenerator ? "1" : "0"
    );
  }, [showSidebarGenerator]);

  useEffect(() => {
    if (!showGeneratorHotkeys || !recordingHotkeyKey) {
      return;
    }

    const handleHotkeyCapture = (event) => {
      const next = eventToHotkey(event);
      if (!next) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      setDraftHotkeys((prev) => ({ ...prev, [recordingHotkeyKey]: next }));
      setRecordingHotkeyKey(null);
      applyStatus(`Горячая клавиша назначена: ${recordingHotkeyKey} = ${next}`);
    };

    window.addEventListener("keydown", handleHotkeyCapture, true);
    return () => window.removeEventListener("keydown", handleHotkeyCapture, true);
  }, [showGeneratorHotkeys, recordingHotkeyKey]);

  const copyGeneratorAction = async (generatorType, action) => {
    const field = GENERATOR_FIELDS.find((item) => item.action === action);
    if (!field) {
      return;
    }

    const data = getGeneratorData(generatorType);
    const value = data?.[field.dataKey] || "";
    if (!value) {
      return;
    }
    await copyText(value);
    setGeneratorActiveAction(generatorType, action);
    applyStatus(`Скопировано: ${generatorType} ${action}`);
  };

  const cycleGeneratorAction = (generatorType) => {
    if (generatorType === "sk") {
      const action = GENERATOR_CYCLE_ORDER[skCycleIndex % GENERATOR_CYCLE_ORDER.length];
      void copyGeneratorAction("sk", action);
      setSkCycleIndex((prev) => (prev + 1) % GENERATOR_CYCLE_ORDER.length);
      return;
    }

    const action = GENERATOR_CYCLE_ORDER[inCycleIndex % GENERATOR_CYCLE_ORDER.length];
    void copyGeneratorAction("in", action);
    setInCycleIndex((prev) => (prev + 1) % GENERATOR_CYCLE_ORDER.length);
  };

  useEffect(() => {
    if ((!showSkPanel && !showInPanel) || showGeneratorHotkeys) {
      return;
    }

    const handleKeydown = (event) => {
      const pressed = eventToHotkey(event);
      if (!pressed) {
        return;
      }

      const activeGenerator = showSkPanel ? "sk" : "in";
      let handled = false;

      if (pressed === generatorHotkeys.sk_close) {
        if (activeGenerator === "sk") {
          closeSkGenerator();
        } else {
          closeInGenerator();
        }
        handled = true;
      } else if (pressed === generatorHotkeys.sk_cycle) {
        cycleGeneratorAction(activeGenerator);
        handled = true;
      } else {
        for (const action of GENERATOR_CYCLE_ORDER) {
          if (pressed === generatorHotkeys[action]) {
            void copyGeneratorAction(activeGenerator, action);
            handled = true;
            break;
          }
        }
      }

      if (handled) {
        event.preventDefault();
        event.stopPropagation();
      }
    };

    window.addEventListener("keydown", handleKeydown);
    return () => window.removeEventListener("keydown", handleKeydown);
  }, [showSkPanel, showInPanel, showGeneratorHotkeys, generatorHotkeys, skCycleIndex, inCycleIndex, skData, inData]);

  useEffect(() => {
    if (!showSkPanel || !pendingSkInitialCycle || !skData) {
      return;
    }

    void copyGeneratorAction("sk", "card");
    setSkCycleIndex(1 % GENERATOR_CYCLE_ORDER.length);
    setPendingSkInitialCycle(false);
  }, [showSkPanel, pendingSkInitialCycle, skData]);

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
      setShowImportPanel(false);
    }, "Импорт аккаунтов...");

  const refreshAccounts = () =>
    withBusy(async () => {
      await loadAccounts(selectedAccountId);
      applyStatus("Список аккаунтов обновлен");
    }, "Обновление списка аккаунтов...");

  const exportAccountsForExcel = () => {
    if (!accounts.length) {
      applyStatus("Нет аккаунтов для экспорта");
      return;
    }

    const lines = ["email;password_openai;password_mail;status"];
    for (const account of accounts) {
      lines.push(
        [
          escapeCsvValue(account.email),
          escapeCsvValue(account.password_openai),
          escapeCsvValue(account.password_mail),
          escapeCsvValue(account.status)
        ].join(";")
      );
    }

    const csvText = lines.join("\n");
    const blob = new Blob([`\uFEFF${csvText}`], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);

    const now = new Date();
    const stamp = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, "0")}${String(
      now.getDate()
    ).padStart(2, "0")}`;

    const link = document.createElement("a");
    link.href = url;
    link.download = `accounts_${stamp}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    applyStatus("Экспорт в CSV для Excel завершен");
  };

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

  const deleteSelectedMailbox = () => {
    if (!selectedAccount) {
      return;
    }

    if (!window.confirm(`Удалить почту ${selectedAccount.email} в mail.tm и из списка?`)) {
      return;
    }

    withBusy(async () => {
      await accountsApi.removeMailbox(token, selectedAccount.id);
      await loadAccounts();
      applyStatus("Почта удалена");
    }, "Удаление почты...");
  };

  const banCheckOne = () => {
    if (!selectedAccount) {
      return;
    }

    withBusy(async () => {
      const result = await mailApi.banCheckOne(token, selectedAccount.id);
      await loadAccounts(selectedAccount.id);
      applyStatus(`Проверка: ${result.result}`);
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

  const openGeneratorHotkeys = () => {
    setDraftHotkeys(generatorHotkeys);
    setRecordingHotkeyKey(null);
    setShowGeneratorHotkeys(true);
  };

  const closeGeneratorHotkeys = () => {
    setRecordingHotkeyKey(null);
    setShowGeneratorHotkeys(false);
  };

  const toggleHotkeyRecord = (key) => {
    setRecordingHotkeyKey((prev) => (prev === key ? null : key));
  };

  const clearDraftHotkey = (key) => {
    setDraftHotkeys((prev) => ({ ...prev, [key]: "" }));
    if (recordingHotkeyKey === key) {
      setRecordingHotkeyKey(null);
    }
  };

  const saveGeneratorHotkeys = (event) => {
    event.preventDefault();
    const normalized = normalizeHotkeyMap(draftHotkeys);
    setGeneratorHotkeys(normalized);
    setDraftHotkeys(normalized);
    setRecordingHotkeyKey(null);
    setShowGeneratorHotkeys(false);
    applyStatus("Настройки горячих клавиш сохранены");
  };

  const resetGeneratorHotkeys = () => {
    const defaults = { ...DEFAULT_GENERATOR_HOTKEYS };
    setDraftHotkeys(defaults);
    setGeneratorHotkeys(defaults);
    setRecordingHotkeyKey(null);
    applyStatus("Горячие клавиши сброшены к значениям по умолчанию");
  };

  const openInGenerator = () => {
    setShowSkPanel(false);
    setShowInPanel(true);
    setInCycleIndex(0);
    setInActiveAction(null);
    if (!inData) {
      void regenerateIn();
    }
  };

  const openSkGenerator = () => {
    setShowInPanel(false);
    setShowSkPanel(true);
    setSkCycleIndex(0);
    setSkActiveAction(null);
    setPendingSkInitialCycle(true);
    if (!skData) {
      void regenerateSk();
    }
  };

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

  const copyGeneratorField = async (label, value) => {
    if (!value) {
      return;
    }
    await copyText(value);
    applyStatus(`Скопировано: ${label}`);
  };

  const copyCode = async () => {
    if (!messageDetail?.code) {
      return;
    }
    await copyText(messageDetail.code);
    applyStatus(`Код ${messageDetail.code} скопирован`);
  };

  const handleMinesweeper = () => {
    applyStatus("Сапер пока доступен только в desktop-версии");
  };

  const toggleSidebarGenerator = () => {
    setShowSidebarGenerator((prev) => {
      const next = !prev;
      applyStatus(next ? "Генератор показан" : "Генератор скрыт");
      return next;
    });
  };

  return (
    <div className={`dashboard-shell theme-${theme}`}>
      {theme === "dark" ? <DarkParallaxDotsBackground /> : null}
      <div className="dashboard-window">
        <aside className="left-panel">
          <div className="brand-strip">
            <h1 className="brand-title">
              <span>Mail.</span>tm
            </h1>
            <div className="brand-actions">
              <button
                type="button"
                className="icon-btn"
                title="Переключить тему"
                onClick={() => setTheme(theme === "light" ? "dark" : "light")}
              >
                Т
              </button>
              <button type="button" className="icon-btn" title="Выйти" onClick={onLogout}>
                В
              </button>
            </div>
          </div>
          <div className="user-caption">{user.username}</div>

          <button type="button" className="primary-btn create-btn" onClick={createMailTm} disabled={busy}>
            + Создать аккаунт
          </button>

          <section className="side-section accounts-section">
            <div className="section-caption">АККАУНТЫ</div>

            <div className="mini-controls">
              <button type="button" onClick={refreshAccounts} disabled={busy}>
                Обновить
              </button>
              <button
                type="button"
                className={showImportPanel ? "active" : ""}
                onClick={() => setShowImportPanel((prev) => !prev)}
                disabled={busy}
              >
                Файл
              </button>
              <button type="button" onClick={exportAccountsForExcel} disabled={busy}>
                Excel
              </button>
              <button type="button" className="danger-btn" onClick={banCheckAll} disabled={busy}>
                Бан
              </button>
            </div>

            {showImportPanel ? (
              <div className="import-panel">
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
                    Добавить
                  </button>
                </form>

                <textarea
                  className="import-textarea"
                  placeholder="Вставьте аккаунты: email / pass;pass / status"
                  value={importText}
                  onChange={(event) => setImportText(event.target.value)}
                />

                <div className="import-actions">
                  <button type="button" onClick={importAccounts} disabled={busy || !importText.trim()}>
                    Импорт
                  </button>
                  <button type="button" onClick={() => setShowImportPanel(false)} disabled={busy}>
                    Закрыть
                  </button>
                </div>
              </div>
            ) : null}

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
                  <span className="account-email">{account.email}</span>
                  <small>{STATUS_LABELS[account.status] || account.status}</small>
                </button>
              ))}

              {!accounts.length ? <div className="empty-list">Аккаунтов пока нет</div> : null}
            </div>
          </section>

          <section className="side-section">
            <div className="section-caption">ДЕЙСТВИЯ</div>

            <div className="actions-grid">
              <button type="button" onClick={() => copyAccountField("email")} disabled={!selectedAccount}>
                Email
              </button>
              <button type="button" onClick={() => copyAccountField("openai")} disabled={!selectedAccount}>
                OpenAI
              </button>
              <button type="button" onClick={() => copyAccountField("mail")} disabled={!selectedAccount}>
                Почта
              </button>
              <button
                type="button"
                className={showSkPanel ? "active" : ""}
                onClick={openSkGenerator}
              >
                SK
              </button>
              <button
                type="button"
                className={showInPanel ? "active" : ""}
                onClick={openInGenerator}
              >
                IN
              </button>
              <button type="button" onClick={handleMinesweeper}>
                Сапёр
              </button>
              <button type="button" onClick={openGeneratorHotkeys}>
                Настройки
              </button>
            </div>

            <div className="utility-row">
              <button type="button" onClick={banCheckOne} disabled={!selectedAccount || busy}>
                Бан 1
              </button>
              <button
                type="button"
                className="danger-btn"
                onClick={deleteSelectedMailbox}
                disabled={!selectedAccount || busy}
              >
                Удалить почту
              </button>
              <button type="button" onClick={deleteSelectedAccount} disabled={!selectedAccount || busy}>
                Удалить запись
              </button>
              <button type="button" onClick={() => copyAccountField("full")} disabled={!selectedAccount}>
                Full
              </button>
            </div>
          </section>

          <section className={`side-section generator-section ${showSidebarGenerator ? "" : "collapsed"}`}>
            <div className="section-header">
              <div className="section-caption">ГЕНЕРАТОР</div>
              <button type="button" className="section-toggle-btn" onClick={toggleSidebarGenerator}>
                {showSidebarGenerator ? "Скрыть" : "Показать"}
              </button>
            </div>

            {showSidebarGenerator ? (
              <>
                <div className="generator-row">
                  <span>Name</span>
                  <code>{randomPerson.name || "-"}</code>
                  <button type="button" onClick={() => copyGeneratorField("name", randomPerson.name)}>
                    Копировать
                  </button>
                </div>

                <div className="generator-row">
                  <span>Дата</span>
                  <code>{randomPerson.birthdate || "-"}</code>
                  <button type="button" onClick={() => copyGeneratorField("birthdate", randomPerson.birthdate)}>
                    Копировать
                  </button>
                </div>

                <button type="button" className="primary-btn" onClick={regenerateRandomPerson} disabled={busy}>
                  Новые данные
                </button>
              </>
            ) : (
              <div className="generator-collapsed-note">Блок генератора скрыт</div>
            )}
          </section>

          {showSidebarGenerator ? (
            <div className="side-footer">Сгенерировано: {randomPerson.name || "-"}</div>
          ) : null}
        </aside>

        <main className="right-panel">
          <header className="top-toolbar">
            <h2>{selectedAccount ? selectedAccount.email : "Выберите аккаунт слева"}</h2>

            <div className="toolbar-controls">
              <button
                type="button"
                className="primary-btn"
                onClick={manualRefresh}
                disabled={!selectedAccount || busy}
              >
                Обновить
              </button>

              <div className="status-switch">
                {STATUS_OPTIONS.map((status) => (
                  <button
                    type="button"
                    key={status}
                    className={`status-chip ${statusClass(status)} ${
                      selectedAccount?.status === status ? "active" : ""
                    }`}
                    onClick={() => setSelectedStatus(status)}
                    disabled={!selectedAccount || busy}
                    title={STATUS_LABELS[status]}
                  >
                    {STATUS_SHORT_LABELS[status]}
                  </button>
                ))}
              </div>
            </div>
          </header>

          <section className="panel-card inbox-card">
            <table className="message-table">
              <thead>
                <tr>
                  <th>От кого</th>
                  <th>Тема</th>
                  <th>Время</th>
                </tr>
              </thead>
              <tbody>
                {messages.map((message) => (
                  <tr
                    key={message.id}
                    className={messageDetail?.id === message.id ? "active" : ""}
                    onClick={() => openMessage(message)}
                  >
                    <td>{message.sender}</td>
                    <td>{message.subject}</td>
                    <td>{toLocalDateTime(message.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {!messages.length ? <div className="empty-list">Писем пока нет</div> : null}
          </section>

          <section className="panel-card viewer-card">
            <div className="viewer-head">
              <h3>Содержание письма</h3>
              {messageDetail?.code ? (
                <button type="button" onClick={copyCode}>
                  Копировать код {messageDetail.code}
                </button>
              ) : null}
            </div>

            <div className="viewer-content">
              {messageDetail ? (
                <>
                  <p>
                    <strong>От:</strong> {messageDetail.sender}
                  </p>
                  <p>
                    <strong>Тема:</strong> {messageDetail.subject}
                  </p>
                  <pre>{messageDetail.text}</pre>
                </>
              ) : (
                <p className="placeholder-text">Выберите письмо, чтобы увидеть содержимое.</p>
              )}
            </div>
          </section>
        </main>
      </div>

      {showSkPanel ? (
        <GeneratorPanel
          title="South Korea Data Generator"
          data={skData}
          busy={busy}
          activeAction={skActiveAction}
          hotkeys={generatorHotkeys}
          onClose={closeSkGenerator}
          onGenerate={regenerateSk}
          onSettings={openGeneratorHotkeys}
          onCopy={(action) => copyGeneratorAction("sk", action)}
        />
      ) : null}

      {showInPanel ? (
        <GeneratorPanel
          title="India Data Generator"
          data={inData}
          busy={busy}
          activeAction={inActiveAction}
          hotkeys={generatorHotkeys}
          onClose={closeInGenerator}
          onGenerate={regenerateIn}
          onSettings={openGeneratorHotkeys}
          onCopy={(action) => copyGeneratorAction("in", action)}
        />
      ) : null}

      {showGeneratorHotkeys ? (
        <HotkeySettingsModal
          draftHotkeys={draftHotkeys}
          recordingHotkeyKey={recordingHotkeyKey}
          onClose={closeGeneratorHotkeys}
          onSave={saveGeneratorHotkeys}
          onReset={resetGeneratorHotkeys}
          onStartRecord={toggleHotkeyRecord}
          onClearHotkey={clearDraftHotkey}
        />
      ) : null}

      <footer className="status-bar">{statusMessage}</footer>
    </div>
  );
}
