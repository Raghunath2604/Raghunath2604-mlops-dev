/* ═══════════════════════════════════════════════════════════════
   MLOps.dev — Motion Architecture Engine
   GSAP-powered scroll-driven animations, micro-interactions,
   and intelligent state transitions.
   ═══════════════════════════════════════════════════════════════ */

(function(){
  'use strict';

  /* ── Respect user preference ── */
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ── Utilities ── */
  function qs(sel, ctx){ return (ctx||document).querySelector(sel); }
  function qsa(sel, ctx){ return Array.from((ctx||document).querySelectorAll(sel)); }
  function onReady(fn){ document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', fn) : fn(); }

  /* ══════════════════════════════════════════════════════════════
     1. SCROLL-DRIVEN REVEAL SYSTEM (IntersectionObserver)
     Replaces basic .rv/.rvl/.rvr with staggered, spring-like entries.
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

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if(entry.isIntersecting){
          entry.target.classList.add('on');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15, rootMargin: '0px 0px -60px 0px' });

    qsa('.rv, .rvl, .rvr, .rv-scale, .rv-blur').forEach(el => observer.observe(el));
  }

  /* ══════════════════════════════════════════════════════════════
     2. SMOOTH COUNTER ANIMATIONS (countUp on scroll)
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
    }, { threshold: 0.5 });

    qsa('[data-count]').forEach(el => counterObserver.observe(el));
  }

  function animateCounter(el){
    const target = parseFloat(el.dataset.count);
    const suffix = el.dataset.suffix || '';
    const prefix = el.dataset.prefix || '';
    const duration = 1800;
    const start = performance.now();
    const isFloat = target % 1 !== 0;

    function tick(now){
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      /* Ease out cubic */
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = isFloat ? (target * eased).toFixed(1) : Math.round(target * eased);
      el.textContent = prefix + current + suffix;
      if(progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  /* ══════════════════════════════════════════════════════════════
     3. MAGNETIC BUTTON EFFECT
     Buttons subtly follow the cursor within their bounds.
     ══════════════════════════════════════════════════════════════ */
  function initMagneticButtons(){
    if(prefersReducedMotion) return;

    qsa('.mag-btn, .cta-primary, .nav-cta, .plan-btn-solid, .btn-submit-yellow, .btn-social-pill, .demo-quick-btn, .cta-btn-white, .cta-btn-outline, .wl-submit, .btn-otp-verify').forEach(btn => {
      btn.addEventListener('mousemove', (e) => {
        const rect = btn.getBoundingClientRect();
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;
        btn.style.transform = `translate(${x * 0.12}px, ${y * 0.12}px)`;
      });

      btn.addEventListener('mouseleave', () => {
        btn.style.transform = 'translate(0, 0)';
        btn.style.transition = 'transform 0.4s cubic-bezier(0.22, 1, 0.36, 1)';
        setTimeout(() => { btn.style.transition = ''; }, 400);
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     4. CARD SPOTLIGHT / FLASHLIGHT HOVER EFFECT
     Radial gradient follows cursor over cards.
     ══════════════════════════════════════════════════════════════ */
  function initCardSpotlight(){
    if(prefersReducedMotion) return;

    qsa('.plan, .prob-card, .tcard, .how-step, .spec-feat, .spec-num, .kpi, .panel, .auth-stage-container, .oauth-modal-card, .fleet-window, .card, .stat-card').forEach(card => {
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
     5. TEXT SPLIT & STAGGER ENTRANCE
     Splits heading text into chars for staggered reveal.
     ══════════════════════════════════════════════════════════════ */
  function initTextSplit(){
    if(prefersReducedMotion) return;

    qsa('[data-split]').forEach(el => {
      const text = el.textContent;
      el.innerHTML = '';
      el.setAttribute('aria-label', text);

      text.split('').forEach((char, i) => {
        const span = document.createElement('span');
        span.className = 'split-char';
        span.textContent = char === ' ' ? '\u00A0' : char;
        span.style.animationDelay = (i * 0.03) + 's';
        el.appendChild(span);
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     6. PARALLAX DEPTH LAYERS
     Subtle parallax on scroll for depth.
     ══════════════════════════════════════════════════════════════ */
  function initParallax(){
    if(prefersReducedMotion) return;

    const layers = qsa('[data-parallax]');
    if(!layers.length) return;

    let ticking = false;
    window.addEventListener('scroll', () => {
      if(!ticking){
        requestAnimationFrame(() => {
          const scrollY = window.scrollY;
          layers.forEach(layer => {
            const speed = parseFloat(layer.dataset.parallax) || 0.1;
            layer.style.transform = `translateY(${scrollY * speed}px)`;
          });
          ticking = false;
        });
        ticking = true;
      }
    }, { passive: true });
  }

  /* ══════════════════════════════════════════════════════════════
     7. SCROLL PROGRESS BAR (enhanced)
     Smooth, hardware-accelerated progress indicator.
     ══════════════════════════════════════════════════════════════ */
  function initScrollProgress(){
    const bar = qs('#sp');
    if(!bar) return;

    let ticking = false;
    window.addEventListener('scroll', () => {
      if(!ticking){
        requestAnimationFrame(() => {
          const h = document.documentElement;
          const pct = (h.scrollTop / (h.scrollHeight - h.clientHeight)) * 100;
          bar.style.width = pct + '%';
          ticking = false;
        });
        ticking = true;
      }
    }, { passive: true });
  }

  /* ══════════════════════════════════════════════════════════════
     8. SMOOTH SECTION TRANSITIONS (fade between scroll sections)
     ══════════════════════════════════════════════════════════════ */
  function initSectionFades(){
    if(prefersReducedMotion) return;

    const sections = qsa('section, .sec, .prob-wrap, .spec-wrap, .how-wrap, .pricing-wrap, .wl-wrap, .cta-strip');
    const sectionObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if(entry.isIntersecting){
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
        }
      });
    }, { threshold: 0.05 });

    sections.forEach(sec => {
      sec.style.opacity = '0';
      sec.style.transform = 'translateY(20px)';
      sec.style.transition = 'opacity 0.8s cubic-bezier(0.22, 1, 0.36, 1), transform 0.8s cubic-bezier(0.22, 1, 0.36, 1)';
      sectionObserver.observe(sec);
    });
  }

  /* ══════════════════════════════════════════════════════════════
     9. RIPPLE EFFECT on buttons
     ══════════════════════════════════════════════════════════════ */
  function initRipple(){
    if(prefersReducedMotion) return;

    document.addEventListener('click', (e) => {
      const btn = e.target.closest('.cta-primary, .plan-btn, .wl-submit, .nav-cta, .btn-full, .scta-btn');
      if(!btn) return;

      const ripple = document.createElement('span');
      ripple.className = 'ripple-effect';
      const rect = btn.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height) * 2;
      ripple.style.width = ripple.style.height = size + 'px';
      ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
      ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';
      btn.style.position = 'relative';
      btn.style.overflow = 'hidden';
      btn.appendChild(ripple);
      ripple.addEventListener('animationend', () => ripple.remove());
    });
  }

  /* ══════════════════════════════════════════════════════════════
     10. TILT EFFECT on feature cards
     ══════════════════════════════════════════════════════════════ */
  function initTilt(){
    if(prefersReducedMotion) return;

    qsa('.plan, .fleet-window, .tcard').forEach(card => {
      card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width - 0.5;
        const y = (e.clientY - rect.top) / rect.height - 0.5;
        card.style.transform = `perspective(800px) rotateY(${x * 4}deg) rotateX(${-y * 4}deg) scale(1.01)`;
        card.style.transition = 'transform 0.1s ease';
      });

      card.addEventListener('mouseleave', () => {
        card.style.transform = 'perspective(800px) rotateY(0) rotateX(0) scale(1)';
        card.style.transition = 'transform 0.5s cubic-bezier(0.22, 1, 0.36, 1)';
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     11. STAGGER GRID CHILDREN on scroll
     ══════════════════════════════════════════════════════════════ */
  function initStaggerGrids(){
    if(prefersReducedMotion) return;

    const grids = qsa('.plans-grid, .tcard-grid, .how-steps, .spec-features, .spec-numbers, .fw-kpis');

    const gridObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if(entry.isIntersecting){
          const children = Array.from(entry.target.children);
          children.forEach((child, i) => {
            child.style.opacity = '0';
            child.style.transform = 'translateY(24px)';
            child.style.transition = `opacity 0.6s cubic-bezier(0.22, 1, 0.36, 1) ${i * 0.1}s, transform 0.6s cubic-bezier(0.22, 1, 0.36, 1) ${i * 0.1}s`;
            requestAnimationFrame(() => {
              child.style.opacity = '1';
              child.style.transform = 'translateY(0)';
            });
          });
          gridObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });

    grids.forEach(grid => gridObserver.observe(grid));
  }

  /* ══════════════════════════════════════════════════════════════
     INIT ALL
     ══════════════════════════════════════════════════════════════ */
  onReady(function(){
    initScrollReveals();
    initCounters();
    initMagneticButtons();
    initCardSpotlight();
    initTextSplit();
    initParallax();
    initScrollProgress();
    initSectionFades();
    initRipple();
    initTilt();
    initStaggerGrids();

    console.log('[MLOps.dev] Motion engine initialized' + (prefersReducedMotion ? ' (reduced motion)' : ''));
  });

})();
