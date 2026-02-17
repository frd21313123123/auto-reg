import { useEffect, useMemo, useRef, useState } from "react";

import { accountsApi, mailApi, toolsApi } from "../api";
import ParallaxDotsBackground from "./ParallaxDotsBackground";

const I = {
  refresh: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/></svg>,
  fileImport: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><polyline points="9 15 12 12 15 15"/></svg>,
  table: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/><line x1="9" y1="3" x2="9" y2="21"/><line x1="15" y1="3" x2="15" y2="21"/></svg>,
  window: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="18" rx="2"/><line x1="2" y1="9" x2="22" y2="9"/><line x1="10" y1="9" x2="10" y2="21"/></svg>,
  shieldX: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="9" y1="9" x2="15" y2="15"/><line x1="15" y1="9" x2="9" y2="15"/></svg>,
  at: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="4"/><path d="M16 8v5a3 3 0 0 0 6 0v-1a10 10 0 1 0-3.92 7.94"/></svg>,
  key: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.78 7.78 5.5 5.5 0 0 1 7.78-7.78zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>,
  lock: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>,
  copy: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>,
  clipboard: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/></svg>,
  bomb: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="13" r="8"/><path d="M16.2 7.8l2-2"/><path d="M18 4l2 2"/><path d="M21 3l-1 1"/></svg>,
  gear: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>,
  chevronUp: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="18 15 12 9 6 15"/></svg>,
  chevronDown: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"/></svg>,
  sun: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>,
  moon: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>,
  logout: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>,
  record: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="6" fill="currentColor"/></svg>,
  eraser: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>,
  check: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>,
  reset: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M2.5 2v6h6"/><path d="M2.5 8a10 10 0 1 1 .5 4"/></svg>,
  trash: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>,
  mailX: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/><line x1="14" y1="14" x2="20" y2="20"/><line x1="20" y1="14" x2="14" y2="20"/></svg>,
  upload: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>,
  dice: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="2" width="20" height="20" rx="3"/><circle cx="8" cy="8" r="1" fill="currentColor"/><circle cx="16" cy="8" r="1" fill="currentColor"/><circle cx="8" cy="16" r="1" fill="currentColor"/><circle cx="16" cy="16" r="1" fill="currentColor"/><circle cx="12" cy="12" r="1" fill="currentColor"/></svg>,
  close: (s = 16) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>,
};

const STATUS_OPTIONS = [
  "not_registered",
  "registered",
  "plus",
  "business",
  "banned",
  "invalid_password"
];

const STATUS_LABELS = {
  not_registered: "Не зарегистрирован",
  registered: "Зарегистрирован",
  plus: "Plus",
  business: "Business",
  busnis: "Business",
  banned: "Banned",
  invalid_password: "Неверный пароль"
};

const STATUS_SHORT_LABELS = {
  not_registered: "Не рег",
  registered: "Рег",
  plus: "Plus",
  business: "Business",
  busnis: "Business",
  banned: "Бан",
  invalid_password: "Пароль"
};

function normalizeAccountStatus(status) {
  return status === "busnis" ? "business" : status;
}

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
  return `status-${normalizeAccountStatus(status)}`;
}

const ACCOUNTS_WINDOW_MIN_WIDTH = 620;
const ACCOUNTS_WINDOW_MIN_HEIGHT = 320;
const ACCOUNTS_WINDOW_MARGIN = 12;
const ACCOUNTS_WINDOW_BOTTOM_GAP = 56;
const GENERATOR_WINDOW_MIN_WIDTH = 520;
const GENERATOR_WINDOW_MIN_HEIGHT = 360;
const SETTINGS_WINDOW_MIN_WIDTH = 500;
const SETTINGS_WINDOW_MIN_HEIGHT = 320;
const IMPORT_WINDOW_MIN_WIDTH = 520;
const IMPORT_WINDOW_MIN_HEIGHT = 300;
const MAIL_INBOX_MIN_HEIGHT = 170;
const MAIL_VIEWER_MIN_HEIGHT = 170;
const MAIL_RESIZE_HANDLE_HEIGHT = 10;
const MAIL_RESIZE_HIT_ZONE = 16;
const SIDEBAR_DRAG_MARGIN = 8;

