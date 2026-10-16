/* Native fullscreen shortcuts for the Tauri and PyWebView desktop shells. */
(() => {
  let changing = false;

  window.addEventListener("keydown", async (event) => {
    if (event.defaultPrevented || event.isComposing || event.altKey ||
        event.ctrlKey || event.metaKey || event.shiftKey ||
        (event.key !== "F11" && event.key !== "Escape")) return;

    const tauri = window.__TAURI_INTERNALS__;
    const preview = window.pywebview?.api;
    if (!tauri?.invoke && !preview?.set_fullscreen) return;

    event.preventDefault();
    if (event.repeat || changing) return;
    changing = true;
    try {
      if (tauri?.invoke) {
        const fullscreen = event.key === "Escape"
          ? false
          : !await tauri.invoke("plugin:window|is_fullscreen");
        await tauri.invoke("plugin:window|set_fullscreen", { value: fullscreen });
      } else {
        await preview.set_fullscreen(event.key === "Escape" ? false : null);
      }
    } catch (error) {
      console.warn("Unable to change desktop fullscreen mode:", error);
    } finally {
      changing = false;
    }
  });
})();
