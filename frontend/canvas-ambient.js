/**
 * ══════════════════════════════════════════════════════════════════════════════
 * MLOps.dev — High-Performance Spatial Ambient Canvas Engine
 * Handcrafted 120 FPS Interactive Particle / Neural Constellation Canvas
 * Tier-1 Production Standard (Magic UI / HorizonX / Supahero.io Caliber)
 * ══════════════════════════════════════════════════════════════════════════════
 */

(function () {
  'use strict';

  function initAmbientCanvas(canvas) {
    if (!canvas) return;
    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return;

    let width = 0;
    let height = 0;
    let dpr = window.devicePixelRatio || 1;
    let particles = [];
    let animationFrameId = null;
    let mouse = { x: -9999, y: -9999, radius: 140, active: false };

    const PARTICLE_COUNT = Math.min(Math.floor(window.innerWidth / 18), 75);
    const MAX_DISTANCE = 130;
    const ACCENT_COLOR = 'rgba(91, 138, 240, ';
    const SECONDARY_COLOR = 'rgba(0, 255, 179, ';
    const CYAN_COLOR = 'rgba(0, 240, 255, ';

    function resize() {
      const rect = canvas.parentElement ? canvas.parentElement.getBoundingClientRect() : canvas.getBoundingClientRect();
      width = rect.width || window.innerWidth;
      height = rect.height || window.innerHeight;
      dpr = Math.min(window.devicePixelRatio || 1, 2);

      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = width + 'px';
      canvas.style.height = height + 'px';
      ctx.scale(dpr, dpr);

      createParticles();
    }

    function createParticles() {
      particles = [];
      const count = Math.min(Math.floor(width / 22), 65);
      for (let i = 0; i < count; i++) {
        particles.push({
          x: Math.random() * width,
          y: Math.random() * height,
          vx: (Math.random() - 0.5) * 0.45,
          vy: (Math.random() - 0.5) * 0.45,
          radius: Math.random() * 1.8 + 0.8,
          alpha: Math.random() * 0.5 + 0.25,
          colorType: i % 5 === 0 ? 'emerald' : i % 3 === 0 ? 'cyan' : 'cobalt'
        });
      }
    }

    function updateParticles() {
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0) p.x = width;
        if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        if (p.y > height) p.y = 0;

        // Mouse interaction
        if (mouse.active) {
          const dx = mouse.x - p.x;
          const dy = mouse.y - p.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < mouse.radius) {
            const force = (1 - dist / mouse.radius) * 0.8;
            p.x -= (dx / dist) * force * 3;
            p.y -= (dy / dist) * force * 3;
          }
        }
      }
    }

    function draw() {
      ctx.clearRect(0, 0, width, height);

      // Draw connections
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < MAX_DISTANCE) {
            const alpha = (1 - dist / MAX_DISTANCE) * 0.18;
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = ACCENT_COLOR + alpha + ')';
            ctx.lineWidth = 0.8;
            ctx.stroke();
          }
        }
      }

      // Draw particles
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);

        let color = ACCENT_COLOR;
        if (p.colorType === 'emerald') color = SECONDARY_COLOR;
        if (p.colorType === 'cyan') color = CYAN_COLOR;

        ctx.fillStyle = color + p.alpha + ')';
        ctx.shadowBlur = p.radius * 4;
        ctx.shadowColor = color + '0.6)';
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      // Mouse connection line
      if (mouse.active) {
        for (let i = 0; i < particles.length; i++) {
          const dx = mouse.x - particles[i].x;
          const dy = mouse.y - particles[i].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < mouse.radius) {
            const alpha = (1 - dist / mouse.radius) * 0.35;
            ctx.beginPath();
            ctx.moveTo(mouse.x, mouse.y);
            ctx.lineTo(particles[i].x, particles[i].y);
            ctx.strokeStyle = CYAN_COLOR + alpha + ')';
            ctx.lineWidth = 1;
            ctx.stroke();
          }
        }
      }
    }

    function loop() {
      updateParticles();
      draw();
      animationFrameId = requestAnimationFrame(loop);
    }

    function onMouseMove(e) {
      const rect = canvas.getBoundingClientRect();
      mouse.x = e.clientX - rect.left;
      mouse.y = e.clientY - rect.top;
      mouse.active = true;
    }

    function onMouseLeave() {
      mouse.active = false;
      mouse.x = -9999;
      mouse.y = -9999;
    }

    window.addEventListener('resize', resize, { passive: true });
    window.addEventListener('mousemove', onMouseMove, { passive: true });
    document.addEventListener('mouseleave', onMouseLeave, { passive: true });

    resize();
    loop();
  }

  // Auto-init on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      document.querySelectorAll('.ambient-canvas, #ambient-canvas').forEach(initAmbientCanvas);
    });
  } else {
    document.querySelectorAll('.ambient-canvas, #ambient-canvas').forEach(initAmbientCanvas);
  }

  window.initAmbientCanvas = initAmbientCanvas;
})();