function clampValue(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function clampMailInboxHeight(value, containerHeight) {
  const maxHeight = Math.max(
    MAIL_INBOX_MIN_HEIGHT,
    containerHeight - MAIL_RESIZE_HANDLE_HEIGHT - MAIL_VIEWER_MIN_HEIGHT
  );
  return clampValue(value, MAIL_INBOX_MIN_HEIGHT, maxHeight);
}

function buildAccountsWindowDefaultRect() {
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const maxWidth = Math.max(360, viewportWidth - ACCOUNTS_WINDOW_MARGIN * 2);
  const maxHeight = Math.max(240, viewportHeight - ACCOUNTS_WINDOW_BOTTOM_GAP - ACCOUNTS_WINDOW_MARGIN);
  const width = Math.min(920, Math.max(640, Math.round(viewportWidth * 0.72), ACCOUNTS_WINDOW_MIN_WIDTH, maxWidth));
  const height = Math.min(520, Math.max(340, Math.round(viewportHeight * 0.62), ACCOUNTS_WINDOW_MIN_HEIGHT, maxHeight));
  return {
    x: Math.max(ACCOUNTS_WINDOW_MARGIN, Math.round((viewportWidth - width) / 2)),
    y: Math.max(ACCOUNTS_WINDOW_MARGIN, Math.round((viewportHeight - height) / 2)),
    width: Math.min(width, maxWidth),
    height: Math.min(height, maxHeight)
  };
}

function buildAccountsWindowMaxRect(isMobile) {
  if (isMobile) {
    return {
      x: 0,
      y: 0,
      width: window.innerWidth,
      height: window.innerHeight
    };
  }

  const margin = 10;
  const width = Math.max(360, window.innerWidth - margin * 2);
  const height = Math.max(260, window.innerHeight - ACCOUNTS_WINDOW_BOTTOM_GAP - margin);
  return {
    x: margin,
    y: margin,
    width,
    height
  };
}

function clampAccountsWindowRect(rect, isMobile) {
  if (isMobile) {
    return buildAccountsWindowMaxRect(true);
  }

  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const availableWidth = Math.max(360, viewportWidth - ACCOUNTS_WINDOW_MARGIN * 2);
  const availableHeight = Math.max(
    260,
    viewportHeight - ACCOUNTS_WINDOW_BOTTOM_GAP - ACCOUNTS_WINDOW_MARGIN
  );
  const width = clampValue(rect.width, ACCOUNTS_WINDOW_MIN_WIDTH, availableWidth);
  const height = clampValue(rect.height, ACCOUNTS_WINDOW_MIN_HEIGHT, availableHeight);
  const maxX = Math.max(ACCOUNTS_WINDOW_MARGIN, viewportWidth - width - ACCOUNTS_WINDOW_MARGIN);
  const maxY = Math.max(
    ACCOUNTS_WINDOW_MARGIN,
    viewportHeight - ACCOUNTS_WINDOW_BOTTOM_GAP - height
  );

  return {
    ...rect,
    width,
    height,
    x: clampValue(rect.x, ACCOUNTS_WINDOW_MARGIN, maxX),
    y: clampValue(rect.y, ACCOUNTS_WINDOW_MARGIN, maxY)
  };
}

function buildGeneratorWindowDefaultRect() {
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const maxWidth = Math.max(360, viewportWidth - ACCOUNTS_WINDOW_MARGIN * 2);
  const maxHeight = Math.max(260, viewportHeight - ACCOUNTS_WINDOW_BOTTOM_GAP - ACCOUNTS_WINDOW_MARGIN);
  const width = Math.min(700, Math.max(560, Math.round(viewportWidth * 0.56), GENERATOR_WINDOW_MIN_WIDTH, maxWidth));
  const height = Math.min(620, Math.max(420, Math.round(viewportHeight * 0.7), GENERATOR_WINDOW_MIN_HEIGHT, maxHeight));
  return {
    x: Math.max(ACCOUNTS_WINDOW_MARGIN, Math.round((viewportWidth - width) / 2)),
    y: Math.max(ACCOUNTS_WINDOW_MARGIN, Math.round((viewportHeight - height) / 2)),
    width: Math.min(width, maxWidth),
    height: Math.min(height, maxHeight)
  };
}

function buildGeneratorWindowMaxRect(isMobile) {
  if (isMobile) {
    return {
      x: 0,
      y: 0,
      width: window.innerWidth,
      height: window.innerHeight
    };
  }

  const margin = 10;
  return {
    x: margin,
    y: margin,
    width: Math.max(360, window.innerWidth - margin * 2),
    height: Math.max(260, window.innerHeight - ACCOUNTS_WINDOW_BOTTOM_GAP - margin)
  };
}

function clampGeneratorWindowRect(rect, isMobile) {
  if (isMobile) {
    return buildGeneratorWindowMaxRect(true);
  }

  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const availableWidth = Math.max(360, viewportWidth - ACCOUNTS_WINDOW_MARGIN * 2);
  const availableHeight = Math.max(
    260,
    viewportHeight - ACCOUNTS_WINDOW_BOTTOM_GAP - ACCOUNTS_WINDOW_MARGIN
  );
  const width = clampValue(rect.width, GENERATOR_WINDOW_MIN_WIDTH, availableWidth);
  const height = clampValue(rect.height, GENERATOR_WINDOW_MIN_HEIGHT, availableHeight);
  const maxX = Math.max(ACCOUNTS_WINDOW_MARGIN, viewportWidth - width - ACCOUNTS_WINDOW_MARGIN);
  const maxY = Math.max(
    ACCOUNTS_WINDOW_MARGIN,
    viewportHeight - ACCOUNTS_WINDOW_BOTTOM_GAP - height
  );
  return {
    ...rect,
    width,
    height,
    x: clampValue(rect.x, ACCOUNTS_WINDOW_MARGIN, maxX),
    y: clampValue(rect.y, ACCOUNTS_WINDOW_MARGIN, maxY)
  };
}

function buildSettingsWindowDefaultRect() {
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const maxWidth = Math.max(360, viewportWidth - ACCOUNTS_WINDOW_MARGIN * 2);
  const maxHeight = Math.max(240, viewportHeight - ACCOUNTS_WINDOW_BOTTOM_GAP - ACCOUNTS_WINDOW_MARGIN);
  const width = Math.min(620, Math.max(520, Math.round(viewportWidth * 0.48), SETTINGS_WINDOW_MIN_WIDTH, maxWidth));
  const height = Math.min(640, Math.max(430, Math.round(viewportHeight * 0.7), SETTINGS_WINDOW_MIN_HEIGHT, maxHeight));
  return {
    x: Math.max(ACCOUNTS_WINDOW_MARGIN, Math.round((viewportWidth - width) / 2)),
    y: Math.max(ACCOUNTS_WINDOW_MARGIN, Math.round((viewportHeight - height) / 2)),
    width: Math.min(width, maxWidth),
    height: Math.min(height, maxHeight)
  };
}

function buildSettingsWindowMaxRect(isMobile) {
  if (isMobile) {
    return {
      x: 0,
      y: 0,
      width: window.innerWidth,
      height: window.innerHeight
    };
  }

  const margin = 10;
  return {
    x: margin,
    y: margin,
    width: Math.max(360, window.innerWidth - margin * 2),
    height: Math.max(260, window.innerHeight - ACCOUNTS_WINDOW_BOTTOM_GAP - margin)
  };
}

function clampSettingsWindowRect(rect, isMobile) {
  if (isMobile) {
    return buildSettingsWindowMaxRect(true);
  }

  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const availableWidth = Math.max(360, viewportWidth - ACCOUNTS_WINDOW_MARGIN * 2);
  const availableHeight = Math.max(
    260,
    viewportHeight - ACCOUNTS_WINDOW_BOTTOM_GAP - ACCOUNTS_WINDOW_MARGIN
  );
  const width = clampValue(rect.width, SETTINGS_WINDOW_MIN_WIDTH, availableWidth);
  const height = clampValue(rect.height, SETTINGS_WINDOW_MIN_HEIGHT, availableHeight);
  const maxX = Math.max(ACCOUNTS_WINDOW_MARGIN, viewportWidth - width - ACCOUNTS_WINDOW_MARGIN);
  const maxY = Math.max(
    ACCOUNTS_WINDOW_MARGIN,
    viewportHeight - ACCOUNTS_WINDOW_BOTTOM_GAP - height
  );
  return {
    ...rect,
    width,
    height,
    x: clampValue(rect.x, ACCOUNTS_WINDOW_MARGIN, maxX),
    y: clampValue(rect.y, ACCOUNTS_WINDOW_MARGIN, maxY)
  };
}

function buildImportWindowDefaultRect() {
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const maxWidth = Math.max(360, viewportWidth - ACCOUNTS_WINDOW_MARGIN * 2);
  const maxHeight = Math.max(240, viewportHeight - ACCOUNTS_WINDOW_BOTTOM_GAP - ACCOUNTS_WINDOW_MARGIN);
  const width = Math.min(740, Math.max(560, Math.round(viewportWidth * 0.52), IMPORT_WINDOW_MIN_WIDTH, maxWidth));
  const height = Math.min(520, Math.max(360, Math.round(viewportHeight * 0.56), IMPORT_WINDOW_MIN_HEIGHT, maxHeight));
  return {
    x: Math.max(ACCOUNTS_WINDOW_MARGIN, Math.round((viewportWidth - width) / 2)),
    y: Math.max(ACCOUNTS_WINDOW_MARGIN, Math.round((viewportHeight - height) / 2)),
    width: Math.min(width, maxWidth),
    height: Math.min(height, maxHeight)
  };
}

function buildImportWindowMaxRect(isMobile) {
  if (isMobile) {
    return {
      x: 0,
      y: 0,
      width: window.innerWidth,
      height: window.innerHeight
    };
  }

  const margin = 10;
  return {
    x: margin,
    y: margin,
    width: Math.max(360, window.innerWidth - margin * 2),
    height: Math.max(260, window.innerHeight - ACCOUNTS_WINDOW_BOTTOM_GAP - margin)
  };
}

function clampImportWindowRect(rect, isMobile) {
  if (isMobile) {
    return buildImportWindowMaxRect(true);
  }

  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const availableWidth = Math.max(360, viewportWidth - ACCOUNTS_WINDOW_MARGIN * 2);
  const availableHeight = Math.max(
    260,
    viewportHeight - ACCOUNTS_WINDOW_BOTTOM_GAP - ACCOUNTS_WINDOW_MARGIN
  );
  const width = clampValue(rect.width, IMPORT_WINDOW_MIN_WIDTH, availableWidth);
  const height = clampValue(rect.height, IMPORT_WINDOW_MIN_HEIGHT, availableHeight);
  const maxX = Math.max(ACCOUNTS_WINDOW_MARGIN, viewportWidth - width - ACCOUNTS_WINDOW_MARGIN);
  const maxY = Math.max(
    ACCOUNTS_WINDOW_MARGIN,
    viewportHeight - ACCOUNTS_WINDOW_BOTTOM_GAP - height
  );
  return {
    ...rect,
    width,
    height,
    x: clampValue(rect.x, ACCOUNTS_WINDOW_MARGIN, maxX),
    y: clampValue(rect.y, ACCOUNTS_WINDOW_MARGIN, maxY)
  };
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

function validateImportAccountsText(text) {
  const lines = String(text || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (!lines.length) {
    return { ok: false, lineNumber: null, reason: "Добавьте минимум одну строку для импорта" };
  }

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const lineNumber = index + 1;
    const parts = line.split(" / ");

    if (parts.length !== 3) {
      return {
        ok: false,
        lineNumber,
        reason: "используйте формат: email / pass;pass / status"
      };
    }

    const [emailRaw, passwordsRaw, statusRaw] = parts.map((part) => part.trim());
    if (!emailRaw || !emailRaw.includes("@")) {
      return { ok: false, lineNumber, reason: "некорректный email" };
    }

    const passwordParts = passwordsRaw.split(";");
    if (passwordParts.length !== 2 || !passwordParts[0].trim() || !passwordParts[1].trim()) {
      return { ok: false, lineNumber, reason: "пароли должны быть в формате pass;pass" };
    }

    const normalizedStatus = normalizeAccountStatus(statusRaw.toLowerCase());
    if (!STATUS_OPTIONS.includes(normalizedStatus)) {
      return {
        ok: false,
        lineNumber,
        reason: `неизвестный статус "${statusRaw}" (допустимо: ${STATUS_OPTIONS.join(", ")})`
      };
    }
  }

  return { ok: true, lineNumber: null, reason: "" };
}

function formatAccountCredentials(account) {
  if (!account) {
    return "";
  }
  return `${account.email}:${account.password_openai};${account.password_mail}`;
}

async function copyText(value) {
  if (!value) {
    return;
  }
  await navigator.clipboard.writeText(value);
}

function HtmlEmailViewer({ html }) {
  const iframeRef = useRef(null);

  useEffect(() => {
    const iframe = iframeRef.current;
    if (!iframe || !html) {
      return;
    }

    const styleOverride = `<style>
      body { margin: 0; padding: 10px; font-family: "Segoe UI", Tahoma, sans-serif; font-size: 14px; line-height: 1.5; word-break: break-word; overflow-wrap: anywhere; color: #e6efff; background: transparent; }
      a { color: #6fa0ff; }
      img { max-width: 100%; height: auto; }
      table { max-width: 100% !important; }
    </style>`;
    const doc = iframe.contentDocument;
    doc.open();
    doc.write(`<!DOCTYPE html><html><head><meta charset="utf-8">${styleOverride}</head><body>${html}</body></html>`);
    doc.close();

    const resize = () => {
      try {
        const height = doc.documentElement.scrollHeight || doc.body.scrollHeight;
        iframe.style.height = `${Math.max(height + 16, 80)}px`;
      } catch {
        /* cross-origin guard */
      }
    };

    resize();
    const timer = setTimeout(resize, 300);
    return () => clearTimeout(timer);
  }, [html]);

  return (
    <iframe
      ref={iframeRef}
      className="html-email-iframe"
      sandbox="allow-same-origin"
      title="Email content"
    />
  );
}

// DarkParallaxDotsBackground is now shared — see ParallaxDotsBackground.jsx

function GeneratorPanel({
  title,
  data,
  busy,
  activeAction,
  hotkeys,
  windowStyle,
  minimized,
  maximized,
  isMobile,
  isDragging,
  onClose,
  onHeaderMouseDown,
  onToggleMinimize,
  onToggleMaximize,
  onGenerate,
  onSettings,
  onCopy
}) {
  return (
    <div className="generator-overlay">
      <section
        className={`generator-modal ${minimized ? "is-minimized" : ""} ${maximized ? "is-maximized" : ""}`}
        style={windowStyle}
      >
        <header
          className={`generator-modal-header ${isDragging ? "dragging" : ""}`}
          onMouseDown={onHeaderMouseDown}
        >
          <h3>{title}</h3>
          <div className="generator-window-actions" onMouseDown={(event) => event.stopPropagation()}>
            <button
              type="button"
              className="generator-window-action refresh"
              onClick={onGenerate}
              disabled={busy}
              title="Сгенерировать"
            >
              ↻
            </button>
            <button
              type="button"
              className="generator-window-action"
              onClick={onToggleMinimize}
              title={minimized ? "Развернуть" : "Свернуть"}
            >
              {minimized ? "▢" : "—"}
            </button>
            {!isMobile ? (
              <button
                type="button"
                className="generator-window-action"
                onClick={onToggleMaximize}
                title={maximized ? "Восстановить" : "Развернуть"}
              >
                {maximized ? "❐" : "□"}
              </button>
            ) : null}
            <button
              type="button"
              className="generator-window-action close"
              onClick={onClose}
              aria-label="Закрыть"
            >
              ×
            </button>
          </div>
        </header>

        {!minimized ? (
          <>
            <div className="generator-modal-body">
              {GENERATOR_FIELDS.map((field) => (
                <div className={`generator-field ${activeAction === field.action ? "active" : ""}`} key={field.action}>
                  <div className="generator-field-label">{field.label}</div>
                  <div className={`generator-field-input-row ${activeAction === field.action ? "highlight" : ""}`}>
                    <input value={data?.[field.dataKey] || ""} readOnly />
                    <button type="button" onClick={() => onCopy(field.action)} title="Копировать">
                      {I.clipboard(18)}
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="generator-modal-actions">
              <button type="button" className="primary-btn" onClick={onGenerate} disabled={busy} title="Сгенерировать">
                {I.refresh(18)}
              </button>
              <button type="button" onClick={onSettings} title="Настройки">
                {I.gear(18)}
              </button>
            </div>

            <div className="generator-hotkeys">
              {hotkeyHintText(hotkeys)}
            </div>
          </>
        ) : (
          <div className="generator-minimized-info">Окно свернуто</div>
        )}
      </section>
    </div>
  );
}
function HotkeySettingsModal({
  windowStyle,
  minimized,
  maximized,
  isMobile,
  isDragging,
  busy,
  selectedAccount,
  accountsCount,
  draftHotkeys,
  recordingHotkeyKey,
  onClose,
  onHeaderMouseDown,
  onToggleMinimize,
  onToggleMaximize,
  onSave,
  onReset,
  onStartRecord,
  onClearHotkey,
  onDeleteAccount,
  onDeleteMailbox,
  onDeleteAllAccounts
}) {
  return (
    <div className="hotkeys-overlay">
      <section
        className={`hotkeys-modal ${minimized ? "is-minimized" : ""} ${maximized ? "is-maximized" : ""}`}
        style={windowStyle}
      >
        <header
          className={`hotkeys-header ${isDragging ? "dragging" : ""}`}
          onMouseDown={onHeaderMouseDown}
        >
          <h3>Настройки горячих клавиш</h3>
          <div className="hotkeys-window-actions" onMouseDown={(event) => event.stopPropagation()}>
            <button
              type="button"
              className="hotkeys-window-action"
              onClick={onToggleMinimize}
              title={minimized ? "Развернуть" : "Свернуть"}
            >
              {minimized ? "▢" : "—"}
            </button>
            {!isMobile ? (
              <button
                type="button"
                className="hotkeys-window-action"
                onClick={onToggleMaximize}
                title={maximized ? "Восстановить" : "Развернуть"}
              >
                {maximized ? "❐" : "□"}
              </button>
            ) : null}
            <button
              type="button"
              className="hotkeys-window-action close"
              onClick={onClose}
              aria-label="Закрыть"
            >
              ×
            </button>
          </div>
        </header>

        {!minimized ? (
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
                    title={recordingHotkeyKey === field.key ? "Нажмите клавишу..." : "Записать"}
                  >
                    {I.record()}
                  </button>
                  <button type="button" onClick={() => onClearHotkey(field.key)} title="Очистить">
                    {I.eraser()}
                  </button>
                </div>
              </label>
            ))}

            <div className="hotkeys-actions">
              <button type="submit" className="primary-btn" title="Сохранить">
                {I.check()}
              </button>
              <button type="button" onClick={onReset} title="Сбросить">
                {I.reset()}
              </button>
              <button type="button" onClick={onClose} title="Закрыть">
                {I.close()}
              </button>
            </div>

            <section className="hotkeys-danger-zone">
              <div className="hotkeys-danger-title">Управление записями</div>
              <div className="hotkeys-danger-subtitle">
                {selectedAccount
                  ? `Выбран: ${selectedAccount.email}`
                  : "Аккаунт не выбран"}
              </div>
              <div className="hotkeys-danger-actions">
                <button
                  type="button"
                  onClick={onDeleteAccount}
                  disabled={!selectedAccount || busy}
                  title="Удалить запись"
                >
                  {I.trash()}
                </button>
                <button
                  type="button"
                  onClick={onDeleteMailbox}
                  disabled={!selectedAccount || busy}
                  title="Удалить почту"
                >
                  {I.mailX()}
                </button>
                <button
                  type="button"
                  className="danger-btn"
                  onClick={onDeleteAllAccounts}
                  disabled={!accountsCount || busy}
                  title="Удалить все записи"
                >
                  {I.trash()} ({accountsCount})
                </button>
              </div>
            </section>
          </form>
        ) : (
          <div className="hotkeys-minimized-info">Окно свернуто</div>
        )}
      </section>
    </div>
  );
}

function useIsMobile(breakpoint = 768) {
  const [isMobile, setIsMobile] = useState(() => window.innerWidth <= breakpoint);

  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${breakpoint}px)`);
    const handler = (e) => setIsMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [breakpoint]);

  return isMobile;
}

export default function Dashboard({ token, user, onLogout }) {
  const [statusMessage, setStatusMessage] = useState("Готово");
  const isMobile = useIsMobile();
  const [mobileTab, setMobileTab] = useState("accounts");

  const [accounts, setAccounts] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [messageDetail, setMessageDetail] = useState(null);
  const [mailInboxHeight, setMailInboxHeight] = useState(() =>
    Math.max(240, Math.round(window.innerHeight * 0.35))
  );
  const [isInboxResizeReady, setIsInboxResizeReady] = useState(false);
  const [sidebarOffset, setSidebarOffset] = useState({ x: 0, y: 0 });
  const [sidebarWidth, setSidebarWidth] = useState(() => Math.round(window.innerWidth * 0.47));
  const [isDraggingSplitter, setIsDraggingSplitter] = useState(false);

  const [importText, setImportText] = useState("");
  const [showImportWindow, setShowImportWindow] = useState(false);
  const [importWindowMinimized, setImportWindowMinimized] = useState(false);
  const [importWindowMaximized, setImportWindowMaximized] = useState(false);
  const [importWindowRect, setImportWindowRect] = useState(() => buildImportWindowDefaultRect());
  const [isDraggingImportWindow, setIsDraggingImportWindow] = useState(false);

  const [randomPerson, setRandomPerson] = useState({ name: "", birthdate: "" });
  const [inData, setInData] = useState(null);
  const [skData, setSkData] = useState(null);

  const [busy, setBusy] = useState(false);
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
  const [showAccountsDataWindow, setShowAccountsDataWindow] = useState(false);
  const [accountsWindowMinimized, setAccountsWindowMinimized] = useState(false);
  const [accountsWindowMaximized, setAccountsWindowMaximized] = useState(false);
  const [accountsWindowRect, setAccountsWindowRect] = useState(() => buildAccountsWindowDefaultRect());
  const [isDraggingAccountsWindow, setIsDraggingAccountsWindow] = useState(false);
  const [windowSelectedAccountIds, setWindowSelectedAccountIds] = useState([]);
  const [generatorWindowMinimized, setGeneratorWindowMinimized] = useState(false);
  const [generatorWindowMaximized, setGeneratorWindowMaximized] = useState(false);
  const [generatorWindowRect, setGeneratorWindowRect] = useState(() => buildGeneratorWindowDefaultRect());
  const [isDraggingGeneratorWindow, setIsDraggingGeneratorWindow] = useState(false);
  const [settingsWindowMinimized, setSettingsWindowMinimized] = useState(false);
  const [settingsWindowMaximized, setSettingsWindowMaximized] = useState(false);
  const [settingsWindowRect, setSettingsWindowRect] = useState(() => buildSettingsWindowDefaultRect());
  const [isDraggingSettingsWindow, setIsDraggingSettingsWindow] = useState(false);
  const [isResizingMailPanels, setIsResizingMailPanels] = useState(false);
  const [isDraggingSidebar, setIsDraggingSidebar] = useState(false);
  const accountsWindowDragRef = useRef(null);
  const accountsWindowRestoreRef = useRef(null);
  const accountsSelectionAnchorRef = useRef(null);
  const accountsWindowElementRef = useRef(null);
  const sidebarPanelRef = useRef(null);
  const sidebarDragRef = useRef(null);
  const splitterDragRef = useRef(null);
  const generatorWindowDragRef = useRef(null);
  const generatorWindowRestoreRef = useRef(null);
  const settingsWindowDragRef = useRef(null);
  const settingsWindowRestoreRef = useRef(null);
  const importWindowDragRef = useRef(null);
  const importWindowRestoreRef = useRef(null);
  const mailPanelsRef = useRef(null);
  const mailPanelsResizeRef = useRef(null);

  const selectedAccount = useMemo(
    () => accounts.find((item) => item.id === selectedAccountId) || null,
    [accounts, selectedAccountId]
  );
  const effectiveWindowSelectedAccountIds = useMemo(() => {
    if (windowSelectedAccountIds.length) {
      return windowSelectedAccountIds;
    }
    return selectedAccountId ? [selectedAccountId] : [];
  }, [windowSelectedAccountIds, selectedAccountId]);
  const selectedAccountsInWindow = useMemo(() => {
    const selectedSet = new Set(effectiveWindowSelectedAccountIds);
    return accounts.filter((item) => selectedSet.has(item.id));
  }, [accounts, effectiveWindowSelectedAccountIds]);
  const selectedAccountCredentials = useMemo(
    () => selectedAccountsInWindow.map((item) => formatAccountCredentials(item)).filter(Boolean).join("\n"),
    [selectedAccountsInWindow]
  );
  const windowSelectedSet = useMemo(
    () => new Set(effectiveWindowSelectedAccountIds),
    [effectiveWindowSelectedAccountIds]
  );
  const activeGeneratorType = showSkPanel ? "sk" : showInPanel ? "in" : null;
  const isGeneratorWindowVisible = Boolean(activeGeneratorType);

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
    setGeneratorWindowMinimized(false);
    setGeneratorWindowMaximized(false);
    setIsDraggingGeneratorWindow(false);
    generatorWindowDragRef.current = null;
    generatorWindowRestoreRef.current = null;
  };

  const closeInGenerator = () => {
    setShowInPanel(false);
    setInCycleIndex(0);
    setInActiveAction(null);
    setGeneratorWindowMinimized(false);
    setGeneratorWindowMaximized(false);
    setIsDraggingGeneratorWindow(false);
    generatorWindowDragRef.current = null;
    generatorWindowRestoreRef.current = null;
  };

  const openAccountsDataWindow = () => {
    setShowAccountsDataWindow(true);
    setAccountsWindowMinimized(false);
    setWindowSelectedAccountIds((prev) => {
      if (prev.length) {
        return prev;
      }
      return selectedAccountId ? [selectedAccountId] : [];
    });
    if (selectedAccountId) {
      const selectedIndex = accounts.findIndex((item) => item.id === selectedAccountId);
      accountsSelectionAnchorRef.current = selectedIndex >= 0 ? selectedIndex : null;
    }
    if (isMobile) {
      setAccountsWindowMaximized(true);
      setAccountsWindowRect(buildAccountsWindowMaxRect(true));
      return;
    }
    setAccountsWindowRect((prev) => clampAccountsWindowRect(prev, false));
  };

  const closeAccountsDataWindow = () => {
    setShowAccountsDataWindow(false);
    setAccountsWindowMinimized(false);
    setAccountsWindowMaximized(false);
    setIsDraggingAccountsWindow(false);
    accountsWindowDragRef.current = null;
    accountsWindowRestoreRef.current = null;
    accountsSelectionAnchorRef.current = null;
  };

  const openImportWindow = () => {
    setShowImportWindow(true);
    setImportWindowMinimized(false);
    if (isMobile) {
      setImportWindowMaximized(true);
      setImportWindowRect(buildImportWindowMaxRect(true));
      return;
    }
    setImportWindowRect((prev) => clampImportWindowRect(prev, false));
  };

  const closeImportWindow = () => {
    setShowImportWindow(false);
    setImportWindowMinimized(false);
    setImportWindowMaximized(false);
    setIsDraggingImportWindow(false);
    importWindowDragRef.current = null;
    importWindowRestoreRef.current = null;
  };

  const toggleImportWindowMinimize = () => {
    setImportWindowMinimized((prev) => !prev);
  };

  const toggleImportWindowMaximize = () => {
    if (isMobile || !showImportWindow) {
      return;
    }

    if (importWindowMaximized) {
      setImportWindowMaximized(false);
      const restoreRect = importWindowRestoreRef.current || buildImportWindowDefaultRect();
      setImportWindowRect(clampImportWindowRect(restoreRect, false));
      importWindowRestoreRef.current = null;
      return;
    }

    importWindowRestoreRef.current = importWindowRect;
    setImportWindowMinimized(false);
    setImportWindowMaximized(true);
    setImportWindowRect(buildImportWindowMaxRect(false));
  };

  const startImportWindowDrag = (event) => {
    if (isMobile || importWindowMaximized || importWindowMinimized || !showImportWindow) {
      return;
    }
    if (event.button !== 0) {
      return;
    }

    event.preventDefault();
    importWindowDragRef.current = {
      offsetX: event.clientX - importWindowRect.x,
      offsetY: event.clientY - importWindowRect.y
    };
    setIsDraggingImportWindow(true);
  };

  const toggleAccountsWindowMinimize = () => {
    setAccountsWindowMinimized((prev) => !prev);
  };

  const toggleAccountsWindowMaximize = () => {
    if (isMobile) {
      return;
    }

    if (accountsWindowMaximized) {
      setAccountsWindowMaximized(false);
      const restoreRect = accountsWindowRestoreRef.current || buildAccountsWindowDefaultRect();
      setAccountsWindowRect(clampAccountsWindowRect(restoreRect, false));
      accountsWindowRestoreRef.current = null;
      return;
    }

    accountsWindowRestoreRef.current = accountsWindowRect;
    setAccountsWindowMinimized(false);
    setAccountsWindowMaximized(true);
    setAccountsWindowRect(buildAccountsWindowMaxRect(false));
  };

  const startAccountsWindowDrag = (event) => {
    if (isMobile || accountsWindowMaximized || accountsWindowMinimized) {
      return;
    }
    if (event.button !== 0) {
      return;
    }

    event.preventDefault();
    accountsWindowDragRef.current = {
      offsetX: event.clientX - accountsWindowRect.x,
      offsetY: event.clientY - accountsWindowRect.y
    };
    setIsDraggingAccountsWindow(true);
  };

  const startMailPanelsResize = (event) => {
    if (isMobile) {
      return;
    }
    if (event.button !== 0) {
      return;
    }

    const inboxCard = event.currentTarget;
    const inboxRect = inboxCard.getBoundingClientRect();
    const distanceFromBottom = inboxRect.bottom - event.clientY;
    if (distanceFromBottom > MAIL_RESIZE_HIT_ZONE) {
      return;
    }

    const container = mailPanelsRef.current;
    if (!container) {
      return;
    }

    event.preventDefault();
    setIsInboxResizeReady(false);
    mailPanelsResizeRef.current = {
      startY: event.clientY,
      startHeight: mailInboxHeight,
      containerHeight: Math.round(container.getBoundingClientRect().height)
    };
    setIsResizingMailPanels(true);
  };

  const handleInboxResizeHover = (event) => {
    if (isMobile || isResizingMailPanels) {
      return;
    }
    const bounds = event.currentTarget.getBoundingClientRect();
    const nearBottom = bounds.bottom - event.clientY <= MAIL_RESIZE_HIT_ZONE;
    setIsInboxResizeReady((prev) => (prev === nearBottom ? prev : nearBottom));
  };

  const clearInboxResizeHover = () => {
    setIsInboxResizeReady(false);
  };

  const startSidebarDrag = (event) => {
    if (isMobile) {
      return;
    }
    if (event.button !== 0) {
      return;
    }
    if (event.target instanceof Element && event.target.closest("button, input, textarea, select, a")) {
      return;
    }

    const panel = sidebarPanelRef.current;
    if (!panel) {
      return;
    }

    event.preventDefault();
    const rect = panel.getBoundingClientRect();
    sidebarDragRef.current = {
      startClientX: event.clientX,
      startClientY: event.clientY,
      startOffsetX: sidebarOffset.x,
      startOffsetY: sidebarOffset.y,
      baseLeft: rect.left - sidebarOffset.x,
      baseTop: rect.top - sidebarOffset.y,
      width: rect.width,
      height: rect.height
    };
    setIsDraggingSidebar(true);
  };

  const startSplitterDrag = (event) => {
    if (isMobile || event.button !== 0) return;
    event.preventDefault();
    splitterDragRef.current = { startX: event.clientX, startWidth: sidebarWidth };
    setIsDraggingSplitter(true);
  };

  const selectAccountFromDataWindow = (event, accountId, rowIndex) => {
    const withMeta = event.ctrlKey || event.metaKey;
    const withShift = event.shiftKey;
    let nextSelected = [accountId];

    if (withShift && accounts.length) {
      const anchorIndex =
        accountsSelectionAnchorRef.current == null ? rowIndex : accountsSelectionAnchorRef.current;
      const start = Math.min(anchorIndex, rowIndex);
      const end = Math.max(anchorIndex, rowIndex);
      const rangeIds = accounts.slice(start, end + 1).map((item) => item.id);
      if (withMeta) {
        const merged = new Set(windowSelectedAccountIds);
        rangeIds.forEach((id) => merged.add(id));
        nextSelected = Array.from(merged);
      } else {
        nextSelected = rangeIds;
      }
    } else if (withMeta) {
      const toggled = new Set(windowSelectedAccountIds);
      if (toggled.has(accountId)) {
        toggled.delete(accountId);
      } else {
        toggled.add(accountId);
      }
      nextSelected = Array.from(toggled);
      accountsSelectionAnchorRef.current = rowIndex;
    } else {
      nextSelected = [accountId];
      accountsSelectionAnchorRef.current = rowIndex;
    }

    setWindowSelectedAccountIds(nextSelected);
    setSelectedAccountId(accountId);
    if (isMobile) {
      setMobileTab("mail");
    }
  };

  const copySelectedAccountCredentials = async () => {
    if (!selectedAccountCredentials) {
      return;
    }
    await copyText(selectedAccountCredentials);
    const count = selectedAccountsInWindow.length;
    applyStatus(
      count > 1
        ? `Скопировано ${count} строк: почта:пароль;2пароль`
        : "Скопировано: почта:пароль;2пароль"
    );
  };

  const toggleGeneratorWindowMinimize = () => {
    setGeneratorWindowMinimized((prev) => !prev);
  };

  const toggleGeneratorWindowMaximize = () => {
    if (isMobile || !isGeneratorWindowVisible) {
      return;
    }

    if (generatorWindowMaximized) {
      setGeneratorWindowMaximized(false);
      const restoreRect = generatorWindowRestoreRef.current || buildGeneratorWindowDefaultRect();
      setGeneratorWindowRect(clampGeneratorWindowRect(restoreRect, false));
      generatorWindowRestoreRef.current = null;
      return;
    }

    generatorWindowRestoreRef.current = generatorWindowRect;
    setGeneratorWindowMinimized(false);
    setGeneratorWindowMaximized(true);
    setGeneratorWindowRect(buildGeneratorWindowMaxRect(false));
  };

  const startGeneratorWindowDrag = (event) => {
    if (isMobile || generatorWindowMaximized || generatorWindowMinimized || !isGeneratorWindowVisible) {
      return;
    }
    if (event.button !== 0) {
      return;
    }

    event.preventDefault();
    generatorWindowDragRef.current = {
      offsetX: event.clientX - generatorWindowRect.x,
      offsetY: event.clientY - generatorWindowRect.y
    };
    setIsDraggingGeneratorWindow(true);
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
    const normalizedResponse = response.map((item) => ({
      ...item,
      status: normalizeAccountStatus(item.status)
    }));
    setAccounts(normalizedResponse);

    if (!normalizedResponse.length) {
      setSelectedAccountId(null);
      setMessages([]);
      setMessageDetail(null);
      return;
    }

    const desiredId = nextSelectedId ?? selectedAccountId;
    const hasDesired = normalizedResponse.some((item) => item.id === desiredId);
    setSelectedAccountId(hasDesired ? desiredId : normalizedResponse[0].id);
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

  const openMessage = (message) =>
    withBusy(async () => {
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
      applyStatus(`Письмо открыто: ${detail.subject || message.subject}`);
    }, "Загрузка письма...");

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

  useEffect(() => {
    if (!isDraggingAccountsWindow) {
      return;
    }

    const handleMouseMove = (event) => {
      const drag = accountsWindowDragRef.current;
      if (!drag) {
        return;
      }

      setAccountsWindowRect((prev) =>
        clampAccountsWindowRect(
          {
            ...prev,
            x: event.clientX - drag.offsetX,
            y: event.clientY - drag.offsetY
          },
          false
        )
      );
    };

    const stopDrag = () => {
      setIsDraggingAccountsWindow(false);
      accountsWindowDragRef.current = null;
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };

    document.body.style.userSelect = "none";
    document.body.style.cursor = "grabbing";

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", stopDrag);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", stopDrag);
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };
  }, [isDraggingAccountsWindow]);

  useEffect(() => {
    const handleResize = () => {
      if (!showAccountsDataWindow) {
        return;
      }
      if (isMobile) {
        setAccountsWindowRect(buildAccountsWindowMaxRect(true));
        return;
      }
      if (accountsWindowMaximized) {
        setAccountsWindowRect(buildAccountsWindowMaxRect(false));
        return;
      }
      setAccountsWindowRect((prev) => clampAccountsWindowRect(prev, false));
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [showAccountsDataWindow, accountsWindowMaximized, isMobile]);

  useEffect(() => {
    if (!showAccountsDataWindow) {
      return;
    }

    if (isMobile) {
      setAccountsWindowMaximized(true);
      setAccountsWindowMinimized(false);
      setAccountsWindowRect(buildAccountsWindowMaxRect(true));
      return;
    }

    if (accountsWindowMaximized && !accountsWindowRestoreRef.current) {
      setAccountsWindowMaximized(false);
      setAccountsWindowRect(clampAccountsWindowRect(buildAccountsWindowDefaultRect(), false));
      return;
    }

    if (!accountsWindowMaximized) {
      setAccountsWindowRect((prev) => clampAccountsWindowRect(prev, false));
    }
  }, [isMobile, showAccountsDataWindow, accountsWindowMaximized]);

  useEffect(() => {
    if (!showAccountsDataWindow || isMobile || accountsWindowMaximized || accountsWindowMinimized) {
      return;
    }

    const windowElement = accountsWindowElementRef.current;
    if (!windowElement || typeof ResizeObserver === "undefined") {
      return;
    }

    const syncWindowSize = () => {
      const bounds = windowElement.getBoundingClientRect();
      const nextWidth = Math.round(bounds.width);
      const nextHeight = Math.round(bounds.height);
      setAccountsWindowRect((prev) => {
        const clamped = clampAccountsWindowRect(
          {
            ...prev,
            width: nextWidth,
            height: nextHeight
          },
          false
        );
        if (
          clamped.width === prev.width &&
          clamped.height === prev.height &&
          clamped.x === prev.x &&
          clamped.y === prev.y
        ) {
          return prev;
        }
        return clamped;
      });
    };

    const observer = new ResizeObserver(syncWindowSize);
    observer.observe(windowElement);
    return () => observer.disconnect();
  }, [showAccountsDataWindow, isMobile, accountsWindowMaximized, accountsWindowMinimized]);

  useEffect(() => {
    if (!isDraggingImportWindow) {
      return;
    }

    const handleMouseMove = (event) => {
      const drag = importWindowDragRef.current;
      if (!drag) {
        return;
      }

      setImportWindowRect((prev) =>
        clampImportWindowRect(
          {
            ...prev,
            x: event.clientX - drag.offsetX,
            y: event.clientY - drag.offsetY
          },
          false
        )
      );
    };

    const stopDrag = () => {
      setIsDraggingImportWindow(false);
      importWindowDragRef.current = null;
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };

    document.body.style.userSelect = "none";
    document.body.style.cursor = "grabbing";

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", stopDrag);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", stopDrag);
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };
  }, [isDraggingImportWindow]);

  useEffect(() => {
    const handleResize = () => {
      if (!showImportWindow) {
        return;
      }
      if (isMobile) {
        setImportWindowRect(buildImportWindowMaxRect(true));
        return;
      }
      if (importWindowMaximized) {
        setImportWindowRect(buildImportWindowMaxRect(false));
        return;
      }
      setImportWindowRect((prev) => clampImportWindowRect(prev, false));
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [showImportWindow, importWindowMaximized, isMobile]);

  useEffect(() => {
    if (!showImportWindow) {
      return;
    }

    if (isMobile) {
      setImportWindowMaximized(true);
      setImportWindowMinimized(false);
      setImportWindowRect(buildImportWindowMaxRect(true));
      return;
    }

    if (importWindowMaximized && !importWindowRestoreRef.current) {
      setImportWindowMaximized(false);
      setImportWindowRect(clampImportWindowRect(buildImportWindowDefaultRect(), false));
      return;
    }

    if (!importWindowMaximized) {
      setImportWindowRect((prev) => clampImportWindowRect(prev, false));
    }
  }, [isMobile, showImportWindow, importWindowMaximized]);

  useEffect(() => {
    setWindowSelectedAccountIds((prev) => {
      if (!prev.length) {
        return prev;
      }
      const existingIds = new Set(accounts.map((item) => item.id));
      const filtered = prev.filter((id) => existingIds.has(id));
      return filtered.length === prev.length ? prev : filtered;
    });
    if (accountsSelectionAnchorRef.current != null && accountsSelectionAnchorRef.current >= accounts.length) {
      accountsSelectionAnchorRef.current = accounts.length ? accounts.length - 1 : null;
    }
  }, [accounts]);

  useEffect(() => {
    if (!isResizingMailPanels) {
      return;
    }

    const handleMouseMove = (event) => {
      const resize = mailPanelsResizeRef.current;
      if (!resize) {
        return;
      }

      const nextRawHeight = resize.startHeight + (event.clientY - resize.startY);
      const nextHeight = clampMailInboxHeight(nextRawHeight, resize.containerHeight);
      setMailInboxHeight((prev) => (Math.abs(prev - nextHeight) < 1 ? prev : nextHeight));
    };

    const stopResize = () => {
      setIsResizingMailPanels(false);
      setIsInboxResizeReady(false);
      mailPanelsResizeRef.current = null;
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };

    document.body.style.userSelect = "none";
    document.body.style.cursor = "row-resize";

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", stopResize);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", stopResize);
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };
  }, [isResizingMailPanels]);

  useEffect(() => {
    if (isMobile) {
      return;
    }

    const container = mailPanelsRef.current;
    if (!container) {
      return;
    }

    const syncInboxHeight = () => {
      const containerHeight = Math.round(container.getBoundingClientRect().height);
      if (!containerHeight) {
        return;
      }
      setMailInboxHeight((prev) => {
        const clamped = clampMailInboxHeight(prev, containerHeight);
        return Math.abs(clamped - prev) < 1 ? prev : clamped;
      });
    };

    syncInboxHeight();

    if (typeof ResizeObserver === "undefined") {
      return;
    }

    const observer = new ResizeObserver(syncInboxHeight);
    observer.observe(container);
    return () => observer.disconnect();
  }, [isMobile]);

  useEffect(() => {
    if (!isDraggingSidebar) {
      return;
    }

    const handleMouseMove = (event) => {
      const drag = sidebarDragRef.current;
      if (!drag) {
        return;
      }

      const nextRawX = drag.startOffsetX + (event.clientX - drag.startClientX);
      const nextRawY = drag.startOffsetY + (event.clientY - drag.startClientY);
      const minX = SIDEBAR_DRAG_MARGIN - drag.baseLeft;
      const maxX = window.innerWidth - drag.width - SIDEBAR_DRAG_MARGIN - drag.baseLeft;
      const minY = SIDEBAR_DRAG_MARGIN - drag.baseTop;
      const maxY = window.innerHeight - drag.height - SIDEBAR_DRAG_MARGIN - drag.baseTop;
      const nextX = clampValue(nextRawX, minX, Math.max(minX, maxX));
      const nextY = clampValue(nextRawY, minY, Math.max(minY, maxY));

      setSidebarOffset((prev) => {
        if (prev.x === nextX && prev.y === nextY) {
          return prev;
        }
        return { x: nextX, y: nextY };
      });
    };

    const stopDrag = () => {
      setIsDraggingSidebar(false);
      sidebarDragRef.current = null;
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };

    document.body.style.userSelect = "none";
    document.body.style.cursor = "grabbing";

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", stopDrag);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", stopDrag);
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };
  }, [isDraggingSidebar]);

  useEffect(() => {
    if (!isDraggingSplitter) return;
    const handleMouseMove = (event) => {
      const drag = splitterDragRef.current;
      if (!drag) return;
      const delta = event.clientX - drag.startX;
      const min = 220;
      const max = Math.round(window.innerWidth * 0.7);
      setSidebarWidth(clampValue(drag.startWidth + delta, min, max));
    };
    const stopDrag = () => {
      setIsDraggingSplitter(false);
      splitterDragRef.current = null;
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };
    document.body.style.userSelect = "none";
    document.body.style.cursor = "col-resize";
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", stopDrag);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", stopDrag);
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };
  }, [isDraggingSplitter]);

  useEffect(() => {
    if (isMobile) {
      setSidebarOffset({ x: 0, y: 0 });
      setIsDraggingSidebar(false);
      sidebarDragRef.current = null;
      return;
    }

    const clampSidebarOffsetToViewport = () => {
      const panel = sidebarPanelRef.current;
      if (!panel) {
        return;
      }
      setSidebarOffset((prev) => {
        const rect = panel.getBoundingClientRect();
        const baseLeft = rect.left - prev.x;
        const baseTop = rect.top - prev.y;
        const minX = SIDEBAR_DRAG_MARGIN - baseLeft;
        const maxX = window.innerWidth - rect.width - SIDEBAR_DRAG_MARGIN - baseLeft;
        const minY = SIDEBAR_DRAG_MARGIN - baseTop;
        const maxY = window.innerHeight - rect.height - SIDEBAR_DRAG_MARGIN - baseTop;
        const nextX = clampValue(prev.x, minX, Math.max(minX, maxX));
        const nextY = clampValue(prev.y, minY, Math.max(minY, maxY));
        if (nextX === prev.x && nextY === prev.y) {
          return prev;
        }
        return { x: nextX, y: nextY };
      });
    };

    clampSidebarOffsetToViewport();
    window.addEventListener("resize", clampSidebarOffsetToViewport);
    return () => window.removeEventListener("resize", clampSidebarOffsetToViewport);
  }, [isMobile]);

  useEffect(() => {
    if (!isDraggingGeneratorWindow) {
      return;
    }

    const handleMouseMove = (event) => {
      const drag = generatorWindowDragRef.current;
      if (!drag) {
        return;
      }

      setGeneratorWindowRect((prev) =>
        clampGeneratorWindowRect(
          {
            ...prev,
            x: event.clientX - drag.offsetX,
            y: event.clientY - drag.offsetY
          },
          false
        )
      );
    };

    const stopDrag = () => {
      setIsDraggingGeneratorWindow(false);
      generatorWindowDragRef.current = null;
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };

    document.body.style.userSelect = "none";
    document.body.style.cursor = "grabbing";

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", stopDrag);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", stopDrag);
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };
  }, [isDraggingGeneratorWindow]);

  useEffect(() => {
    const handleResize = () => {
      if (!isGeneratorWindowVisible) {
        return;
      }
      if (isMobile) {
        setGeneratorWindowRect(buildGeneratorWindowMaxRect(true));
        return;
      }
      if (generatorWindowMaximized) {
        setGeneratorWindowRect(buildGeneratorWindowMaxRect(false));
        return;
      }
      setGeneratorWindowRect((prev) => clampGeneratorWindowRect(prev, false));
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [isGeneratorWindowVisible, generatorWindowMaximized, isMobile]);

  useEffect(() => {
    if (!isGeneratorWindowVisible) {
      return;
    }

    if (isMobile) {
      setGeneratorWindowMaximized(true);
      setGeneratorWindowMinimized(false);
      setGeneratorWindowRect(buildGeneratorWindowMaxRect(true));
      return;
    }

    if (generatorWindowMaximized && !generatorWindowRestoreRef.current) {
      setGeneratorWindowMaximized(false);
      setGeneratorWindowRect(clampGeneratorWindowRect(buildGeneratorWindowDefaultRect(), false));
      return;
    }

    if (!generatorWindowMaximized) {
      setGeneratorWindowRect((prev) => clampGeneratorWindowRect(prev, false));
    }
  }, [isMobile, isGeneratorWindowVisible, generatorWindowMaximized]);

  useEffect(() => {
    if (!isDraggingSettingsWindow) {
      return;
    }

    const handleMouseMove = (event) => {
      const drag = settingsWindowDragRef.current;
      if (!drag) {
        return;
      }

      setSettingsWindowRect((prev) =>
        clampSettingsWindowRect(
          {
            ...prev,
            x: event.clientX - drag.offsetX,
            y: event.clientY - drag.offsetY
          },
          false
        )
      );
    };

    const stopDrag = () => {
      setIsDraggingSettingsWindow(false);
      settingsWindowDragRef.current = null;
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };

    document.body.style.userSelect = "none";
    document.body.style.cursor = "grabbing";

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", stopDrag);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", stopDrag);
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };
  }, [isDraggingSettingsWindow]);

  useEffect(() => {
    const handleResize = () => {
      if (!showGeneratorHotkeys) {
        return;
      }
      if (isMobile) {
        setSettingsWindowRect(buildSettingsWindowMaxRect(true));
        return;
      }
      if (settingsWindowMaximized) {
        setSettingsWindowRect(buildSettingsWindowMaxRect(false));
        return;
      }
      setSettingsWindowRect((prev) => clampSettingsWindowRect(prev, false));
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [showGeneratorHotkeys, settingsWindowMaximized, isMobile]);

  useEffect(() => {
    if (!showGeneratorHotkeys) {
      return;
    }

    if (isMobile) {
      setSettingsWindowMaximized(true);
      setSettingsWindowMinimized(false);
      setSettingsWindowRect(buildSettingsWindowMaxRect(true));
      return;
    }

    if (settingsWindowMaximized && !settingsWindowRestoreRef.current) {
      setSettingsWindowMaximized(false);
      setSettingsWindowRect(clampSettingsWindowRect(buildSettingsWindowDefaultRect(), false));
      return;
    }

    if (!settingsWindowMaximized) {
      setSettingsWindowRect((prev) => clampSettingsWindowRect(prev, false));
    }
  }, [isMobile, showGeneratorHotkeys, settingsWindowMaximized]);

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

  const importAccounts = () => {
    const validation = validateImportAccountsText(importText);
    if (!validation.ok) {
      const lineText = validation.lineNumber == null ? "" : ` (строка ${validation.lineNumber})`;
      applyStatus(`Ошибка формата${lineText}: ${validation.reason}`);
      return;
    }

    withBusy(async () => {
      const result = await accountsApi.importAccounts(token, importText);
      await loadAccounts();
      applyStatus(
        `Импорт: добавлено ${result.added}, дубли ${result.duplicates}, пропущено ${result.skipped}`
      );
      setImportText("");
      closeImportWindow();
    }, "Импорт аккаунтов...");
  };

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
      const statusLabel = STATUS_LABELS[status] || status;
      applyStatus(`Статус изменен: ${statusLabel}`);
    }, "Обновление статуса...");
  };

  const deleteSelectedAccount = () => {
    if (!selectedAccount) {
      return;
    }

    withBusy(async () => {
      await accountsApi.remove(token, selectedAccount.id);
      await loadAccounts();
      applyStatus("Аккаунт удален");
    }, "Удаление аккаунта...");
  };

  const deleteMailboxByAccount = (account) => {
    if (!account) {
      return;
    }

    withBusy(async () => {
      // Remove account from the user's list for any mailbox domain.
      await accountsApi.remove(token, account.id);
      setWindowSelectedAccountIds((prev) => prev.filter((id) => id !== account.id));
      await loadAccounts();
      applyStatus(`Почта убрана из списка: ${account.email}`);
    }, "Удаление почты...");
  };

  const deleteSelectedMailbox = () => {
    deleteMailboxByAccount(selectedAccount);
  };

  const deleteAllAccounts = () => {
    if (!accounts.length) {
      applyStatus("Нет записей для удаления");
      return;
    }

    const total = accounts.length;

    withBusy(async () => {
      let deleted = 0;
      let failed = 0;
      const ids = accounts.map((item) => item.id);

      for (const id of ids) {
        try {
          await accountsApi.remove(token, id);
          deleted += 1;
        } catch {
          failed += 1;
        }
      }

      setWindowSelectedAccountIds([]);
      accountsSelectionAnchorRef.current = null;
      await loadAccounts();

      if (failed > 0) {
        applyStatus(`Удалено ${deleted} из ${total}. Ошибок: ${failed}`);
      } else {
        applyStatus(`Удалены все записи: ${deleted}`);
      }
    }, "Удаление всех записей...");
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
    setSettingsWindowMinimized(false);
    if (isMobile) {
      setSettingsWindowMaximized(true);
      setSettingsWindowRect(buildSettingsWindowMaxRect(true));
    } else {
      setSettingsWindowRect((prev) => clampSettingsWindowRect(prev, false));
    }
    setShowGeneratorHotkeys(true);
  };

  const closeGeneratorHotkeys = () => {
    setRecordingHotkeyKey(null);
    setShowGeneratorHotkeys(false);
    setSettingsWindowMinimized(false);
    setSettingsWindowMaximized(false);
    setIsDraggingSettingsWindow(false);
    settingsWindowDragRef.current = null;
    settingsWindowRestoreRef.current = null;
  };

  const toggleSettingsWindowMinimize = () => {
    setSettingsWindowMinimized((prev) => !prev);
  };

  const toggleSettingsWindowMaximize = () => {
    if (isMobile || !showGeneratorHotkeys) {
      return;
    }

    if (settingsWindowMaximized) {
      setSettingsWindowMaximized(false);
      const restoreRect = settingsWindowRestoreRef.current || buildSettingsWindowDefaultRect();
      setSettingsWindowRect(clampSettingsWindowRect(restoreRect, false));
      settingsWindowRestoreRef.current = null;
      return;
    }

    settingsWindowRestoreRef.current = settingsWindowRect;
    setSettingsWindowMinimized(false);
    setSettingsWindowMaximized(true);
    setSettingsWindowRect(buildSettingsWindowMaxRect(false));
  };

  const startSettingsWindowDrag = (event) => {
    if (isMobile || settingsWindowMaximized || settingsWindowMinimized || !showGeneratorHotkeys) {
      return;
    }
    if (event.button !== 0) {
      return;
    }

    event.preventDefault();
    settingsWindowDragRef.current = {
      offsetX: event.clientX - settingsWindowRect.x,
      offsetY: event.clientY - settingsWindowRect.y
    };
    setIsDraggingSettingsWindow(true);
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
    setSettingsWindowMinimized(false);
    setSettingsWindowMaximized(false);
    setIsDraggingSettingsWindow(false);
    settingsWindowDragRef.current = null;
    settingsWindowRestoreRef.current = null;
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
    setGeneratorWindowMinimized(false);
    if (isMobile) {
      setGeneratorWindowMaximized(true);
      setGeneratorWindowRect(buildGeneratorWindowMaxRect(true));
    } else {
      setGeneratorWindowRect((prev) => clampGeneratorWindowRect(prev, false));
    }
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
    setGeneratorWindowMinimized(false);
    if (isMobile) {
      setGeneratorWindowMaximized(true);
      setGeneratorWindowRect(buildGeneratorWindowMaxRect(true));
    } else {
      setGeneratorWindowRect((prev) => clampGeneratorWindowRect(prev, false));
    }
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
      value = formatAccountCredentials(selectedAccount);
    }

    await copyText(value);
    applyStatus(
      field === "full" ? "Скопировано: почта:пароль;2пароль" : `Скопировано: ${field}`
    );
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

  const accountsPanel = (
    <>
      <button type="button" className="primary-btn create-btn" onClick={createMailTm} disabled={busy}>
        + Создать аккаунт
      </button>

      <section className="side-section accounts-section">
        <div className="section-caption">АККАУНТЫ</div>

        <div className="mini-controls">
          <button type="button" onClick={refreshAccounts} disabled={busy} title="Обновить список">
            {I.refresh()}
          </button>
          <button
            type="button"
            className={showImportWindow ? "active" : ""}
            onClick={() => {
              if (showImportWindow) {
                closeImportWindow();
              } else {
                openImportWindow();
              }
            }}
            disabled={busy}
            title="Импорт из файла"
          >
            {I.fileImport()}
          </button>
          <button type="button" onClick={exportAccountsForExcel} disabled={busy} title="Экспорт в Excel">
            {I.table()}
          </button>
          <button type="button" onClick={openAccountsDataWindow} disabled={busy} title="Окно данных">
            {I.window()}
          </button>
          <button type="button" className="danger-btn" onClick={banCheckAll} disabled={busy} title="Проверить баны">
            {I.shieldX()}
          </button>
        </div>

        <div className="account-list">
          {accounts.map((account) => (
            <button
              key={account.id}
              type="button"
              className={`account-item ${statusClass(account.status)} ${
                account.id === selectedAccountId ? "active" : ""
              }`}
              onClick={() => {
                setSelectedAccountId(account.id);
                if (isMobile) {
                  setMobileTab("mail");
                }
              }}
            >
              <span className="account-item-main">
                <span className="account-email">{account.email}</span>
                <small>{STATUS_LABELS[account.status] || account.status}</small>
              </span>
              <span
                className="account-mail-delete"
                title={`Удалить почту ${account.email}`}
                onMouseDown={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                }}
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  deleteMailboxByAccount(account);
                }}
              >
                ×
              </span>
            </button>
          ))}

          {!accounts.length ? <div className="empty-list">Аккаунтов пока нет</div> : null}
        </div>
      </section>

      <section className="side-section">
        <div className="section-caption">ДЕЙСТВИЯ</div>

        <div className="actions-grid">
          <button type="button" onClick={() => copyAccountField("email")} disabled={!selectedAccount} title="Копировать Email">
            {I.at()}
          </button>
          <button type="button" onClick={() => copyAccountField("openai")} disabled={!selectedAccount} title="Копировать OpenAI пароль">
            {I.key()}
          </button>
          <button type="button" onClick={() => copyAccountField("mail")} disabled={!selectedAccount} title="Копировать пароль почты">
            {I.lock()}
          </button>
          <button type="button" onClick={() => copyAccountField("full")} disabled={!selectedAccount} title="Копировать всё">
            {I.copy()}
          </button>
        </div>

      </section>
    </>
  );

  const mailPanel = (
    <>
      <header className="top-toolbar">
        <div className="top-toolbar-title-row">
          {isMobile ? (
            <button
              type="button"
              className="mobile-back-btn"
              onClick={() => setMobileTab("accounts")}
              aria-label="Назад к аккаунтам"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M15 18l-6-6 6-6" />
              </svg>
            </button>
          ) : null}
          <h2>{selectedAccount ? selectedAccount.email : "Выберите аккаунт"}</h2>
        </div>

        <div className="toolbar-controls">
          <button
            type="button"
            className="primary-btn"
            onClick={manualRefresh}
            disabled={!selectedAccount || busy}
            title="Обновить почту"
          >
            {I.refresh()}
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

      <div className="mail-panels" ref={isMobile ? null : mailPanelsRef}>
        <section
          className={`panel-card inbox-card ${isInboxResizeReady ? "resize-ready" : ""} ${
            isResizingMailPanels ? "is-resizing" : ""
          }`}
          style={!isMobile ? { height: `${Math.round(mailInboxHeight)}px` } : undefined}
          onMouseDown={!isMobile ? startMailPanelsResize : undefined}
          onMouseMove={!isMobile ? handleInboxResizeHover : undefined}
          onMouseLeave={!isMobile ? clearInboxResizeHover : undefined}
        >
          {isMobile ? (
            <div className="mobile-message-list">
              {messages.map((message) => (
                <button
                  key={message.id}
                  type="button"
                  className={`mobile-message-item ${messageDetail?.id === message.id ? "active" : ""}`}
                  onClick={() => openMessage(message)}
                >
                  <div className="mobile-msg-sender">{message.sender}</div>
                  <div className="mobile-msg-subject">{message.subject}</div>
                  <div className="mobile-msg-time">{toLocalDateTime(message.created_at)}</div>
                </button>
              ))}
              {!messages.length ? <div className="empty-list">Писем пока нет</div> : null}
            </div>
          ) : (
            <>
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
            </>
          )}
        </section>

        <section className="panel-card viewer-card">
          <div className="viewer-head">
            <h3>Содержание письма</h3>
            {messageDetail?.code ? (
              <button type="button" onClick={copyCode} title="Копировать код">
                {I.clipboard()} {messageDetail.code}
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
                {messageDetail.html ? (
                  <HtmlEmailViewer html={messageDetail.html} />
                ) : (
                  <pre>{messageDetail.text}</pre>
                )}
              </>
            ) : (
              <p className="placeholder-text">Выберите письмо, чтобы увидеть содержимое.</p>
            )}
          </div>
        </section>
      </div>
    </>
  );

  const toolsPanel = (
    <>
      <section className="mobile-tools-section">
        <div className="section-caption">ГЕНЕРАТОРЫ</div>

        <div className="mobile-tools-grid">
          <button
            type="button"
            className={`mobile-tool-card ${showSkPanel ? "active" : ""}`}
            onClick={openSkGenerator}
          >
            <span className="mobile-tool-icon">SK</span>
            <span className="mobile-tool-label">South Korea</span>
          </button>
          <button
            type="button"
            className={`mobile-tool-card ${showInPanel ? "active" : ""}`}
            onClick={openInGenerator}
          >
            <span className="mobile-tool-icon">IN</span>
            <span className="mobile-tool-label">India</span>
          </button>
          <button type="button" className="mobile-tool-card" onClick={openGeneratorHotkeys}>
            <span className="mobile-tool-icon">HK</span>
            <span className="mobile-tool-label">Настройки</span>
          </button>
          <button type="button" className="mobile-tool-card" onClick={handleMinesweeper}>
            <span className="mobile-tool-icon">MS</span>
            <span className="mobile-tool-label">Сапёр</span>
          </button>
        </div>
      </section>

      <section className="mobile-tools-section">
        <div className="section-caption">СЛУЧАЙНЫЕ ДАННЫЕ</div>

        <div className="mobile-person-card">
          <div className="mobile-person-row">
            <span className="mobile-person-label">Имя</span>
            <code className="mobile-person-value">{randomPerson.name || "-"}</code>
            <button type="button" onClick={() => copyGeneratorField("name", randomPerson.name)} title="Копировать">
              {I.clipboard()}
            </button>
          </div>
          <div className="mobile-person-row">
            <span className="mobile-person-label">Дата</span>
            <code className="mobile-person-value">{randomPerson.birthdate || "-"}</code>
            <button type="button" onClick={() => copyGeneratorField("birthdate", randomPerson.birthdate)} title="Копировать">
              {I.clipboard()}
            </button>
          </div>
          <button type="button" className="primary-btn" onClick={regenerateRandomPerson} disabled={busy} title="Новые данные">
            {I.dice()}
          </button>
        </div>
      </section>
    </>
  );

  const accountsDataWindowStyle = showAccountsDataWindow
    ? {
        left: `${accountsWindowRect.x}px`,
        top: `${accountsWindowRect.y}px`,
        width: `${accountsWindowRect.width}px`,
        height: `${accountsWindowRect.height}px`
      }
    : null;

  const generatorWindowStyle = isGeneratorWindowVisible
    ? {
        left: `${generatorWindowRect.x}px`,
        top: `${generatorWindowRect.y}px`,
        width: `${generatorWindowRect.width}px`,
        height: `${generatorWindowRect.height}px`
      }
    : null;

  const hotkeysWindowStyle = showGeneratorHotkeys
    ? {
        left: `${settingsWindowRect.x}px`,
        top: `${settingsWindowRect.y}px`,
        width: `${settingsWindowRect.width}px`,
        height: `${settingsWindowRect.height}px`
      }
    : null;

  const importWindowStyle = showImportWindow
    ? {
        left: `${importWindowRect.x}px`,
        top: `${importWindowRect.y}px`,
        width: `${importWindowRect.width}px`,
        height: `${importWindowRect.height}px`
      }
    : null;

  const accountsDataWindow = showAccountsDataWindow ? (
    <div className="accounts-data-window-layer">
      <section
        ref={accountsWindowElementRef}
        className={`accounts-data-window ${accountsWindowMinimized ? "is-minimized" : ""} ${
          accountsWindowMaximized ? "is-maximized" : ""
        }`}
        style={accountsDataWindowStyle}
      >
        <header
          className={`accounts-data-window-header ${isDraggingAccountsWindow ? "dragging" : ""}`}
          onMouseDown={startAccountsWindowDrag}
        >
          <div className="accounts-data-window-title">
            <strong>Данные аккаунтов</strong>
            <span>
              Всего: {accounts.length} • Выделено: {selectedAccountsInWindow.length}
            </span>
          </div>
          <div className="accounts-data-window-actions" onMouseDown={(event) => event.stopPropagation()}>
            <button
              type="button"
              className="accounts-window-action refresh"
              onClick={refreshAccounts}
              disabled={busy}
              title="Обновить список"
            >
              ↻
            </button>
            <button
              type="button"
              className="accounts-window-action"
              onClick={toggleAccountsWindowMinimize}
              title={accountsWindowMinimized ? "Развернуть" : "Свернуть"}
            >
              {accountsWindowMinimized ? "▢" : "—"}
            </button>
            {!isMobile ? (
              <button
                type="button"
                className="accounts-window-action"
                onClick={toggleAccountsWindowMaximize}
                title={accountsWindowMaximized ? "Восстановить" : "Развернуть"}
              >
                {accountsWindowMaximized ? "❐" : "□"}
              </button>
            ) : null}
            <button
              type="button"
              className="accounts-window-action close"
              onClick={closeAccountsDataWindow}
              title="Закрыть"
            >
              ×
            </button>
          </div>
        </header>

        {!accountsWindowMinimized ? (
          <div className="accounts-data-window-body">
            <div className="accounts-data-copy-row">
              <textarea
                value={selectedAccountCredentials}
                readOnly
                placeholder="почта:пароль;2пароль"
                onFocus={(event) => event.target.select()}
                rows={Math.min(Math.max(selectedAccountsInWindow.length || 1, 1), 4)}
              />
              <button
                type="button"
                onClick={copySelectedAccountCredentials}
                disabled={!selectedAccountsInWindow.length}
                title="Скопировать выбранные строки"
              >
                {I.clipboard()}
              </button>
            </div>
            <div className="accounts-data-select-hint">
              Выделение: Shift — диапазон, Ctrl/Cmd — добавить или снять выбор
            </div>
            <table className="accounts-data-table">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>OpenAI</th>
                  <th>Почта</th>
                  <th>Статус</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((account, index) => (
                  <tr
                    key={account.id}
                    className={`${statusClass(account.status)} ${
                      windowSelectedSet.has(account.id) ? "active" : ""
                    }`}
                    onClick={(event) => selectAccountFromDataWindow(event, account.id, index)}
                    onMouseDown={(event) => {
                      if (event.shiftKey || event.ctrlKey || event.metaKey) {
                        event.preventDefault();
                      }
                    }}
                  >
                    <td title={account.email}>{account.email}</td>
                    <td title={account.password_openai}>{account.password_openai}</td>
                    <td title={account.password_mail}>{account.password_mail}</td>
                    <td>{STATUS_LABELS[account.status] || account.status}</td>
                  </tr>
                ))}
                {!accounts.length ? (
                  <tr>
                    <td colSpan={4} className="accounts-data-empty">
                      Аккаунтов пока нет
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </div>
  ) : null;

  const importAccountsWindow = showImportWindow ? (
    <div className="accounts-data-window-layer">
      <section
        className={`accounts-data-window import-accounts-window ${importWindowMinimized ? "is-minimized" : ""} ${
          importWindowMaximized ? "is-maximized" : ""
        }`}
        style={importWindowStyle}
      >
        <header
          className={`accounts-data-window-header ${isDraggingImportWindow ? "dragging" : ""}`}
          onMouseDown={startImportWindowDrag}
        >
          <div className="accounts-data-window-title">
            <strong>Импорт аккаунтов</strong>
            <span>Вставьте аккаунты: email / pass;pass / status</span>
          </div>
          <div className="accounts-data-window-actions" onMouseDown={(event) => event.stopPropagation()}>
            <button
              type="button"
              className="accounts-window-action refresh"
              onClick={importAccounts}
              disabled={busy || !importText.trim()}
              title="Импортировать"
            >
              ↥
            </button>
            <button
              type="button"
              className="accounts-window-action"
              onClick={toggleImportWindowMinimize}
              title={importWindowMinimized ? "Развернуть" : "Свернуть"}
            >
              {importWindowMinimized ? "▢" : "—"}
            </button>
            {!isMobile ? (
              <button
                type="button"
                className="accounts-window-action"
                onClick={toggleImportWindowMaximize}
                title={importWindowMaximized ? "Восстановить" : "Развернуть"}
              >
                {importWindowMaximized ? "❐" : "□"}
              </button>
            ) : null}
            <button
              type="button"
              className="accounts-window-action close"
              onClick={closeImportWindow}
              title="Закрыть"
            >
              ×
            </button>
          </div>
        </header>

        {!importWindowMinimized ? (
          <div className="accounts-data-window-body import-accounts-window-body">
            <textarea
              className="import-textarea import-window-textarea"
              placeholder="Вставьте аккаунты: email / pass;pass / status"
              value={importText}
              onChange={(event) => setImportText(event.target.value)}
            />

            <div className="import-actions import-window-actions">
              <button type="button" className="primary-btn" onClick={importAccounts} disabled={busy || !importText.trim()} title="Импортировать">
                {I.upload()}
              </button>
              <button type="button" onClick={closeImportWindow} disabled={busy} title="Закрыть">
                {I.close()}
              </button>
            </div>
          </div>
        ) : (
          <div className="hotkeys-minimized-info">Окно свернуто</div>
        )}
      </section>
    </div>
  ) : null;

  if (isMobile) {
    return (
      <div className="dashboard-shell theme-dark mobile-shell">
        <ParallaxDotsBackground />

        <header className="mobile-header">
          <h1 className="brand-title">
            <span>Mail.</span>tm
          </h1>
          <div className="mobile-header-actions">
            <span className="mobile-user-badge">{user.username}</span>
            <button type="button" className="icon-btn" title="Выйти" onClick={onLogout}>
              {I.logout()}
            </button>
          </div>
        </header>

        <div className="mobile-content">
          {mobileTab === "accounts" ? accountsPanel : null}
          {mobileTab === "mail" ? mailPanel : null}
          {mobileTab === "tools" ? toolsPanel : null}
        </div>

        <footer className="mobile-status-bar">{statusMessage}</footer>

        <nav className="mobile-bottom-nav">
          <button
            type="button"
            className={mobileTab === "accounts" ? "active" : ""}
            onClick={() => setMobileTab("accounts")}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
            <span>Аккаунты</span>
          </button>
          <button
            type="button"
            className={mobileTab === "mail" ? "active" : ""}
            onClick={() => setMobileTab("mail")}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="4" width="20" height="16" rx="2" />
              <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
            </svg>
            <span>Почта</span>
          </button>
          <button
            type="button"
            className={mobileTab === "tools" ? "active" : ""}
            onClick={() => setMobileTab("tools")}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
            </svg>
            <span>Инструм.</span>
          </button>
        </nav>

        {accountsDataWindow}
        {importAccountsWindow}

        {showSkPanel ? (
          <GeneratorPanel
            title="South Korea Data Generator"
            data={skData}
            busy={busy}
            activeAction={skActiveAction}
            hotkeys={generatorHotkeys}
            windowStyle={generatorWindowStyle}
            minimized={generatorWindowMinimized}
            maximized={generatorWindowMaximized}
            isMobile={isMobile}
            isDragging={isDraggingGeneratorWindow}
            onClose={closeSkGenerator}
            onHeaderMouseDown={startGeneratorWindowDrag}
            onToggleMinimize={toggleGeneratorWindowMinimize}
            onToggleMaximize={toggleGeneratorWindowMaximize}
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
            windowStyle={generatorWindowStyle}
            minimized={generatorWindowMinimized}
            maximized={generatorWindowMaximized}
            isMobile={isMobile}
            isDragging={isDraggingGeneratorWindow}
            onClose={closeInGenerator}
            onHeaderMouseDown={startGeneratorWindowDrag}
            onToggleMinimize={toggleGeneratorWindowMinimize}
            onToggleMaximize={toggleGeneratorWindowMaximize}
            onGenerate={regenerateIn}
            onSettings={openGeneratorHotkeys}
            onCopy={(action) => copyGeneratorAction("in", action)}
          />
        ) : null}

        {showGeneratorHotkeys ? (
          <HotkeySettingsModal
            windowStyle={hotkeysWindowStyle}
            minimized={settingsWindowMinimized}
            maximized={settingsWindowMaximized}
            isMobile={isMobile}
            isDragging={isDraggingSettingsWindow}
            busy={busy}
            selectedAccount={selectedAccount}
            accountsCount={accounts.length}
            draftHotkeys={draftHotkeys}
            recordingHotkeyKey={recordingHotkeyKey}
            onClose={closeGeneratorHotkeys}
            onHeaderMouseDown={startSettingsWindowDrag}
            onToggleMinimize={toggleSettingsWindowMinimize}
            onToggleMaximize={toggleSettingsWindowMaximize}
            onSave={saveGeneratorHotkeys}
            onReset={resetGeneratorHotkeys}
            onStartRecord={toggleHotkeyRecord}
            onClearHotkey={clearDraftHotkey}
            onDeleteAccount={deleteSelectedAccount}
            onDeleteMailbox={deleteSelectedMailbox}
            onDeleteAllAccounts={deleteAllAccounts}
          />
        ) : null}
      </div>
    );
  }

  return (
    <div className="dashboard-shell theme-dark">
      <ParallaxDotsBackground />
      <div
        className="dashboard-window"
        style={!isMobile ? { gridTemplateColumns: `${sidebarWidth}px auto 1fr` } : undefined}
      >
        <aside
          ref={sidebarPanelRef}
          className={`left-panel ${!isMobile ? "movable" : ""} ${isDraggingSidebar ? "is-dragging" : ""} ${
            sidebarOffset.x || sidebarOffset.y ? "is-floating" : ""
          }`}
          style={
            !isMobile
              ? { transform: `translate(${Math.round(sidebarOffset.x)}px, ${Math.round(sidebarOffset.y)}px)` }
              : undefined
          }
        >
          <div
            className={`brand-strip ${!isMobile ? "drag-handle" : ""} ${isDraggingSidebar ? "dragging" : ""}`}
            onMouseDown={!isMobile ? startSidebarDrag : undefined}
          >
            <h1 className="brand-title">
              <span>Mail.</span>tm
            </h1>
            <div className="brand-actions">
              <button type="button" className="icon-btn" title="Выйти" onClick={onLogout}>
                {I.logout()}
              </button>
            </div>
          </div>
          <div className="user-caption">{user.username}</div>

          {accountsPanel}

          <section className="side-section">
            <div className="section-caption">ДЕЙСТВИЯ</div>

            <div className="actions-grid">
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
              <button type="button" onClick={handleMinesweeper} title="Сапёр">
                {I.bomb()}
              </button>
              <button type="button" onClick={openGeneratorHotkeys} title="Настройки">
                {I.gear()}
              </button>
            </div>
          </section>

          <section className={`side-section generator-section ${showSidebarGenerator ? "" : "collapsed"}`}>
            <div className="section-header">
              <div className="section-caption">ГЕНЕРАТОР</div>
              <button type="button" className="section-toggle-btn" onClick={toggleSidebarGenerator} title={showSidebarGenerator ? "Скрыть" : "Показать"}>
                {showSidebarGenerator ? I.chevronUp() : I.chevronDown()}
              </button>
            </div>

            {showSidebarGenerator ? (
              <>
                <div className="generator-row">
                  <span>Name</span>
                  <code>{randomPerson.name || "-"}</code>
                  <button type="button" onClick={() => copyGeneratorField("name", randomPerson.name)} title="Копировать">
                    {I.clipboard()}
                  </button>
                </div>

                <div className="generator-row">
                  <span>Дата</span>
                  <code>{randomPerson.birthdate || "-"}</code>
                  <button type="button" onClick={() => copyGeneratorField("birthdate", randomPerson.birthdate)} title="Копировать">
                    {I.clipboard()}
                  </button>
                </div>

                <button type="button" className="primary-btn" onClick={regenerateRandomPerson} disabled={busy} title="Новые данные">
                  {I.dice()}
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

        {!isMobile ? (
          <div
            className={`panel-splitter ${isDraggingSplitter ? "is-dragging" : ""}`}
            onMouseDown={startSplitterDrag}
          />
        ) : null}

        <main className="right-panel">
          {mailPanel}
        </main>
      </div>

      {accountsDataWindow}
      {importAccountsWindow}

      {showSkPanel ? (
        <GeneratorPanel
          title="South Korea Data Generator"
          data={skData}
          busy={busy}
          activeAction={skActiveAction}
          hotkeys={generatorHotkeys}
          windowStyle={generatorWindowStyle}
          minimized={generatorWindowMinimized}
          maximized={generatorWindowMaximized}
          isMobile={isMobile}
          isDragging={isDraggingGeneratorWindow}
          onClose={closeSkGenerator}
          onHeaderMouseDown={startGeneratorWindowDrag}
          onToggleMinimize={toggleGeneratorWindowMinimize}
          onToggleMaximize={toggleGeneratorWindowMaximize}
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
          windowStyle={generatorWindowStyle}
          minimized={generatorWindowMinimized}
          maximized={generatorWindowMaximized}
          isMobile={isMobile}
          isDragging={isDraggingGeneratorWindow}
          onClose={closeInGenerator}
          onHeaderMouseDown={startGeneratorWindowDrag}
          onToggleMinimize={toggleGeneratorWindowMinimize}
          onToggleMaximize={toggleGeneratorWindowMaximize}
          onGenerate={regenerateIn}
          onSettings={openGeneratorHotkeys}
          onCopy={(action) => copyGeneratorAction("in", action)}
        />
      ) : null}

      {showGeneratorHotkeys ? (
        <HotkeySettingsModal
          windowStyle={hotkeysWindowStyle}
          minimized={settingsWindowMinimized}
          maximized={settingsWindowMaximized}
          isMobile={isMobile}
          isDragging={isDraggingSettingsWindow}
          busy={busy}
          selectedAccount={selectedAccount}
          accountsCount={accounts.length}
          draftHotkeys={draftHotkeys}
          recordingHotkeyKey={recordingHotkeyKey}
          onClose={closeGeneratorHotkeys}
          onHeaderMouseDown={startSettingsWindowDrag}
          onToggleMinimize={toggleSettingsWindowMinimize}
          onToggleMaximize={toggleSettingsWindowMaximize}
          onSave={saveGeneratorHotkeys}
          onReset={resetGeneratorHotkeys}
          onStartRecord={toggleHotkeyRecord}
          onClearHotkey={clearDraftHotkey}
          onDeleteAccount={deleteSelectedAccount}
          onDeleteMailbox={deleteSelectedMailbox}
          onDeleteAllAccounts={deleteAllAccounts}
        />
      ) : null}

      <footer className="status-bar">{statusMessage}</footer>
    </div>
  );
}
