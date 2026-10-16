/* Regression coverage for text geometry and the live resize preview. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../assets/text_interactions.js"), "utf8");

function editor({ devicePixelRatio = 1, atlasReady = true } = {}) {
  const handlers = new Map();
  const canvases = [];
  const observers = new Set();
  const imageListeners = new Set();
  const layout = {
    canvasWidth: 1000, canvasHeight: 800, width: 400, height: 240,
    fontFamily: "Microsoft YaHei", fontSize: 36, padding: 13, lineHeight: 60,
    bold: false, color: "#ffffff", background: "#000000", opacity: 65, align: "left",
  };
  layout.atlas = "pillow-glyphs.png";
  layout.kerning = {};
  layout.glyphs = Object.fromEntries(Array.from({ length: 95 }, (_, index) => {
    const character = String.fromCharCode(index + 32);
    return [character, { x: index * 20, y: 0, width: 18, height: 28, left: 0, top: -28,
      inkWidth: character === " " ? 0 : 18, inkHeight: character === " " ? 0 : 28, advance: 18 }];
  }));
  const atlases = [];
  class AtlasImage {
    constructor() {
      this.complete = atlasReady;
      this.naturalWidth = atlasReady ? 2000 : 0;
      atlases.push(this);
    }
  }
  const image = {
    alt: "A long text annotation that wraps as the box gets narrower",
    src: "original.png", currentSrc: "original.png", complete: true,
    addEventListener: (type, callback) => imageListeners.add(callback),
    removeEventListener: (type, callback) => imageListeners.delete(callback),
  };
  const stage = { getBoundingClientRect: () => ({ left: 0, top: 0, width: 1000, height: 800 }) };
  const box = {
    dataset: { textId: "annotation", textLayout: JSON.stringify(layout) }, style: {},
    getBoundingClientRect: () => ({ left: 100, right: 500, top: 100, bottom: 340, width: 400, height: 240 }),
    closest: selector => selector === "[data-text-id]" ? box : selector === "#crop-stage" ? stage : null,
    contains: node => node === box,
    setPointerCapture() {},
    querySelector: () => image,
    appendChild() {},
  };
  class Input {
    set value(value) { this.text = value; }
    dispatchEvent() {}
  }
  const input = new Input();
  const document = {
    getElementById: () => input,
    createElement(tag) {
      assert.equal(tag, "canvas");
      const context = {
        draws: [], transforms: [],
        setTransform(...values) { this.transforms.push(values); },
        beginPath() {}, roundRect() {}, rect() {}, clip() {}, save() {}, restore() {}, fill() {},
        measureText() { throw new Error("Live resize must use Pillow metrics"); },
        fillText() { throw new Error("Live resize must not rasterize browser fonts"); },
        drawImage(bitmap, sx, sy, sw, sh, x, y, width, height) {
          const text = Object.keys(layout.glyphs).find(letter => layout.glyphs[letter].x === sx);
          this.draws.push({ bitmap, text, x, y, width, height, sourceWidth: sw, sourceHeight: sh, composition: this.globalCompositeOperation });
        },
      };
      const canvas = {
        context, setAttribute() {}, getContext: () => context,
        remove() { this.removed = true; },
      };
      canvases.push(canvas);
      return canvas;
    },
    addEventListener(type, callback, options) {
      const list = handlers.get(type) || [];
      list.push({ callback, signal: options?.signal });
      handlers.set(type, list);
    },
  };
  class MutationObserver {
    constructor(callback) { this.callback = callback; }
    observe() { observers.add(this); }
    disconnect() { observers.delete(this); }
  }
  const context = vm.createContext({ document, window: { devicePixelRatio }, Image: AtlasImage, HTMLInputElement: Input, Event, AbortController, MutationObserver });
  function load() { vm.runInContext(source, context); }
  function emit(type, x, y, target = box) {
    const event = { target, button: 0, pointerId: 1, pointerType: "mouse", clientX: x, clientY: y, preventDefault() {} };
    for (const listener of handlers.get(type) || []) {
      if (!listener.signal?.aborted) listener.callback(event);
    }
  }
  load();
  function updateLayout(updates) {
    box.dataset.textLayout = JSON.stringify({ ...layout, ...updates });
    for (const observer of observers) observer.callback();
  }
  function imageLoaded() {
    image.complete = true;
    image.currentSrc = image.src;
    for (const listener of imageListeners) listener();
  }
  return { box, input, emit, load, image, canvases, atlases, updateLayout, imageLoaded };
}

for (const scenario of [
  { edge: "right", from: [498, 165], to: [548, 165], key: "width", size: 45, x: 10, y: 12.5 },
  { edge: "left", from: [102, 165], to: [62, 165], key: "width", size: 44, x: 6, y: 12.5 },
  { edge: "top", from: [200, 102], to: [200, 62], key: "height", size: 35, x: 10, y: 7.5 },
  { edge: "bottom", from: [200, 338], to: [200, 378], key: "height", size: 35, x: 10, y: 12.5 },
]) {
  test(`resizes the ${scenario.edge} border between dots instead of moving`, () => {
    const { emit, input } = editor();
    emit("pointerdown", ...scenario.from);
    emit("pointermove", ...scenario.to);
    emit("pointerup", ...scenario.to);
    const result = JSON.parse(input.text);
    assert.equal(result[scenario.key], scenario.size);
    assert.equal(result.x, scenario.x);
    assert.equal(result.y, scenario.y);
  });
}

test("corner proximity resizes both dimensions without hitting a dot", () => {
  const { emit, input } = editor();
  emit("pointerdown", 495, 335);
  emit("pointermove", 545, 375);
  emit("pointerup", 545, 375);
  assert.deepEqual(JSON.parse(input.text), { id: "annotation", x: 10, y: 12.5, width: 45, height: 35 });
});

test("dragging the interior still only moves the box", () => {
  const { emit, input } = editor();
  emit("pointerdown", 300, 220);
  emit("pointermove", 350, 260);
  emit("pointerup", 350, 260);
  assert.deepEqual(JSON.parse(input.text), { id: "annotation", x: 15, y: 17.5 });
});

test("hover shows a resize cursor across the whole border", () => {
  const { box, emit } = editor();
  emit("pointermove", 498, 165);
  assert.equal(box.style.cursor, "ew-resize");
  emit("pointermove", 200, 102);
  assert.equal(box.style.cursor, "ns-resize");
  emit("pointermove", 300, 220);
  assert.equal(box.style.cursor, "move");
});

test("reloading interaction code removes the previous listeners", () => {
  const { emit, input, load } = editor();
  load();
  emit("pointerdown", 498, 165);
  emit("pointermove", 548, 165);
  emit("pointerup", 548, 165);
  assert.equal(JSON.parse(input.text).width, 45);
});

test("resizing reuses Pillow glyph pixels at the same size", () => {
  const { box, emit, canvases } = editor();
  emit("pointerdown", 495, 335);
  emit("pointermove", 545, 375);
  emit("pointermove", 595, 415);
  assert.equal(box.dataset.textResizing, "true");
  assert.equal(canvases.length, 1);
  assert.equal(canvases[0].width, 500);
  assert.equal(canvases[0].height, 320);
  const { draws, transforms } = canvases[0].context;
  assert.ok(draws.length > 0);
  assert.ok(draws.every(draw => draw.width === 18 && draw.height === 28));
  assert.ok(draws.every(draw => draw.composition === "copy"));
  assert.ok(draws.every(draw => draw.sourceWidth === draw.width && draw.sourceHeight === draw.height));
  assert.ok(transforms.every(values => values[0] === values[3]));
});

test("narrowing the box rewraps text instead of squeezing it", () => {
  const { emit, canvases, image } = editor();
  image.alt = "Text should wrap without squeezing its glyphs";
  emit("pointerdown", 498, 165);
  emit("pointermove", 548, 165);
  const context = canvases[0].context;
  const wideLines = context.draws.map(draw => draw.text);
  const wideLineCount = new Set(context.draws.map(draw => draw.y)).size;
  context.draws = [];
  emit("pointermove", 348, 165);
  const narrowLines = context.draws.map(draw => draw.text);
  assert.ok(new Set(context.draws.map(draw => draw.y)).size > wideLineCount);
  assert.equal(narrowLines.join(""), wideLines.join(""));
});

test("the live preview stays until the new bitmap and matching layout are ready", () => {
  const { box, emit, canvases, image, updateLayout, imageLoaded } = editor();
  emit("pointerdown", 498, 165);
  emit("pointermove", 548, 165);
  emit("pointerup", 548, 165);
  assert.equal(box.dataset.textResizing, "true");
  image.src = "resized.png";
  image.complete = false;
  updateLayout({ width: 450 });
  assert.equal(box.dataset.textResizing, "true");
  imageLoaded();
  assert.equal(box.dataset.textResizing, undefined);
  assert.equal(canvases[0].removed, true);
});

test("returning to the original size clears the preview without a bitmap reload", () => {
  const { box, emit, canvases } = editor();
  emit("pointerdown", 498, 165);
  emit("pointermove", 548, 165);
  emit("pointermove", 498, 165);
  emit("pointerup", 498, 165);
  assert.equal(box.dataset.textResizing, undefined);
  assert.equal(canvases[0].removed, true);
});

test("reloading the script also removes an unfinished preview", () => {
  const { box, emit, canvases, load } = editor();
  emit("pointerdown", 498, 165);
  emit("pointermove", 548, 165);
  load();
  assert.equal(box.dataset.textResizing, undefined);
  assert.equal(canvases[0].removed, true);
});


test("screen DPI does not change the glyph raster resolution", () => {
  for (const devicePixelRatio of [1, 1.25, 2]) {
    const { emit, canvases } = editor({ devicePixelRatio });
    emit("pointerdown", 498, 165);
    emit("pointermove", 548, 165);
    assert.equal(canvases[0].width, 450);
    assert.equal(canvases[0].height, 240);
    assert.ok(canvases[0].context.transforms.every(values => values[0] === 1 && values[3] === 1));
  }
});

test("while glyphs decode the existing bitmap keeps its original dimensions", () => {
  const { emit, canvases, atlases, image } = editor({ atlasReady: false });
  emit("pointerdown", 498, 165);
  emit("pointermove", 548, 165);
  const context = canvases[0].context;
  assert.equal(context.draws[0].bitmap, image);
  assert.equal(context.draws[0].sourceWidth, 400);
  assert.equal(context.draws[0].sourceHeight, 240);
  context.draws = [];
  atlases[0].complete = true;
  atlases[0].naturalWidth = 2000;
  atlases[0].onload();
  assert.ok(context.draws.length > 0);
  assert.ok(context.draws.every(draw => draw.bitmap === atlases[0]));
});
