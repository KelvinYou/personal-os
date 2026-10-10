/* Travel-plan HTML controls. Inline verbatim; usable through file://. */
(() => {
  const root = document.documentElement;
  const zh = root.lang.toLowerCase().startsWith('zh');
  const theme = document.getElementById('theme');
  const print = document.getElementById('print');
  const clarity = document.getElementById('clarity');
  const appearance = document.querySelector('.appearance');
  if (appearance) appearance.open = false;
  appearance?.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      appearance.open = false;
      appearance.querySelector('summary')?.focus();
    }
  });
  let preference = 'light';
  try {
    const saved = localStorage.getItem('travel-plan-theme');
    if (saved === 'light' || saved === 'dark') preference = saved;
  } catch (_) {}
  function applyTheme() {
    root.dataset.theme = preference;
    if (theme) theme.checked = preference === 'dark';
  }
  applyTheme();
  root.dataset.material = 'glass';
  if (clarity) clarity.checked = false;
  theme?.addEventListener('change', () => {
    preference = theme.checked ? 'dark' : 'light';
    applyTheme();
    try { localStorage.setItem('travel-plan-theme', preference); } catch (_) {}
  });
  clarity?.addEventListener('change', () => {
    root.dataset.material = clarity.checked ? 'solid' : 'glass';
  });
  print?.addEventListener('click', () => window.print());
  window.addEventListener('beforeprint', () => {
    document.querySelectorAll('details').forEach(item => {
      item.dataset.printOpen = String(item.open);
      item.open = true;
    });
  });
  window.addEventListener('afterprint', () => {
    document.querySelectorAll('details[data-print-open]').forEach(item => {
      item.open = item.dataset.printOpen === 'true';
    });
  });
  // Reveal script-only actions only after their handlers are attached.
  root.classList.add('controls-ready');
  // Reflect the section being read without replacing native anchor navigation.
  const navLinks = [...document.querySelectorAll('.nav a[href^="#"]')];
  const sections = navLinks.map(link => ({link, section: document.getElementById(link.hash.slice(1))})).filter(item => item.section);
  let scheduled = false;
  function updateLocation() {
    scheduled = false;
    let current = null;
    for (const item of sections) {
      if (item.section.getBoundingClientRect().top <= innerHeight * 0.3) current = item;
    }
    for (const item of sections) {
      if (item === current) item.link.setAttribute('aria-current', 'location');
      else item.link.removeAttribute('aria-current');
    }
  }
  function scheduleLocation() {
    if (!scheduled) { scheduled = true; if (typeof requestAnimationFrame === 'function') requestAnimationFrame(updateLocation); else updateLocation(); }
  }
  addEventListener('scroll', scheduleLocation, {passive: true});
  addEventListener('resize', scheduleLocation);
  addEventListener('hashchange', scheduleLocation);
  updateLocation();
  // Make deliberately scrollable comparison tables discoverable and keyboard usable.
  document.querySelectorAll('.scroll').forEach(region => {
    region.tabIndex = 0;
    region.setAttribute('role', 'region');
    region.setAttribute('aria-label', zh ? '表格，可横向滚动' : 'Table, scroll horizontally');
    const hint = document.createElement('p');
    hint.className = 'table-hint';
    hint.textContent = zh ? '表格较宽时，左右滑动查看。' : 'Swipe sideways when the table is wider than the screen.';
    region.before(hint);
  });
  root.classList.add('enhanced');
})();
