import { useEffect, useState } from "react";

import { authApi } from "./api";
import AuthView from "./components/AuthView";
import Dashboard from "./components/Dashboard";
import LauncherView from "./components/LauncherView";
import WaveView from "./components/WaveView";

const TOKEN_KEY = "auto_reg_web_token";
const PROJECT_KEY = "auto_reg_web_project";

function LiquidGlassSvgDefs() {
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      width="0"
      height="0"
      style={{ position: "absolute", pointerEvents: "none" }}
    >
      <defs>
        <filter
          id="liquidGlass"
          x="-20%"
          y="-20%"
          width="140%"
          height="140%"
          colorInterpolationFilters="sRGB"
        >
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.012"
            numOctaves="1"
            seed="2"
            result="noise"
          />
          <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="blur" />
          <feDisplacementMap
            in="blur"
            in2="noise"
            scale="18"
            xChannelSelector="R"
            yChannelSelector="G"
            result="refract"
          />
          <feColorMatrix in="refract" type="saturate" values="1.15" result="out" />
          <feComposite in="out" in2="SourceGraphic" operator="over" />
        </filter>
      </defs>
    </svg>
  );
}

export default function App() {
  const [project, setProject] = useState(() => sessionStorage.getItem(PROJECT_KEY));
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

  useEffect(() => {
    const root = document.documentElement;
    const supportsApi = typeof window.CSS?.supports === "function";
    const hasBackdrop = supportsApi
      ? window.CSS.supports("(-webkit-backdrop-filter: blur(1px))") ||
        window.CSS.supports("(backdrop-filter: blur(1px))")
      : false;
    const hasLiquid = supportsApi ? window.CSS.supports("(backdrop-filter: url('#liquidGlass'))") : false;

    root.classList.toggle("has-backdrop", hasBackdrop);
    root.classList.toggle("has-liquid", hasLiquid);

    return () => {
      root.classList.remove("has-backdrop");
      root.classList.remove("has-liquid");
    };
  }, []);

  const handleSelectAutoReg = () => {
    sessionStorage.setItem(PROJECT_KEY, "autoreg");
    setProject("autoreg");
  };

  const handleSelectWave = () => {
    sessionStorage.setItem(PROJECT_KEY, "wave");
    setProject("wave");
  };

  const handleBackToLauncher = () => {
    sessionStorage.removeItem(PROJECT_KEY);
    setProject(null);
  };

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

  let content;

  if (!project) {
    content = <LauncherView onSelectAutoReg={handleSelectAutoReg} onSelectWave={handleSelectWave} />;
  } else if (project === "wave") {
    content = <WaveView onBack={handleBackToLauncher} />;
  } else if (checking) {
    content = <div className="boot-loader">Проверка сессии...</div>;
  } else if (!token || !user) {
    content = <AuthView onAuthSuccess={handleAuthSuccess} onBack={handleBackToLauncher} />;
  } else {
    content = (
      <Dashboard
        token={token}
        user={user}
        onLogout={handleLogout}
        onBack={handleBackToLauncher}
      />
    );
  }

  return (
    <>
      <LiquidGlassSvgDefs />
      {content}
    </>
  );
}
