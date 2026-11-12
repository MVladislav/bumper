/**
 * Add a larger view to every Mermaid diagram.
 *
 * Zensical renders a diagram into a closed shadow root, so the rendered SVG
 * cannot be reused. The source is captured before Zensical replaces the
 * <pre class="mermaid"> block, then rendered again into a native <dialog> at
 * the width of the page. Native <dialog> keeps focus handling and Escape for
 * free, and the diagram follows the active palette because it is rendered by
 * the same Mermaid instance the page already uses.
 */
(() => {
  "use strict";

  const sources = [];
  let sourcePath = null;
  let dialog = null;
  let dialogBody = null;
  let timer;
  let sequence = 0;
  let current = null;

  function captureSources() {
    const blocks = [...document.querySelectorAll("pre.mermaid")];
    if (!blocks.length) return;

    // A diagram is a <pre> until Zensical renders it and a host after, so the
    // two counts together name the set the sources belong to.
    const count =
      blocks.length + document.querySelectorAll("div.mermaid").length;
    if (window.location.pathname === sourcePath && sources.length === count) {
      return;
    }

    sources.length = 0;
    for (const block of blocks) {
      sources.push(block.textContent.trim());
    }
    sourcePath = window.location.pathname;
  }

  function buildDialog() {
    if (dialog) return dialog;

    dialog = document.createElement("dialog");
    dialog.className = "mermaid-zoom-dialog";
    dialog.setAttribute("aria-label", "Diagram in a larger view");

    const bar = document.createElement("div");
    bar.className = "mermaid-zoom-bar";

    const title = document.createElement("span");
    title.className = "mermaid-zoom-title";
    title.textContent = "Diagram";

    const close = document.createElement("button");
    close.type = "button";
    close.className = "mermaid-zoom-close";
    close.title = "Close";
    close.setAttribute("aria-label", "Close");
    close.textContent = "\u00d7";
    close.addEventListener("click", () => dialog.close());

    bar.append(title, close);

    dialogBody = document.createElement("div");
    dialogBody.className = "mermaid-zoom-body";

    dialog.append(bar, dialogBody);
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close();
    });
    document.body.appendChild(dialog);

    return dialog;
  }

  async function openDialog(source) {
    if (typeof mermaid === "undefined") return;

    const element = buildDialog();
    dialogBody.replaceChildren();
    current = null;
    element.showModal();

    const id = `mermaid-zoom-${(sequence += 1)}`;
    try {
      const { svg, bindFunctions } = await mermaid.render(id, source);
      dialogBody.innerHTML = svg;

      const rendered = dialogBody.querySelector("svg");
      if (rendered) {
        rendered.removeAttribute("width");
        rendered.removeAttribute("height");
        rendered.removeAttribute("style");
        current = rendered;
        fitDiagram();
      }
      bindFunctions?.(dialogBody);
    } catch (error) {
      dialogBody.textContent = "The diagram could not be rendered.";
      console.error("Mermaid larger view:", error);
    } finally {
      document.getElementById(`d${id}`)?.remove();
    }
  }

  /**
   * Size a diagram from its viewBox so it fills the dialog without being
   * distorted. A narrow screen is the exception: filling it would make the
   * diagram no larger than the card it came from, so it keeps its own width and
   * the dialog scrolls instead.
   */
  function fitDiagram() {
    const box = current?.viewBox?.baseVal;
    if (!box?.width || !box?.height || !dialogBody) return;

    const ratio = box.width / box.height;
    const style = getComputedStyle(dialogBody);
    const available =
      dialogBody.clientWidth -
      parseFloat(style.paddingLeft) -
      parseFloat(style.paddingRight);
    const availableHeight =
      dialogBody.clientHeight -
      parseFloat(style.paddingTop) -
      parseFloat(style.paddingBottom);

    const narrow = window.matchMedia("(max-width: 44rem)").matches;
    const width = narrow
      ? box.width
      : Math.min(available, availableHeight * ratio);

    current.style.width = `${Math.round(width)}px`;
    current.style.height = `${Math.round(width / ratio)}px`;
  }

  function attachButton(host) {
    if (host.dataset.zoomAttached === "true") return;

    const hostIndex = [...document.querySelectorAll("div.mermaid")].indexOf(
      host,
    );
    const source = sources[hostIndex];
    if (!source) return;

    host.dataset.zoomAttached = "true";

    const wrapper = document.createElement("div");
    wrapper.className = "mermaid-zoom-wrapper";
    host.parentNode.insertBefore(wrapper, host);
    wrapper.appendChild(host);

    const button = document.createElement("button");
    button.type = "button";
    button.className = "mermaid-zoom-button";
    button.title = "Open diagram in a larger view";
    button.setAttribute("aria-label", "Open diagram in a larger view");
    button.innerHTML =
      '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 3H3v6M15 3h6v6M9 21H3v-6M21 15v6h-6"/></svg>';
    button.addEventListener("click", () => openDialog(source));

    wrapper.appendChild(button);
  }

  function attachButtons() {
    if (window.location.pathname !== sourcePath) return;

    for (const host of document.querySelectorAll("div.mermaid")) {
      attachButton(host);
    }
  }

  function sync() {
    captureSources();
    attachButtons();
  }

  function scheduleSync() {
    clearTimeout(timer);
    timer = setTimeout(sync, 150);
  }

  // A diagram appears after Mermaid has rendered it, which is after the first
  // mutation. The source has to be read at once, because Zensical replaces the
  // <pre> with the rendered host in the same beat; only the attach is deferred,
  // so a burst of mutations costs one pass.
  new MutationObserver(() => {
    captureSources();
    scheduleSync();
  }).observe(document.documentElement, {
    childList: true,
    subtree: true,
  });

  // Instant navigation replaces the page content without reloading the script.
  if (window.document$) {
    window.document$.subscribe(() => {
      if (dialog?.open) dialog.close();
      captureSources();
      scheduleSync();
    });
  }

  sync();
  window.addEventListener("load", scheduleSync, { once: true });
  window.addEventListener("resize", () => {
    if (dialog?.open) fitDiagram();
  });
})();
