/* Pointer-driven crop movement/resizing. State is synchronized through the
   hidden Reflex range inputs when a gesture completes. */
(function () {
  let drag = null;

  function number(id) {
    const input = document.getElementById(id);
    return input ? Number(input.value) : 0;
  }

  function sync(id, value) {
    const input = document.getElementById(id);
    if (!input) return;
    const descriptor = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
    descriptor.set.call(input, String(value));
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function render(selection, values) {
    selection.style.left = values.x + "%";
    selection.style.top = values.y + "%";
    selection.style.width = values.w + "%";
    selection.style.height = values.h + "%";
  }

  document.addEventListener("pointerdown", function (event) {
    const selection = event.target.closest("#crop-selection");
    if (!selection) return;
    const overlay = document.getElementById("crop-stage-overlay");
    if (!overlay) return;
    event.preventDefault();
    selection.setPointerCapture?.(event.pointerId);
    drag = {
      selection,
      overlay,
      handle: event.target.dataset.handle || "move",
      startX: event.clientX,
      startY: event.clientY,
      values: { x: number("crop-x"), y: number("crop-y"), w: number("crop-w"), h: number("crop-h") },
    };
  });

  document.addEventListener("pointermove", function (event) {
    if (!drag) return;
    const rect = drag.overlay.getBoundingClientRect();
    const dx = (event.clientX - drag.startX) / rect.width * 100;
    const dy = (event.clientY - drag.startY) / rect.height * 100;
    let { x, y, w, h } = drag.values;
    const handle = drag.handle;
    if (handle === "move") {
      x = Math.max(0, Math.min(100 - w, x + dx));
      y = Math.max(0, Math.min(100 - h, y + dy));
    } else {
      if (handle.includes("w")) { const right = x + w; x = Math.max(0, Math.min(right - 1, x + dx)); w = right - x; }
      if (handle.includes("e")) w = Math.max(1, Math.min(100 - x, w + dx));
      if (handle.includes("n")) { const bottom = y + h; y = Math.max(0, Math.min(bottom - 1, y + dy)); h = bottom - y; }
      if (handle.includes("s")) h = Math.max(1, Math.min(100 - y, h + dy));
    }
    drag.current = { x, y, w, h };
    render(drag.selection, drag.current);
  });

  document.addEventListener("pointerup", function () {
    if (!drag) return;
    const values = drag.current || drag.values;
    sync("crop-x", values.x.toFixed(3));
    sync("crop-y", values.y.toFixed(3));
    sync("crop-w", values.w.toFixed(3));
    sync("crop-h", values.h.toFixed(3));
    drag = null;
  });
})();
