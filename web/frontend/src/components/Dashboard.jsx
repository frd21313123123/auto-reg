import { useEffect, useRef, useState } from "react";

import { accountsApi, mailApi } from "../api";

const QUICK_STATUS_OPTIONS = [
  { value: "not_registered", label: "Не рег" },
  { value: "registered", label: "Рег" },
  { value: "plus", label: "Plus" }
];

const EXTRA_STATUS_OPTIONS = [
  { value: "banned", label: "Banned" },
  { value: "invalid_password", label: "Пароль" }
];

const FOLDER_FILTER_ALL = "all";
const FOLDER_FILTER_UNASSIGNED = "unassigned";
const MAIL_LIST_MIN_HEIGHT = 220;
const MAIL_VIEWER_MIN_HEIGHT = 280;
const MAIL_PANEL_RESIZER_HEIGHT = 14;
const MAIL_PANEL_RATIO_STORAGE_KEY = "auto_reg_mail_list_ratio";
const LEGACY_MAIL_PANEL_HEIGHT_STORAGE_KEY = "auto_reg_mail_list_height";
const DEFAULT_MAIL_PANEL_RATIO = 0.48;

const STATUS_LABELS = {
  not_registered: "Не зарегистрирован",
  registered: "Зарегистрирован",
  plus: "Plus",
  banned: "Banned",
  invalid_password: "Неверный пароль",
  business: "Business"
};

function getFolderIdFromFilter(folderFilter) {
  if (folderFilter === FOLDER_FILTER_ALL || folderFilter === FOLDER_FILTER_UNASSIGNED) {
    return null;
  }

  return Number(folderFilter);
}

function getFolderFilterLabel(folderFilter, folders) {
  if (folderFilter === FOLDER_FILTER_ALL) {
    return "Все почты";
  }
  if (folderFilter === FOLDER_FILTER_UNASSIGNED) {
    return "Без папки";
  }

  return folders.find((folder) => String(folder.id) === folderFilter)?.name || "Папка";
}

function getDeleteAllPayload(folderFilter) {
  if (folderFilter === FOLDER_FILTER_ALL) {
    return { scope: "all" };
  }
  if (folderFilter === FOLDER_FILTER_UNASSIGNED) {
    return { scope: "unassigned" };
  }

  return {
    scope: "folder",
    folder_id: Number(folderFilter)
  };
}

function getDeleteAllLabel(folderFilter) {
  if (folderFilter === FOLDER_FILTER_ALL) {
    return "Удалить всё";
  }
  if (folderFilter === FOLDER_FILTER_UNASSIGNED) {
    return "Очистить без папки";
  }

  return "Очистить папку";
}

function filterAccountsByFolder(accounts, folderFilter) {
  if (folderFilter === FOLDER_FILTER_ALL) {
    return accounts;
  }
  if (folderFilter === FOLDER_FILTER_UNASSIGNED) {
    return accounts.filter((account) => !account.folder_id);
  }

  const folderId = Number(folderFilter);
  return accounts.filter((account) => account.folder_id === folderId);
}

function formatTimestamp(value) {
  if (!value) {
    return "—";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "short",
    timeStyle: "short"
  }).format(parsed);
}

function makeAccountLine(account) {
  const mailPassword = account.password_mail || account.password_openai || "";
  const openAiPassword = account.password_openai || mailPassword;
  const passwords =
    openAiPassword && mailPassword && openAiPassword !== mailPassword
      ? `${openAiPassword};${mailPassword}`
      : openAiPassword || mailPassword;

  return `${account.email} / ${passwords} / ${account.status}`;
}

function formatEmailForDisplay(email) {
  return String(email ?? "").replace(/([@._+-])/g, "$1\u200b");
}

