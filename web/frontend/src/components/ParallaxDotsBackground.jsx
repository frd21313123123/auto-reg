import { useEffect, useRef } from "react";

export default function ParallaxDotsBackground() {
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
