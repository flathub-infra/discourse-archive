// Run with: node --test scripts/test_theme.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "../output/assets/js/archive.js"), "utf8"
);

function setup(saved = null, storageBlocked = false, withHeader = true) {
  function element() {
    return {
      attributes: {}, children: [], listeners: {},
      setAttribute(key, value) { this.attributes[key] = value; },
      getAttribute(key) { return this.attributes[key] || null; },
      removeAttribute(key) { delete this.attributes[key]; },
      appendChild(child) { this.children.push(child); },
      addEventListener(name, listener) { this.listeners[name] = listener; },
    };
  }
  const root = element();
  const header = element();
  const window = element();
  const writes = [];
  vm.runInNewContext(source, {
    document: {
      documentElement: root,
      querySelector: selector => selector === ".header-inner" && withHeader ? header : null,
      createElement: element,
    },
    window,
    localStorage: {
      getItem() {
        if (storageBlocked) throw new Error("Storage blocked");
        return saved;
      },
      setItem(key, value) {
        if (storageBlocked) throw new Error("Storage blocked");
        writes.push([key, value]);
      },
    },
  });
  return { root, chooser: header.children[0], window, writes };
}

test("defaults to the system theme and provides a labelled chooser", () => {
  const { root, chooser } = setup();
  assert.equal(root.getAttribute("data-theme"), null);
  assert.equal(chooser.value, "system");
  assert.equal(chooser.getAttribute("aria-label"), "Color theme");
  assert.deepEqual(chooser.children.map(option => option.value), ["system", "light", "dark"]);
});

test("restores saved light and dark preferences; ignores invalid values", () => {
  for (const theme of ["light", "dark"]) {
    const { root, chooser } = setup(theme);
    assert.equal(root.getAttribute("data-theme"), theme);
    assert.equal(chooser.value, theme);
  }
  assert.equal(setup("invalid").chooser.value, "system");
});

test("persists changes and returning to System removes the override", () => {
  const { root, chooser, writes } = setup();
  for (const theme of ["dark", "light", "system"]) {
    chooser.value = theme;
    chooser.listeners.change();
    assert.equal(root.getAttribute("data-theme"), theme === "system" ? null : theme);
    assert.deepEqual(writes.at(-1), ["archive-theme", theme]);
  }
});

test("works when persistent storage is blocked", () => {
  const { root, chooser } = setup(null, true);
  chooser.value = "dark";
  chooser.listeners.change();
  assert.equal(root.getAttribute("data-theme"), "dark");
});

test("synchronizes changes and storage clearing from other tabs", () => {
  const { root, chooser, window } = setup("dark");
  window.listeners.storage({ key: "other", newValue: "light" });
  assert.equal(chooser.value, "dark");
  window.listeners.storage({ key: "archive-theme", newValue: "light" });
  assert.equal(root.getAttribute("data-theme"), "light");
  assert.equal(chooser.value, "light");
  window.listeners.storage({ key: null, newValue: null });
  assert.equal(root.getAttribute("data-theme"), null);
  assert.equal(chooser.value, "system");
});

test("pages without a header still restore the preference", () => {
  assert.equal(setup("dark", false, false).root.getAttribute("data-theme"), "dark");
});
