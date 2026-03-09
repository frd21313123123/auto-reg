import { useState } from "react";

import ParallaxDotsBackground from "./ParallaxDotsBackground";

export default function LauncherView({ onSelectAutoReg, onSelectWave }) {
  const [hoveredProject, setHoveredProject] = useState(null);

  return (
    <div className="launcher-root auth-dark">
      <ParallaxDotsBackground />
      <div className="launcher-card">
        <h1 className="launcher-title">Выберите проект</h1>

        <div className="launcher-cards">
          <button
            type="button"
            className={`launcher-project-card ${hoveredProject === "autoreg" ? "hovered" : ""}`}
            onMouseEnter={() => setHoveredProject("autoreg")}
            onMouseLeave={() => setHoveredProject(null)}
            onClick={onSelectAutoReg}
          >
            <img
              src="/autoreg-icon.png"
              alt="Auto-Reg"
              className="launcher-project-icon"
            />
            <span className="launcher-project-name">Auto-Reg</span>
          </button>

          <button
            type="button"
            className={`launcher-project-card ${hoveredProject === "wave" ? "hovered" : ""}`}
            onMouseEnter={() => setHoveredProject("wave")}
            onMouseLeave={() => setHoveredProject(null)}
            onClick={onSelectWave}
          >
            <img src="/wave-icon.png" alt="Wave" className="launcher-project-icon" />
            <span className="launcher-project-name">Wave</span>
          </button>
        </div>
      </div>
    </div>
  );
}