function downloadText(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function buildExcelDocument(accounts) {
  const statusColors = {
    not_registered: "#ffffff",
    registered: "#d9e1f2",
    plus: "#46bdc6",
    banned: "#fecaca",
    invalid_password: "#e9d5ff",
    business: "#c7f9cc"
  };

  const rows = accounts
    .map((account) => {
      const color = statusColors[account.status] || "#ffffff";
      return `
        <tr style="background:${color}">
          <td>${escapeHtml(makeAccountLine(account))}</td>
          <td>${escapeHtml(account.email)}</td>
          <td>${escapeHtml(account.password_openai)}</td>
          <td>${escapeHtml(account.password_mail)}</td>
          <td>${escapeHtml(STATUS_LABELS[account.status] || account.status)}</td>
        </tr>
      `;
    })
    .join("");

  return `
    <html>
      <head>
        <meta charset="utf-8" />
      </head>
      <body>
        <table border="1">
          <thead>
            <tr>
              <th>Полная строка</th>
              <th>Email</th>
              <th>OpenAI</th>
              <th>Почта</th>
              <th>Статус</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </body>
    </html>
  `;
}

async function copyText(value) {
  if (!value) {
    return;
  }

  await navigator.clipboard.writeText(String(value));
}

function readStoredMailListRatio() {
  try {
    const value = Number(localStorage.getItem(MAIL_PANEL_RATIO_STORAGE_KEY));
    return Number.isFinite(value) && value > 0 && value < 1 ? value : null;
  } catch {
    return null;
  }
}

function readStoredLegacyMailListHeight() {
  try {
    const value = Number(localStorage.getItem(LEGACY_MAIL_PANEL_HEIGHT_STORAGE_KEY));
    return Number.isFinite(value) && value > 0 ? value : null;
  } catch {
    return null;
  }
}

function getMailPanelAvailableHeight(stack) {
  if (!stack) {
    return 0;
  }

  return Math.max(stack.getBoundingClientRect().height - MAIL_PANEL_RESIZER_HEIGHT, 1);
}

function clampMailListRatio(ratio, stack) {
  const availableHeight = getMailPanelAvailableHeight(stack);
  if (!availableHeight || !Number.isFinite(ratio)) {
    return DEFAULT_MAIL_PANEL_RATIO;
  }

  const minRatio = Math.min(MAIL_LIST_MIN_HEIGHT / availableHeight, 1);
  const maxRatio = Math.max(
    Math.min((availableHeight - MAIL_VIEWER_MIN_HEIGHT) / availableHeight, 1),
    minRatio
  );

  return Math.min(Math.max(ratio, minRatio), maxRatio);
}

function convertHeightToRatio(height, stack) {
  const availableHeight = getMailPanelAvailableHeight(stack);
  if (!availableHeight || !Number.isFinite(height)) {
    return DEFAULT_MAIL_PANEL_RATIO;
  }

  return clampMailListRatio(height / availableHeight, stack);
}

export default function Dashboard({ token, user, onLogout }) {
  const importFileRef = useRef(null);
  const inboxRefreshRef = useRef(false);
  const generatorWindowsRef = useRef({});
  const mailStackRef = useRef(null);
  const mailPanelDragRef = useRef(null);

  const [folders, setFolders] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [selectedFolderFilter, setSelectedFolderFilter] = useState(FOLDER_FILTER_ALL);
  const [selectedAccountIds, setSelectedAccountIds] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [selectedMessageId, setSelectedMessageId] = useState(null);
  const [messageDetail, setMessageDetail] = useState(null);
  const [folderName, setFolderName] = useState("");
  const [moveTargetFolder, setMoveTargetFolder] = useState(FOLDER_FILTER_UNASSIGNED);
  const [importText, setImportText] = useState("");
  const [foldersLoading, setFoldersLoading] = useState(false);
  const [accountsLoading, setAccountsLoading] = useState(false);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [createBusy, setCreateBusy] = useState(false);
  const [folderBusy, setFolderBusy] = useState(false);
  const [importBusy, setImportBusy] = useState(false);
  const [banBusy, setBanBusy] = useState(false);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [mailListRatio, setMailListRatio] = useState(() => readStoredMailListRatio());
  const [isResizingMailPanels, setIsResizingMailPanels] = useState(false);
  const [statusText, setStatusText] = useState("Готов к работе");

  const visibleAccounts = filterAccountsByFolder(accounts, selectedFolderFilter);
  const selectedAccount =
    visibleAccounts.find((account) => account.id === selectedAccountId) || null;
  const selectedMessage =
    messages.find((message) => message.id === selectedMessageId) || null;
  const currentFolderLabel = getFolderFilterLabel(selectedFolderFilter, folders);
  const messageHtml = detailLoading ? "" : String(messageDetail?.html || "").trim();
  const visibleAccountIds = visibleAccounts.map((account) => account.id);
  const selectedVisibleCount = visibleAccountIds.filter((id) =>
    selectedAccountIds.includes(id)
  ).length;
  const allVisibleSelected =
    visibleAccountIds.length > 0 && visibleAccountIds.every((id) => selectedAccountIds.includes(id));
  const mailStackStyle = mailListRatio
    ? {
        gridTemplateRows: `minmax(${MAIL_LIST_MIN_HEIGHT}px, ${mailListRatio}fr) ${MAIL_PANEL_RESIZER_HEIGHT}px minmax(${MAIL_VIEWER_MIN_HEIGHT}px, ${Math.max(1 - mailListRatio, 0.01)}fr)`
      }
    : undefined;

  const loadFolders = async () => {
    try {
      setFoldersLoading(true);
      const nextFolders = await accountsApi.listFolders(token);
      setFolders(nextFolders);
    } catch (error) {
      setStatusText(error.message);
    } finally {
      setFoldersLoading(false);
    }
  };

  const loadAccounts = async (preferredAccountId = null) => {
    try {
      setAccountsLoading(true);
      const nextAccounts = await accountsApi.list(token);
      setAccounts(nextAccounts);

      setSelectedAccountId((currentValue) => {
        if (
          preferredAccountId &&
          nextAccounts.some((account) => account.id === preferredAccountId)
        ) {
          return preferredAccountId;
        }
        if (currentValue && nextAccounts.some((account) => account.id === currentValue)) {
          return currentValue;
        }
        return nextAccounts[0]?.id ?? null;
      });

      if (!nextAccounts.length) {
        setMessages([]);
        setSelectedMessageId(null);
        setMessageDetail(null);
      }

      setStatusText(`Аккаунтов: ${nextAccounts.length}`);
    } catch (error) {
      setStatusText(error.message);
    } finally {
      setAccountsLoading(false);
    }
  };

  const loadMessages = async (accountId, options = {}) => {
    const { ensureConnection = false, silent = false } = options;
    if (!accountId || inboxRefreshRef.current) {
      return;
    }

    inboxRefreshRef.current = true;

    try {
      if (!silent) {
        setMessagesLoading(true);
        setStatusText("Обновление писем...");
      }

      if (ensureConnection) {
        try {
          await mailApi.connect(token, accountId);
        } catch (error) {
          if (!silent) {
            setStatusText(error.message);
          }
        }
      }

      const nextMessages = await mailApi.messages(token, accountId);
      setMessages(nextMessages);
      setSelectedMessageId((currentValue) => {
        if (currentValue && nextMessages.some((message) => message.id === currentValue)) {
          return currentValue;
        }
        return nextMessages[0]?.id ?? null;
      });
      if (!nextMessages.length) {
        setMessageDetail(null);
      }
      if (!silent) {
        setStatusText(`Писем: ${nextMessages.length}`);
      }
    } catch (error) {
      if (!silent) {
        setStatusText(error.message);
      }
    } finally {
      inboxRefreshRef.current = false;
      setMessagesLoading(false);
    }
  };

  const loadMessageDetail = async (accountId, message) => {
    if (!accountId || !message) {
      setMessageDetail(null);
      return;
    }

    try {
      setDetailLoading(true);
      const detail = await mailApi.messageDetail(
        token,
        accountId,
        message.id,
        message.sender,
        message.subject
      );
      setMessageDetail(detail);
    } catch (error) {
      setMessageDetail({
        id: message.id,
        sender: message.sender,
        subject: message.subject,
        text: error.message,
        code: null
      });
      setStatusText(error.message);
    } finally {
      setDetailLoading(false);
    }
  };

  const openGeneratorPopup = (kind) => {
    const popupUrl = new URL(window.location.origin + window.location.pathname);
    popupUrl.searchParams.set("popup", kind);

    const screenLeft = typeof window.screenLeft === "number" ? window.screenLeft : 0;
    const screenTop = typeof window.screenTop === "number" ? window.screenTop : 0;
    const width = 560;
    const height = 760;
    const left = Math.max(screenLeft + Math.round((window.outerWidth - width) / 2), 0);
    const top = Math.max(screenTop + Math.round((window.outerHeight - height) / 2), 0);
    const popupName = kind === "in" ? "auto-reg-generator-in" : "auto-reg-generator-sk";
    const features = [
      "popup=yes",
      `width=${width}`,
      `height=${height}`,
      `left=${left}`,
      `top=${top}`,
      "resizable=yes",
      "scrollbars=yes"
    ].join(",");

    const existingWindow = generatorWindowsRef.current[kind];
    if (existingWindow && !existingWindow.closed) {
      existingWindow.location.href = popupUrl.toString();
      existingWindow.focus();
      setStatusText(`Окно ${kind.toUpperCase()} уже открыто`);
      return;
    }

    const popupWindow = window.open(popupUrl.toString(), popupName, features);
    if (!popupWindow) {
      setStatusText("Браузер заблокировал popup окно");
      return;
    }

    generatorWindowsRef.current[kind] = popupWindow;
    popupWindow.focus();
    setStatusText(`Открыто окно ${kind.toUpperCase()}`);
  };

  useEffect(() => {
    void Promise.all([loadFolders(), loadAccounts()]);
  }, [token]);

  useEffect(() => {
    return () => {
      Object.values(generatorWindowsRef.current).forEach((popupWindow) => {
        if (popupWindow && !popupWindow.closed) {
          popupWindow.close();
        }
      });
    };
  }, []);

  useEffect(() => {
    try {
      if (mailListRatio) {
        localStorage.setItem(MAIL_PANEL_RATIO_STORAGE_KEY, String(mailListRatio));
      } else {
        localStorage.removeItem(MAIL_PANEL_RATIO_STORAGE_KEY);
      }
      localStorage.removeItem(LEGACY_MAIL_PANEL_HEIGHT_STORAGE_KEY);
    } catch {
      return;
    }
  }, [mailListRatio]);

  useEffect(() => {
    if (mailListRatio) {
      return undefined;
    }

    const stack = mailStackRef.current;
    const legacyHeight = readStoredLegacyMailListHeight();
    if (!stack || !legacyHeight) {
      return undefined;
    }

    setMailListRatio(convertHeightToRatio(legacyHeight, stack));
    return undefined;
  }, [mailListRatio]);

  useEffect(() => {
    setSelectedAccountIds([]);
  }, [selectedFolderFilter]);

  useEffect(() => {
    setSelectedAccountIds((currentValue) =>
      currentValue.filter((accountId) =>
        accounts.some((account) => account.id === accountId)
      )
    );
  }, [accounts]);

  useEffect(() => {
    setMoveTargetFolder((currentValue) => {
      if (currentValue === FOLDER_FILTER_UNASSIGNED) {
        return currentValue;
      }
      return folders.some((folder) => String(folder.id) === currentValue)
        ? currentValue
        : FOLDER_FILTER_UNASSIGNED;
    });
  }, [folders]);

  useEffect(() => {
    if (selectedAccountId && visibleAccounts.some((account) => account.id === selectedAccountId)) {
      return;
    }

    const nextAccountId = visibleAccounts[0]?.id ?? null;
    if (nextAccountId !== selectedAccountId) {
      setSelectedAccountId(nextAccountId);
    }
  }, [accounts, selectedAccountId, selectedFolderFilter]);

  useEffect(() => {
    if (!isResizingMailPanels) {
      return undefined;
    }

    const handlePointerMove = (event) => {
      const dragState = mailPanelDragRef.current;
      if (!dragState) {
        return;
      }

      const nextHeight = dragState.startHeight + (event.clientY - dragState.startY);
      setMailListRatio(convertHeightToRatio(nextHeight, dragState.stack));
    };

    const stopResizing = () => {
      mailPanelDragRef.current = null;
      setIsResizingMailPanels(false);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", stopResizing);
    window.addEventListener("pointercancel", stopResizing);

    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", stopResizing);
      window.removeEventListener("pointercancel", stopResizing);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [isResizingMailPanels]);

  useEffect(() => {
    if (!selectedAccountId) {
      setMessages([]);
      setSelectedMessageId(null);
      setMessageDetail(null);
      return;
    }

    // Reset the viewer only when switching accounts, not on every inbox poll.
    setMessages([]);
    setSelectedMessageId(null);
    setMessageDetail(null);
    loadMessages(selectedAccountId, { ensureConnection: true });
  }, [selectedAccountId]);

  useEffect(() => {
    if (!selectedAccountId) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      loadMessages(selectedAccountId, { silent: true });
    }, 5000);

    return () => window.clearInterval(timer);
  }, [selectedAccountId]);

  useEffect(() => {
    if (!selectedAccountId || !selectedMessageId) {
      setMessageDetail(null);
      return;
    }

    const nextMessage = messages.find((message) => message.id === selectedMessageId);
    if (!nextMessage) {
      setMessageDetail(null);
      return;
    }

    loadMessageDetail(selectedAccountId, nextMessage);
  }, [selectedAccountId, selectedMessageId]);

  const handleCreateFolder = async () => {
    const nextFolderName = folderName.trim();
    if (!nextFolderName) {
      setStatusText("Введите название папки");
      return;
    }

    try {
      setFolderBusy(true);
      const createdFolder = await accountsApi.createFolder(token, nextFolderName);
      setFolderName("");
      setSelectedFolderFilter(String(createdFolder.id));
      setMoveTargetFolder(String(createdFolder.id));
      await loadFolders();
      setStatusText(`Папка создана: ${createdFolder.name}`);
    } catch (error) {
      setStatusText(error.message);
    } finally {
      setFolderBusy(false);
    }
  };

  const handleCreateAccount = async () => {
    try {
      setCreateBusy(true);
      const createdAccount = await accountsApi.createMailTm(
        token,
        12,
        getFolderIdFromFilter(selectedFolderFilter)
      );
      await Promise.all([loadFolders(), loadAccounts(createdAccount.id)]);
      setStatusText(`Создан: ${createdAccount.email}`);
    } catch (error) {
      setStatusText(error.message);
    } finally {
      setCreateBusy(false);
    }
  };

  const handleRefreshWorkspace = async () => {
    await Promise.all([loadFolders(), loadAccounts(selectedAccountId)]);
    if (selectedAccountId) {
      await loadMessages(selectedAccountId, { ensureConnection: true });
    }
  };

  const handleUpdateStatus = async (status) => {
    if (!selectedAccount) {
      return;
    }

    try {
      await accountsApi.updateStatus(token, selectedAccount.id, status);
      await loadAccounts(selectedAccount.id);
      setStatusText(`Статус обновлён: ${STATUS_LABELS[status] || status}`);
    } catch (error) {
      setStatusText(error.message);
    }
  };

  const handleBanCheck = async () => {
    const accountIds = accounts
      .filter((account) => !["banned", "invalid_password"].includes(account.status))
      .map((account) => account.id);

    if (!accountIds.length) {
      setStatusText("Нет аккаунтов для проверки");
      return;
    }

    try {
      setBanBusy(true);
      const result = await mailApi.banCheckBulk(token, accountIds);
      await loadAccounts(selectedAccountId);
      setStatusText(
        `Проверено: ${result.checked} | Забанено: ${result.banned} | Неверный пароль: ${result.invalid_password}`
      );
    } catch (error) {
      setStatusText(error.message);
    } finally {
      setBanBusy(false);
    }
  };

  const handleImport = async (rawText = importText) => {
    const cleanText = rawText.trim();
    if (!cleanText) {
      setStatusText("Вставьте аккаунты для импорта");
      return;
    }

    try {
      setImportBusy(true);
      const result = await accountsApi.importAccounts(
        token,
        cleanText,
        getFolderIdFromFilter(selectedFolderFilter)
      );
      await Promise.all([loadFolders(), loadAccounts(selectedAccountId)]);
      setStatusText(
        `Импорт: +${result.added} | Дубликаты: ${result.duplicates} | Пропущено: ${result.skipped}`
      );
      setImportText(cleanText);
    } catch (error) {
      setStatusText(error.message);
    } finally {
      setImportBusy(false);
    }
  };

  const handleClipboardPaste = async () => {
    try {
      const clipboardText = await navigator.clipboard.readText();
      setImportText(clipboardText);
      setStatusText("Текст из буфера вставлен");
    } catch (error) {
      setStatusText(error.message || "Не удалось прочитать буфер");
    }
  };

  const handleImportFileChange = async (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    try {
      const fileText = await file.text();
      setImportText(fileText);
      setStatusText(`Файл загружен: ${file.name}`);
    } catch (error) {
      setStatusText(error.message);
    } finally {
      event.target.value = "";
    }
  };

  const handleExportTxt = () => {
    downloadText("accounts.txt", accounts.map(makeAccountLine).join("\n"), "text/plain;charset=utf-8");
    setStatusText("TXT экспорт готов");
  };

  const handleExportExcel = () => {
    downloadText(
      "accounts.xls",
      buildExcelDocument(accounts),
      "application/vnd.ms-excel;charset=utf-8"
    );
    setStatusText("Excel экспорт готов");
  };

  const handleCopyField = async (value, label) => {
    try {
      await copyText(value);
      setStatusText(`Скопировано: ${label}`);
    } catch (error) {
      setStatusText(error.message || "Не удалось скопировать");
    }
  };

  const handleAccountSelection = (accountId, checked) => {
    setSelectedAccountIds((currentValue) => {
      if (checked) {
        return currentValue.includes(accountId) ? currentValue : [...currentValue, accountId];
      }
      return currentValue.filter((id) => id !== accountId);
    });
  };

  const handleToggleVisibleSelection = () => {
    if (!visibleAccountIds.length) {
      return;
    }

    setSelectedAccountIds((currentValue) => {
      if (allVisibleSelected) {
        return currentValue.filter((id) => !visibleAccountIds.includes(id));
      }
      return Array.from(new Set([...currentValue, ...visibleAccountIds]));
    });
  };

  const handleDeleteAccount = async (account, event) => {
    event.stopPropagation();

    try {
      setBulkBusy(true);
      await accountsApi.remove(token, account.id);
      setSelectedAccountIds((currentValue) => currentValue.filter((id) => id !== account.id));
      await Promise.all([
        loadFolders(),
        loadAccounts(selectedAccountId === account.id ? null : selectedAccountId)
      ]);
      setStatusText(`Удалена: ${account.email}`);
    } catch (error) {
      setStatusText(error.message);
    } finally {
      setBulkBusy(false);
    }
  };

  const handleBulkDelete = async () => {
    if (!selectedAccountIds.length) {
      setStatusText("Сначала выделите почты");
      return;
    }

    if (!window.confirm(`Удалить выбранные почты: ${selectedAccountIds.length}?`)) {
      return;
    }

    try {
      setBulkBusy(true);
      const result = await accountsApi.bulkDelete(token, selectedAccountIds);
      setSelectedAccountIds([]);
      await Promise.all([loadFolders(), loadAccounts(selectedAccountId)]);
      setStatusText(`Удалено почт: ${result.affected}`);
    } catch (error) {
      setStatusText(error.message);
    } finally {
      setBulkBusy(false);
    }
  };

  const handleMoveSelected = async () => {
    if (!selectedAccountIds.length) {
      setStatusText("Сначала выделите почты");
      return;
    }

    try {
      setBulkBusy(true);
      const folderId =
        moveTargetFolder === FOLDER_FILTER_UNASSIGNED ? null : Number(moveTargetFolder);
      const result = await accountsApi.moveBulk(token, selectedAccountIds, folderId);
      setSelectedAccountIds([]);
      await Promise.all([loadFolders(), loadAccounts(selectedAccountId)]);
      const destinationLabel =
        moveTargetFolder === FOLDER_FILTER_UNASSIGNED
          ? "Без папки"
          : getFolderFilterLabel(moveTargetFolder, folders);
      setStatusText(`Перенесено: ${result.affected} → ${destinationLabel}`);
    } catch (error) {
      setStatusText(error.message);
    } finally {
      setBulkBusy(false);
    }
  };

  const handleDeleteAll = async () => {
    if (!visibleAccounts.length) {
      setStatusText("Нет почт для удаления");
      return;
    }

    const deleteLabel = getDeleteAllLabel(selectedFolderFilter);
    if (!window.confirm(`${deleteLabel}? Будут удалены ${visibleAccounts.length} почт.`)) {
      return;
    }

    try {
      setBulkBusy(true);
      const result = await accountsApi.deleteAll(token, getDeleteAllPayload(selectedFolderFilter));
      setSelectedAccountIds([]);
      await Promise.all([loadFolders(), loadAccounts(null)]);
      setStatusText(`Удалено почт: ${result.affected}`);
    } catch (error) {
      setStatusText(error.message);
    } finally {
      setBulkBusy(false);
    }
  };

  const handleMailPanelResizeStart = (event) => {
    const stack = mailStackRef.current;
    if (!stack) {
      return;
    }

    const messagesCard = stack.querySelector(".offline-messages-card");
    const initialHeight = messagesCard
      ? Math.round(messagesCard.getBoundingClientRect().height)
      : Math.round(
          getMailPanelAvailableHeight(stack) * (mailListRatio || DEFAULT_MAIL_PANEL_RATIO)
        );

    mailPanelDragRef.current = {
      startY: event.clientY,
      startHeight: initialHeight,
      stack
    };

    setIsResizingMailPanels(true);
    document.body.style.cursor = "row-resize";
    document.body.style.userSelect = "none";
    event.preventDefault();
  };

  return (
    <div className="dashboard offline-dashboard">
      <div className="offline-shell">
        <aside className="offline-sidebar">
          <section className="offline-card offline-sidebar-head">
            <div>
              <p className="offline-eyebrow">Auto-Reg Web</p>
              <h1>Mail.tm</h1>
              <p className="offline-sidebar-user">{user.username}</p>
            </div>
            <button type="button" className="ghost-button" onClick={onLogout}>
              Выйти
            </button>
          </section>

          <button
            type="button"
            className="offline-create-button"
            onClick={handleCreateAccount}
            disabled={createBusy}
          >
            {createBusy ? "Создание..." : `+ Создать аккаунт в "${currentFolderLabel}"`}
          </button>

          <section className="offline-card">
            <div className="offline-section-heading">
              <span>ПАПКИ</span>
              <strong>{folders.length}</strong>
            </div>

            <div className="offline-folder-list">
              <button
                type="button"
                className={`offline-folder-item ${
                  selectedFolderFilter === FOLDER_FILTER_ALL ? "active" : ""
                }`}
                onClick={() => setSelectedFolderFilter(FOLDER_FILTER_ALL)}
              >
                <span>Все почты</span>
                <strong>{accounts.length}</strong>
              </button>

              <button
                type="button"
                className={`offline-folder-item ${
                  selectedFolderFilter === FOLDER_FILTER_UNASSIGNED ? "active" : ""
                }`}
                onClick={() => setSelectedFolderFilter(FOLDER_FILTER_UNASSIGNED)}
              >
                <span>Без папки</span>
                <strong>{accounts.filter((account) => !account.folder_id).length}</strong>
              </button>

              {folders.map((folder) => (
                <button
                  key={folder.id}
                  type="button"
                  className={`offline-folder-item ${
                    selectedFolderFilter === String(folder.id) ? "active" : ""
                  }`}
                  onClick={() => setSelectedFolderFilter(String(folder.id))}
                >
                  <span>{folder.name}</span>
                  <strong>
                    {accounts.filter((account) => account.folder_id === folder.id).length}
                  </strong>
                </button>
              ))}
            </div>

            <div className="offline-folder-create">
              <input
                value={folderName}
                onChange={(event) => setFolderName(event.target.value)}
                placeholder="Новая папка"
                maxLength={120}
              />
              <button type="button" onClick={handleCreateFolder} disabled={folderBusy}>
                {folderBusy ? "..." : "Создать"}
              </button>
            </div>

            <p className="offline-folder-note">
              {foldersLoading
                ? "Обновляю папки..."
                : `Новые аккаунты и импорт идут в: ${currentFolderLabel}`}
            </p>
          </section>

          <section className="offline-card">
            <div className="offline-section-heading">
              <span>АККАУНТЫ</span>
              <strong>{visibleAccounts.length}</strong>
            </div>

            <div className="offline-inline-buttons quad">
              <button type="button" onClick={handleRefreshWorkspace} disabled={accountsLoading}>
                Обновить
              </button>
              <button type="button" onClick={handleExportTxt} disabled={!accounts.length}>
                TXT
              </button>
              <button type="button" onClick={handleExportExcel} disabled={!accounts.length}>
                Excel
              </button>
              <button type="button" onClick={handleBanCheck} disabled={banBusy || !accounts.length}>
                {banBusy ? "..." : "Бан"}
              </button>
            </div>

            <div className="offline-inline-buttons quad">
              <button
                type="button"
                onClick={handleToggleVisibleSelection}
                disabled={!visibleAccounts.length}
              >
                {allVisibleSelected ? "Снять всё" : "Выбрать всё"}
              </button>
              <button
                type="button"
                onClick={() => setSelectedAccountIds([])}
                disabled={!selectedAccountIds.length}
              >
                Снять
              </button>
              <button
                type="button"
                className="danger-inline"
                onClick={handleBulkDelete}
                disabled={bulkBusy || !selectedAccountIds.length}
              >
                Удалить
              </button>
              <button
                type="button"
                className="danger-inline"
                onClick={handleDeleteAll}
                disabled={bulkBusy || !visibleAccounts.length}
              >
                {getDeleteAllLabel(selectedFolderFilter)}
              </button>
            </div>

            <div className="offline-bulk-row">
              <select
                value={moveTargetFolder}
                onChange={(event) => setMoveTargetFolder(event.target.value)}
              >
                <option value={FOLDER_FILTER_UNASSIGNED}>Без папки</option>
                {folders.map((folder) => (
                  <option key={folder.id} value={String(folder.id)}>
                    {folder.name}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={handleMoveSelected}
                disabled={bulkBusy || !selectedAccountIds.length}
              >
                Перенести
              </button>
            </div>

            <p className="offline-folder-note">
              Текущая папка: {currentFolderLabel}. Выбрано: {selectedVisibleCount} из{" "}
              {visibleAccounts.length}.
            </p>

            <div className="offline-account-list">
              {accountsLoading ? <div className="empty-state compact">Загрузка аккаунтов...</div> : null}

              {!accountsLoading && !accounts.length ? (
                <div className="empty-state compact">
                  Аккаунтов пока нет. Создайте mail.tm аккаунт или импортируйте список ниже.
                </div>
              ) : null}

              {!accountsLoading && accounts.length > 0 && !visibleAccounts.length ? (
                <div className="empty-state compact">В этой папке пока пусто.</div>
              ) : null}

              {visibleAccounts.map((account) => {
                const isSelected = selectedAccountIds.includes(account.id);
                const isActive = account.id === selectedAccountId;

                return (
                  <div
                    key={account.id}
                    className={`offline-account-item ${
                      isActive ? "active" : ""
                    } ${isSelected ? "selected-for-bulk" : ""}`}
                  >
                    <label
                      className="offline-account-checkbox"
                      onClick={(event) => event.stopPropagation()}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={(event) =>
                          handleAccountSelection(account.id, event.target.checked)
                        }
                      />
                    </label>

                    <button
                      type="button"
                      className="offline-account-main"
                      onClick={() => setSelectedAccountId(account.id)}
                    >
                      <div className="offline-account-item-top">
                        <div>
                          <div className="offline-account-email" title={account.email}>
                            {formatEmailForDisplay(account.email)}
                          </div>
                          <small className="offline-account-folder">
                            {account.folder_name || "Без папки"}
                          </small>
                        </div>
                        <span className={`offline-status-chip status-${account.status}`}>
                          {STATUS_LABELS[account.status] || account.status}
                        </span>
                      </div>
                    </button>

                    <button
                      type="button"
                      className="offline-account-delete"
                      aria-label={`Удалить ${account.email}`}
                      onClick={(event) => handleDeleteAccount(account, event)}
                    >
                      ×
                    </button>
                  </div>
                );
              })}
            </div>
          </section>

          <section className="offline-card">
            <div className="offline-section-heading">
              <span>ДЕЙСТВИЯ</span>
            </div>

            <div className="offline-inline-buttons">
              <button
                type="button"
                onClick={() => handleCopyField(selectedAccount?.email, "Email")}
                disabled={!selectedAccount}
              >
                Email
              </button>
              <button
                type="button"
                onClick={() => handleCopyField(selectedAccount?.password_openai, "OpenAI")}
                disabled={!selectedAccount}
              >
                OpenAI
              </button>
              <button
                type="button"
                onClick={() => handleCopyField(selectedAccount?.password_mail, "Почта")}
                disabled={!selectedAccount}
              >
                Почта
              </button>
            </div>

            <div className="offline-inline-buttons">
              <button
                type="button"
                onClick={() => openGeneratorPopup("sk")}
              >
                SK
              </button>
              <button type="button" disabled title="Доступно только в офлайн версии">
                Настройки
              </button>
            </div>

            <div className="offline-import-panel">
              <textarea
                className="import-textarea"
                value={importText}
                onChange={(event) => setImportText(event.target.value)}
                placeholder="email / password_openai;password_mail / status"
              />
              <div className="offline-inline-buttons">
                <button type="button" onClick={() => handleImport()} disabled={importBusy}>
                  {importBusy ? "Импорт..." : "Импорт"}
                </button>
                <button type="button" onClick={() => importFileRef.current?.click()}>
                  Файл
                </button>
                <button type="button" onClick={handleClipboardPaste}>
                  Буфер
                </button>
              </div>
              <input
                ref={importFileRef}
                type="file"
                accept=".txt,.csv,.tsv"
                hidden
                onChange={handleImportFileChange}
              />
            </div>
          </section>

        </aside>

        <main className="offline-main">
          <section className="offline-card offline-account-head">
            <div>
              <p className="offline-eyebrow">Аккаунт</p>
              <h2>{selectedAccount?.email || "Аккаунт не выбран"}</h2>
              <p className="offline-account-meta">
                {selectedAccount
                  ? `Папка: ${selectedAccount.folder_name || "Без папки"} | Почта: ${selectedAccount.password_mail} | OpenAI: ${selectedAccount.password_openai}`
                  : "Выберите аккаунт слева, чтобы открыть inbox и письмо."}
              </p>
            </div>

            <div className="offline-head-actions">
              <div className="offline-inline-buttons compact">
                {QUICK_STATUS_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    className={`offline-status-button status-${option.value}`}
                    onClick={() => handleUpdateStatus(option.value)}
                    disabled={!selectedAccount}
                  >
                    {option.label}
                  </button>
                ))}
              </div>

              <div className="offline-inline-buttons compact">
                {EXTRA_STATUS_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    className={`offline-status-button status-${option.value}`}
                    onClick={() => handleUpdateStatus(option.value)}
                    disabled={!selectedAccount}
                  >
                    {option.label}
                  </button>
                ))}
                <button
                  type="button"
                  className="primary-inline"
                  onClick={() =>
                    selectedAccountId && loadMessages(selectedAccountId, { ensureConnection: true })
                  }
                  disabled={!selectedAccountId}
                >
                  Обновить
                </button>
              </div>
            </div>
          </section>

          <div ref={mailStackRef} className="offline-mail-stack" style={mailStackStyle}>
            <section className="offline-card offline-messages-card">
              <div className="offline-panel-heading border-bottom">
                <div>
                  <h3>Входящие</h3>
                  <p>{selectedAccount ? `Всего писем: ${messages.length}` : "Нет выбранного аккаунта"}</p>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    selectedAccountId && loadMessages(selectedAccountId, { ensureConnection: true })
                  }
                  disabled={!selectedAccountId}
                >
                  {messagesLoading ? "Загрузка..." : "Обновить"}
                </button>
              </div>

              <div className="offline-message-list">
                {!selectedAccount ? (
                  <div className="empty-state">Выберите аккаунт в левом списке.</div>
                ) : null}

                {selectedAccount && !messages.length && !messagesLoading ? (
                  <div className="empty-state">Писем пока нет.</div>
                ) : null}

                {messages.map((message) => (
                  <button
                    key={message.id}
                    type="button"
                    className={`offline-message-row ${
                      message.id === selectedMessageId ? "active" : ""
                    }`}
                    onClick={() => setSelectedMessageId(message.id)}
                  >
                    <div className="offline-message-main">
                      <strong>{message.sender || "Неизвестно"}</strong>
                      <span>{message.subject || "(без темы)"}</span>
                    </div>
                    <time>{formatTimestamp(message.created_at)}</time>
                  </button>
                ))}
              </div>
            </section>

            <button
              type="button"
              className={`offline-panel-resizer ${isResizingMailPanels ? "is-dragging" : ""}`}
              aria-label="Изменить высоту блоков писем"
              onDoubleClick={() => setMailListRatio(null)}
              onPointerDown={handleMailPanelResizeStart}
            >
              <span className="offline-panel-resizer-line" />
            </button>

            <section className="offline-card offline-viewer-card">
              <div className="offline-panel-heading border-bottom">
                <div>
                  <h3>{selectedMessage?.subject || "Просмотр письма"}</h3>
                  <p>{selectedMessage ? `От: ${selectedMessage.sender}` : "Выберите письмо, чтобы увидеть содержимое."}</p>
                </div>
                {messageDetail?.code ? (
                  <button type="button" onClick={() => handleCopyField(messageDetail.code, "Код")}>
                    Копировать код
                  </button>
                ) : null}
              </div>

              <div className="offline-message-detail">
                {detailLoading ? (
                  <pre>Загрузка...</pre>
                ) : messageHtml ? (
                  <>
                    <iframe
                      title="HTML preview"
                      className="offline-message-html"
                      sandbox="allow-popups allow-popups-to-escape-sandbox"
                      srcDoc={messageHtml}
                    />
                    {messageDetail?.text ? (
                      <details className="offline-message-raw">
                        <summary>Сырой текст</summary>
                        <pre>{messageDetail.text}</pre>
                      </details>
                    ) : null}
                  </>
                ) : (
                  <pre>{messageDetail?.text || "Выберите письмо, чтобы увидеть содержимое."}</pre>
                )}
              </div>
            </section>
          </div>
        </main>
      </div>

      <footer className="status-bar offline-status-bar">{statusText}</footer>
    </div>
  );
}
