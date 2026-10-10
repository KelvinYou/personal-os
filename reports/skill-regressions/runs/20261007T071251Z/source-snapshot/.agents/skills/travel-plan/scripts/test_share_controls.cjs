const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(process.argv[2] || path.join(__dirname, '../assets/share.js'), 'utf8');

function boot({ saved = null, blockedStorage = false, missingMedia = false } = {}) {
  const classes = new Set();
  const root = { lang: 'zh-CN', dataset: {}, classList: { add: name => classes.add(name) } };
  const events = {};
  function element() {
    return {
      checked: false, open: true, dataset: {}, label: { textContent: '' },
      addEventListener(type, handler) { this[type] = handler; },
      setAttribute() {}, removeAttribute() {},
      querySelector() { return this.label; }
    };
  }
  const theme = element(), clarity = element(), print = element(), appearance = element();
  const ids = { theme, clarity, print };
  let stored = saved, prints = 0;
  const context = {
    document: {
      documentElement: root, getElementById: id => ids[id],
      querySelector: selector => selector === '.appearance' ? appearance : null,
      querySelectorAll: selector => selector === 'details' || (selector === 'details[data-print-open]' && appearance.dataset.printOpen !== undefined) ? [appearance] : []
    },
    localStorage: {
      getItem() { if (blockedStorage) throw new Error('Storage denied'); return stored; },
      setItem(key, value) { if (blockedStorage) throw new Error('Storage denied'); stored = value; }
    },
    innerHeight: 800, requestAnimationFrame: callback => callback(),
    addEventListener: (type, handler) => { events[type] = handler; },
    window: { print: () => { prints += 1; }, addEventListener: (type, handler) => { events[type] = handler; } }
  };
  if (!missingMedia) context.matchMedia = () => ({ matches: true }); // dark OS, legacy media listener API
  vm.runInNewContext(source, context);
  return { root, classes, theme, clarity, print, appearance, events,
    stored: () => stored, prints: () => prints };
}

let page = boot({ missingMedia: true, blockedStorage: true });
assert.equal(page.root.dataset.theme, 'light', 'Default must remain light without browser/media/storage APIs');
assert(page.classes.has('controls-ready'), 'Controls must be exposed after their handlers are ready');
assert.equal(page.appearance.open, false, 'Menu starts closed');
page.theme.checked = true;
page.theme.change();
assert.equal(page.root.dataset.theme, 'dark', 'Checkbox turns dark mode on without storage');
page.theme.checked = false;
page.theme.change();
assert.equal(page.root.dataset.theme, 'light', 'Checkbox turns dark mode off');
page.clarity.checked = true;
page.clarity.change();
assert.equal(page.root.dataset.material, 'solid', 'Checkbox reduces glass');
page.clarity.checked = false;
page.clarity.change();
assert.equal(page.root.dataset.material, 'glass', 'Checkbox restores glass');
page.print.click();
assert.equal(page.prints(), 1, 'Print is wired');
page.events.beforeprint();
assert.equal(page.appearance.open, true);
page.events.afterprint();
assert.equal(page.appearance.open, false, 'Print restores disclosure state');

page = boot();
assert.equal(page.root.dataset.theme, 'light', 'Dark OS must not change a new page default');
page.theme.checked = true;
page.theme.change();
assert.equal(page.stored(), 'dark', 'Only explicit theme changes are persisted');
page = boot({ saved: 'dark' });
assert.equal(page.root.dataset.theme, 'dark', 'Restore an explicit saved preference');
assert.equal(page.theme.checked, true, 'Native checkbox reflects restored preference');
page = boot({ saved: 'invalid' });
assert.equal(page.root.dataset.theme, 'light', 'Unknown preference falls back to white');
console.log('PASS: white default, restricted APIs/storage, checkbox toggles, saved preference and printing');
