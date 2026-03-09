import { useEffect, useMemo, useState } from "react";

import { toolsApi } from "../api";

const GENERATOR_META = {
  in: {
    title: "India Data Generator",
    subtitle: "Отдельное окно генератора данных для Индии",
    load: (token) => toolsApi.generatorIn(token)
  },
  sk: {
    title: "South Korea Data Generator",
    subtitle: "Отдельное окно генератора данных для Южной Кореи",
    load: (token) => toolsApi.generatorSk(token)
  }
};

const FIELD_ORDER = ["card", "exp", "cvv", "name", "city", "street", "postcode", "address_en"];

const FIELD_LABELS = {
  card: "Номер карты",
  exp: "Expiration Date",
  cvv: "CVV",
  name: "Имя (Name)",
  city: "Город (City)",
  street: "Улица (Street)",
  postcode: "Индекс (Postcode)",
  address_en: "Address (English)"
};

async function copyText(value) {
  if (!value) {
    return;
  }

  await navigator.clipboard.writeText(String(value));
}

export default function GeneratorPopup({ token, kind, onLogout }) {
  const meta = useMemo(() => GENERATOR_META[kind] || null, [kind]);
  const [data, setData] = useState({});
  const [busy, setBusy] = useState(false);
  const [statusText, setStatusText] = useState("Готов к генерации");

  const loadData = async () => {
    if (!meta) {
      return;
    }

    try {
      setBusy(true);
      const nextData = await meta.load(token);
      setData(nextData);
      setStatusText("Данные обновлены");
    } catch (error) {
      setStatusText(error.message || "Не удалось загрузить данные");
    } finally {
      setBusy(false);
    }
  };

  const handleCopy = async (value, label) => {
    try {
      await copyText(value);
      setStatusText(`Скопировано: ${label}`);
    } catch (error) {
      setStatusText(error.message || "Не удалось скопировать");
    }
  };

  useEffect(() => {
    if (!meta) {
      document.title = "Generator";
      return;
    }

    document.title = meta.title;
    loadData();
  }, [meta, token]);

  if (!meta) {
    return (
      <div className="generator-popup-root">
        <div className="generator-popup-card">
          <h1>Неизвестное окно генератора</h1>
          <p>Параметр popup должен быть `in` или `sk`.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`generator-popup-root generator-popup-root-${kind}`}>
      <div className="generator-popup-card">
        <div className="generator-popup-topbar">
          <div>
            <p className="offline-eyebrow">Generator Window</p>
            <h1>{meta.title}</h1>
            <p className="generator-popup-subtitle">{meta.subtitle}</p>
          </div>
          <div className="generator-popup-actions">
            <button type="button" onClick={onLogout}>
              Выйти
            </button>
            <button type="button" className="ghost-button" onClick={() => window.close()}>
              Закрыть
            </button>
          </div>
        </div>

        <div className="generator-popup-list">
          {FIELD_ORDER.filter((key) => key in data).map((key) => (
            <div key={key} className="generator-popup-row">
              <label>{FIELD_LABELS[key] || key}</label>
              <code>{data[key]}</code>
              <button type="button" onClick={() => handleCopy(data[key], FIELD_LABELS[key] || key)}>
                Copy
              </button>
            </div>
          ))}
        </div>

        <div className="generator-popup-footer">
          <button type="button" className="primary-inline" onClick={loadData} disabled={busy}>
            {busy ? "Генерация..." : "Сгенерировать"}
          </button>
          <span>{statusText}</span>
        </div>
      </div>
    </div>
  );
}
