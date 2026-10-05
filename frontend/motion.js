/* ═══════════════════════════════════════════════════════════════
   MLOps.dev — Framer Motion & 21st.dev UI Architecture Engine
   Powered by Framer Motion / Motion One WAAPI Spring Physics
   ═══════════════════════════════════════════════════════════════ */

(function(){
  'use strict';

  /* ── User Motion Preference ── */
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ── Helpers ── */
  function qs(sel, ctx){ return (ctx||document).querySelector(sel); }
  function qsa(sel, ctx){ return Array.from((ctx||document).querySelectorAll(sel)); }
  function onReady(fn){ document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', fn) : fn(); }

  /* ══════════════════════════════════════════════════════════════
     1. FRAMER MOTION / MOTION ONE CORE INTEGRATION
     ══════════════════════════════════════════════════════════════ */
  const M = window.Motion || null;

  /* ══════════════════════════════════════════════════════════════
     2. SPRING-LOADED SCROLL REVEALS (21st.dev InView)
     ══════════════════════════════════════════════════════════════ */
  function initScrollReveals(){
    if(prefersReducedMotion) {
      qsa('.rv, .rvl, .rvr, .rv-scale, .rv-blur').forEach(el => {
        el.style.opacity = '1';
        el.style.transform = 'none';
        el.style.filter = 'none';
      });
      return;
    }

    if(M && M.inView){
      qsa('.rv, .rvl, .rvr, .rv-scale, .rv-blur').forEach(el => {
        M.inView(el, ({ target }) => {
          const isLeft = target.classList.contains('rvl');
          const isRight = target.classList.contains('rvr');
          const isScale = target.classList.contains('rv-scale');

          const initialX = isLeft ? -30 : isRight ? 30 : 0;
          const initialScale = isScale ? 0.95 : 1;

          M.animate(target, 
            { 
              opacity: [0, 1], 
              transform: [`translate3d(${initialX}px, 24px, 0) scale(${initialScale})`, 'translate3d(0, 0, 0) scale(1)'] 
            }, 
            { 
              duration: 0.65, 
              easing: [0.16, 1, 0.3, 1] 
            }
          );
        }, { margin: '0px 0px -40px 0px' });
      });
    } else {
      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if(entry.isIntersecting){
            entry.target.classList.add('on');
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'none';
            observer.unobserve(entry.target);
          }
        });
      }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

      qsa('.rv, .rvl, .rvr, .rv-scale, .rv-blur').forEach(el => observer.observe(el));
    }
  }

  /* ══════════════════════════════════════════════════════════════
     3. FRAMER MOTION MAGNETIC SPRING BUTTONS (21st.dev Style)
     ══════════════════════════════════════════════════════════════ */
  function initMagneticButtons(){
    if(prefersReducedMotion) return;

    const selectors = '.mag-btn, .cta-primary, .nav-cta, .plan-btn-solid, .btn-submit-yellow, .btn-social-pill, .demo-quick-btn, .cta-btn-white, .cta-btn-outline, .wl-submit, .btn-otp-verify';
    
    qsa(selectors).forEach(btn => {
      btn.addEventListener('mousemove', (e) => {
        const rect = btn.getBoundingClientRect();
        const x = (e.clientX - rect.left - rect.width / 2) * 0.18;
        const y = (e.clientY - rect.top - rect.height / 2) * 0.18;

        if(M && M.animate){
          M.animate(btn, { transform: `translate3d(${x}px, ${y}px, 0)` }, { duration: 0.15 });
        } else {
          btn.style.transform = `translate3d(${x}px, ${y}px, 0)`;
        }
      });

      btn.addEventListener('mouseleave', () => {
        if(M && M.animate){
          M.animate(btn, { transform: 'translate3d(0, 0, 0)' }, { 
            duration: 0.5, 
            easing: [0.175, 0.885, 0.32, 1.275] // spring bounce
          });
        } else {
          btn.style.transform = 'translate3d(0, 0, 0)';
          btn.style.transition = 'transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
          setTimeout(() => { btn.style.transition = ''; }, 400);
        }
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     4. CURSOR-AWARE RADIAL SPOTLIGHT (Magic UI / 21st.dev)
     ══════════════════════════════════════════════════════════════ */
  function initCardSpotlight(){
    if(prefersReducedMotion) return;

    const cards = qsa('.plan, .prob-card, .tcard, .how-step, .spec-feat, .spec-num, .kpi, .panel, .auth-stage-container, .oauth-modal-card, .fleet-window, .card, .stat-card, .bento-card, .metric-card');

    cards.forEach(card => {
      card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        card.style.setProperty('--spotlight-x', x + 'px');
        card.style.setProperty('--spotlight-y', y + 'px');
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     5. 3D CARD PERSPECTIVE TILT (OriginKit / 21st.dev)
     ══════════════════════════════════════════════════════════════ */
  function initTilt(){
    if(prefersReducedMotion) return;

    qsa('.plan, .fleet-window, .tcard, .bento-card').forEach(card => {
      card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width - 0.5;
        const y = (e.clientY - rect.top) / rect.height - 0.5;

        const tiltX = -y * 5;
        const tiltY = x * 5;

        card.style.transform = `perspective(1000px) rotateX(${tiltX}deg) rotateY(${tiltY}deg) translate3d(0, -2px, 0)`;
        card.style.transition = 'transform 0.1s ease-out';
      });

      card.addEventListener('mouseleave', () => {
        card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translate3d(0, 0, 0)';
        card.style.transition = 'transform 0.5s cubic-bezier(0.16, 1, 0.3, 1)';
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     6. LIVE COUNTER INTERPOLATION (NumberTicker)
     ══════════════════════════════════════════════════════════════ */
  function initCounters(){
    if(prefersReducedMotion) return;

    const counterObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if(entry.isIntersecting){
          animateCounter(entry.target);
          counterObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.4 });

    qsa('[data-count]').forEach(el => counterObserver.observe(el));
  }

  function animateCounter(el){
    const target = parseFloat(el.dataset.count);
    const suffix = el.dataset.suffix || '';
    const prefix = el.dataset.prefix || '';
    const duration = 1600;
    const start = performance.now();
    const isFloat = target % 1 !== 0;

    function tick(now){
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Quintic ease-out for ultra smooth number deceleration
      const eased = 1 - Math.pow(1 - progress, 4);
      const current = isFloat ? (target * eased).toFixed(1) : Math.round(target * eased);
      el.textContent = prefix + current + suffix;
      if(progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  /* ══════════════════════════════════════════════════════════════
     7. HARDWARE SCROLL PROGRESS HUD
     ══════════════════════════════════════════════════════════════ */
  function initScrollProgress(){
    const bar = qs('#sp, #scroll-prog-d');
    if(!bar) return;

    window.addEventListener('scroll', () => {
      requestAnimationFrame(() => {
        const h = document.documentElement;
        const pct = (h.scrollTop / (h.scrollHeight - h.clientHeight)) * 100;
        bar.style.width = pct + '%';
      });
    }, { passive: true });
  }

  /* ══════════════════════════════════════════════════════════════
     INIT ALL ENGINES ON DOM READY
     ══════════════════════════════════════════════════════════════ */
  onReady(function(){
    initScrollReveals();
    initMagneticButtons();
    initCardSpotlight();
    initTilt();
    initCounters();
    initScrollProgress();

    console.log('[MLOps.dev] Framer Motion & 21st.dev UI Motion Engine initialized');
  });

})();

