/* Move/resize text tiles locally, then commit their geometry to Reflex. */
(function () {
  // Replacing a script during development must not leave two gesture handlers.
  window.photoToolTextInteractions?.abort();
  const controller = new AbortController();
  window.photoToolTextInteractions = controller;
  const listenerOptions = { signal: controller.signal };
  let drag = null;
  const previews = new Map();
  const cursors = {
    move: "move", n: "ns-resize", s: "ns-resize", e: "ew-resize", w: "ew-resize",
    nw: "nwse-resize", se: "nwse-resize", ne: "nesw-resize", sw: "nesw-resize",
  };

  function handleAt(event, box, rect = box.getBoundingClientRect()) {
    const control = event.target.closest("[data-text-handle]");
    if (control && box.contains(control)) return control.dataset.textHandle;
    // Treat the whole border as a resize target, including gaps between dots.
    const margin = event.pointerType === "touch" ? 14 : 10;
    const horizontalMargin = Math.min(margin, rect.width / 3);
    const verticalMargin = Math.min(margin, rect.height / 3);
    const horizontal = event.clientX - rect.left <= horizontalMargin ? "w"
      : rect.right - event.clientX <= horizontalMargin ? "e" : "";
    const vertical = event.clientY - rect.top <= verticalMargin ? "n"
      : rect.bottom - event.clientY <= verticalMargin ? "s" : "";
    return vertical + horizontal || "move";
  }

  function sync(box, position) {
    const input = document.getElementById("text-box-sync");
    if (!input) return;
    const descriptor = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
    const geometry = Object.fromEntries(Object.entries(position).map(([key, value]) => [key, Math.round(value * 1e6) / 1e6]));
    descriptor.set.call(input, JSON.stringify({ id: box.dataset.textId, ...geometry }));
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function textWidth(text, layout) {
    let width = 0, previous = "";
    for (const letter of text) {
      width += layout.glyphs[letter].advance + (layout.kerning[previous + letter] || 0);
      previous = letter;
    }
    return width;
  }

  function textBounds(text, layout) {
    if (layout.lineBounds?.[text]) return layout.lineBounds[text];
    let left = Infinity, top = Infinity, right = -Infinity, bottom = -Infinity;
    let cursor = 0, previous = "";
    for (const letter of text) {
      const glyph = layout.glyphs[letter];
      cursor += layout.kerning[previous + letter] || 0;
      const bounds = glyph.visibleBounds || [glyph.left, glyph.top, glyph.left + glyph.inkWidth, glyph.top + glyph.inkHeight];
      if (bounds[2] > bounds[0] && bounds[3] > bounds[1]) {
        left = Math.min(left, cursor + bounds[0]);
        right = Math.max(right, cursor + bounds[2]);
        top = Math.min(top, bounds[1]);
        bottom = Math.max(bottom, bounds[3]);
      }
      cursor += glyph.advance;
      previous = letter;
    }
    return left === Infinity ? [0, 0, 0, 0] : [left, top, right, bottom];
  }

  function wrapText(text, layout, width) {
    const lines = [];
    for (const paragraph of text.replace(/\r\n?/g, "\n").split("\n")) {
      let line = "", column = 0;
      for (const character of paragraph) {
        const expanded = character === "\t" ? " ".repeat(4 - column % 4) : character;
        for (const letter of expanded) {
          if (line && textWidth(line + letter, layout) > width) {
            const bounds = textBounds(line + letter, layout);
            if (bounds[2] - bounds[0] > width) {
              lines.push(line);
              line = "";
            }
          }
          line += letter;
          column++;
        }
      }
      lines.push(line);
    }
    return lines;
  }

  function removePreview(preview) {
    preview.observer.disconnect();
    preview.image.removeEventListener("load", preview.ready);
    preview.atlas.onload = null;
    preview.canvas.remove();
    delete preview.box.dataset.textResizing;
    previews.delete(preview.box);
  }

  function settlePreview(preview) {
    if (drag?.box === preview.box || !preview.target || !preview.image.complete
        || preview.image.currentSrc !== preview.image.src) return;
    const layout = JSON.parse(preview.box.dataset.textLayout);
    if (layout.width === preview.target.width && layout.height === preview.target.height) removePreview(preview);
  }

  function resizePreview(gesture, position) {
    let preview = previews.get(gesture.box);
    if (!preview) {
      const image = gesture.box.querySelector(".text-box-image");
      if (!image || !gesture.box.dataset.textLayout) return;
      const canvas = document.createElement("canvas");
      canvas.className = "text-resize-preview";
      canvas.setAttribute("aria-hidden", "true");
      preview = { box: gesture.box, image, canvas, atlas: new Image(), layout: JSON.parse(gesture.box.dataset.textLayout) };
      preview.ready = () => settlePreview(preview);
      preview.observer = new MutationObserver(preview.ready);
      preview.observer.observe(gesture.box, { attributes: true, attributeFilter: ["data-text-layout"] });
      image.addEventListener("load", preview.ready);
      previews.set(gesture.box, preview);
      gesture.box.appendChild(canvas);
      gesture.box.dataset.textResizing = "true";
      preview.atlas.onload = () => {
        if (previews.get(preview.box) === preview && preview.position) drawPreview(preview);
      };
      preview.atlas.src = preview.layout.atlas;
    }
    preview.position = position;
    drawPreview(preview);
  }

  function drawPreview(preview) {
    const { layout, canvas, position, atlas } = preview;
    const width = Math.max(1, Math.round(layout.canvasWidth * position.width / 100));
    const height = Math.max(1, Math.round(layout.canvasHeight * position.height / 100));
    preview.target = { width, height };
    // Use the same bitmap resolution as the regular preview, independent of screen DPI.
    const scale = layout.previewScale || 1;
    canvas.width = Math.max(1, Math.round(width * scale));
    canvas.height = Math.max(1, Math.round(height * scale));
    const context = canvas.getContext("2d");
    context.setTransform(scale, 0, 0, scale, 0, 0);
    if (!atlas.complete || !atlas.naturalWidth) {
      // Keep the existing glyph pixels at their original size while the atlas decodes.
      context.drawImage(preview.image, 0, 0, layout.width, layout.height);
      return;
    }
    if (!preview.image.alt.trim()) return;
    const padding = Math.min(layout.padding, Math.max(0, Math.floor((width - 1) / 2)));
    context.fillStyle = layout.background;
    context.globalAlpha = Math.round(layout.opacity * 255 / 100) / 255;
    context.beginPath();
    context.roundRect(0, 0, width, height, Math.min(padding, height / 2));
    context.fill();
    context.globalAlpha = 1;
    const lines = wrapText(preview.image.alt, layout, Math.max(1, width - 2 * padding));
    lines.forEach((line, index) => {
      const top = padding + index * layout.lineHeight;
      if (top >= height) return;
      const bounds = textBounds(line, layout);
      const baseline = top - bounds[1];
      const lineWidth = bounds[2] - bounds[0];
      let left = padding - bounds[0], previous = "";
      if (layout.align === "center") left = Math.floor((width - lineWidth) / 2) - bounds[0];
      else if (layout.align === "right") left = width - padding - lineWidth - bounds[0];
      for (const letter of line) {
        const glyph = layout.glyphs[letter];
        left += layout.kerning[previous + letter] || 0;
        if (glyph.inkWidth && glyph.inkHeight) {
          const x = Math.floor(left + glyph.left), y = baseline + glyph.top;
          // Glyph pixels already include Pillow's background/alpha blending. Copy them
          // directly; source-over blending would make antialiased edges look heavier.
          context.save();
          context.beginPath();
          for (const [left, top, width, height] of glyph.clips || [[0, 0, glyph.inkWidth, glyph.inkHeight]]) {
            context.rect(x + left, y + top, width, height);
          }
          context.clip();
          context.globalCompositeOperation = "copy";
          context.drawImage(atlas, glyph.x, glyph.y, glyph.width, glyph.height,
            x, y, glyph.inkWidth, glyph.inkHeight);
          context.restore();
        }
        left += glyph.advance;
        previous = letter;
      }
    });
  }

  controller.signal.addEventListener("abort", () => {
    for (const preview of previews.values()) removePreview(preview);
  });

  document.addEventListener("pointerdown", function (event) {
    const box = event.target.closest("[data-text-id]");
    if (!box || event.button !== 0 || drag) return;
    const stage = box.closest("#crop-stage");
    if (!stage) return;
    const rect = stage.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const boxRect = box.getBoundingClientRect();
    const handle = handleAt(event, box, boxRect);
    event.preventDefault();
    box.setPointerCapture?.(event.pointerId);
    box.style.cursor = cursors[handle];
    drag = {
      box, rect, pointerId: event.pointerId,
      handle,
      startX: event.clientX, startY: event.clientY,
      x: (boxRect.left - rect.left) / rect.width * 100,
      y: (boxRect.top - rect.top) / rect.height * 100,
      width: boxRect.width / rect.width * 100, height: boxRect.height / rect.height * 100,
    };
  }, listenerOptions);

  document.addEventListener("pointermove", function (event) {
    if (!drag) {
      const box = event.target.closest("[data-text-id]");
      if (box) box.style.cursor = cursors[handleAt(event, box)];
      return;
    }
    if (drag.pointerId !== event.pointerId) return;
    const dx = (event.clientX - drag.startX) / drag.rect.width * 100;
    const dy = (event.clientY - drag.startY) / drag.rect.height * 100;
    let { x, y, width, height, handle } = drag;
    if (handle === "move") {
      drag.current = {
        x: Math.max(0, Math.min(100 - width, x + dx)),
        y: Math.max(0, Math.min(100 - height, y + dy)),
      };
    } else {
      // Keep the opposite edge anchored and prevent inverted or off-image boxes.
      if (handle.includes("w")) {
        const right = x + width;
        x = Math.max(0, Math.min(right - 5, x + dx));
        width = right - x;
      }
      if (handle.includes("e")) width = Math.max(5, Math.min(100 - x, width + dx));
      if (handle.includes("n")) {
        const bottom = y + height;
        y = Math.max(0, Math.min(bottom - 3, y + dy));
        height = bottom - y;
      }
      if (handle.includes("s")) height = Math.max(3, Math.min(100 - y, height + dy));
      // Freeze the rendered height on the first resize, including horizontal gestures.
      y = Math.min(y, 97);
      height = Math.max(3, Math.min(100 - y, height));
      drag.current = { x, y, width, height };
      drag.box.style.width = width + "%";
      drag.box.style.height = height + "%";
      resizePreview(drag, drag.current);
    }
    drag.box.style.left = drag.current.x + "%";
    drag.box.style.top = drag.current.y + "%";
  }, listenerOptions);

  function finish(event) {
    if (!drag || drag.pointerId !== event.pointerId) return;
    const completed = drag;
    drag = null;
    if (completed.current) sync(completed.box, completed.current);
    const preview = previews.get(completed.box);
    if (preview) settlePreview(preview);
  }

  document.addEventListener("pointerup", finish, listenerOptions);
  document.addEventListener("pointercancel", finish, listenerOptions);
  document.addEventListener("lostpointercapture", finish, listenerOptions);
})();
