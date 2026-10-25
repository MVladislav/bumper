let openPanel = null;

function showToast(message, type = "info") {
  const toastContainer = document.getElementById("toast-container");

  // Create the toast element
  const toast = document.createElement("div");
  toast.className = `toast align-items-center text-bg-${type} border-0 show`;
  toast.style.animation = "fadeInOut 3s ease-in-out";
  toast.setAttribute("role", "alert");
  toast.setAttribute("aria-live", "assertive");
  toast.setAttribute("aria-atomic", "true");

  // Add the toast content
  toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" onclick="this.closest('.toast').remove()" aria-label="Close"></button>
        </div>
    `;

  // Append the toast to the container
  toastContainer.appendChild(toast);

  // Automatically remove the toast after 3 seconds
  setTimeout(() => {
    toast.remove();
  }, 3000);
}

function restartService(service) {
  console.log("restart service", service);
  fetch("restart_" + service)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`Failed to restart ${service}: ${response.statusText}`);
      }
      return response.json();
    })
    .then((data) => {
      showToast(
        `Restarting ${service}: ${data.status}`,
        data.status === "complete" ? "success" : "danger",
      );
      console.log(`restart ${service} - ${data.status}`);
    })
    .catch((error) => {
      showToast(error.message, "danger");
      console.error(error);
    });
}

function renameEntity(el) {
  const { type, id, name, value } = el.dataset;
  closeMenu();
  const nickname = window.prompt(`New name for ${name || id}`, value || "");
  if (!nickname || nickname === value) {
    return;
  }
  console.log(`rename ${type}`, id, nickname);
  fetch(`${type}/nickname/${id}?nickname=${encodeURIComponent(nickname)}`)
    .then((response) => {
      if (!response.ok) {
        throw new Error(
          `Failed to rename ${type} - ${id}: ${response.statusText}`,
        );
      }
      return response.json();
    })
    .then((data) => {
      showToast(
        `Renaming ${type} - ${id} - ${data.status}`,
        data.status.includes("success") ? "success" : "danger",
      );
      htmx.trigger(el, "entity-renamed");
      console.log(`rename ${type}`, id, data.status);
    })
    .catch((error) => {
      showToast(error.message, "danger");
      console.error(error);
    });
}

function removeEntity(el) {
  const { type, id, name } = el.dataset;
  closeMenu();
  if (!window.confirm(`Remove ${name || id}?`)) {
    return;
  }
  console.log(`remove ${type}`, id);
  fetch(`${type}/remove/${id}`)
    .then((response) => {
      if (!response.ok) {
        throw new Error(
          `Failed to remove ${type} - ${id}: ${response.statusText}`,
        );
      }
      return response.json();
    })
    .then((data) => {
      showToast(
        `Removing ${type} - ${id} - ${data.status}`,
        data.status.includes("success") ? "success" : "danger",
      );
      htmx.trigger(el, "entity-removed");
      console.log(`remove ${type}`, id, data.status);
    })
    .catch((error) => {
      showToast(error.message, "danger");
      console.error(error);
    });
}

// The map of a job is shown over the page, in full.
function showMap(el) {
  const viewer = document.getElementById("map-viewer");
  const image = document.getElementById("map-viewer-image");
  if (!viewer || !image) {
    return;
  }
  const source = el.dataset.src;
  const name = el.dataset.name || "Map";
  image.src = source;
  image.alt = name;

  const title = document.getElementById("map-viewer-title");
  if (title) {
    title.textContent = name;
  }
  const open = document.getElementById("map-viewer-open");
  if (open) {
    open.href = source;
  }
  const download = document.getElementById("map-viewer-download");
  if (download) {
    download.href = source;
    download.download = `${name.replace(/[^a-z0-9._-]+/gi, "-")}.svg`;
  }

  if (!viewer.open) {
    viewer.showModal();
  }
}

// The panel of a menu is placed next to the icon that opened it.
function placeMenu(menu) {
  const panel = menu.querySelector(".menu-panel");
  const icon = menu.querySelector("summary");
  if (!panel || !icon) {
    return;
  }
  if (panel.parentElement !== document.body) {
    document.body.appendChild(panel);
  }
  openPanel = panel;

  const anchor = icon.getBoundingClientRect();
  const box = panel.getBoundingClientRect();
  const gap = 4;
  const edge = 8;

  let top = anchor.bottom + gap;
  if (top + box.height > window.innerHeight - edge) {
    top = anchor.top - box.height - gap;
  }
  top = Math.min(Math.max(edge, top), window.innerHeight - box.height - edge);

  const left = Math.min(
    Math.max(edge, anchor.right - box.width),
    window.innerWidth - box.width - edge,
  );

  panel.style.top = `${top}px`;
  panel.style.left = `${left}px`;
  panel.style.visibility = "visible";
}

// A menu that closes puts its panel back where it belongs.
function hideMenu(menu) {
  const panel = openPanel || menu.querySelector(".menu-panel");
  if (!panel) {
    return;
  }
  panel.style.visibility = "hidden";
  if (panel.parentElement === document.body) {
    menu.appendChild(panel);
  }
  openPanel = null;
}

// Every open menu is closed.
function closeMenu() {
  document.querySelectorAll("details.menu[open]").forEach((menu) => {
    menu.removeAttribute("open");
  });
}

// A menu of the actions of a row closes when the click lands outside of it.
document.addEventListener("click", (event) => {
  document.querySelectorAll("details.menu[open]").forEach((menu) => {
    if (!menu.contains(event.target)) {
      menu.removeAttribute("open");
    }
  });
});

// The menu of a row is placed when it opens and follows the icon when the page moves.
document.addEventListener(
  "toggle",
  (event) => {
    const menu = event.target;
    if (menu.tagName !== "DETAILS") {
      return;
    }
    if (menu.open) {
      placeMenu(menu);
    } else {
      hideMenu(menu);
    }
  },
  true,
);

document.addEventListener(
  "scroll",
  () => {
    document.querySelectorAll("details.menu[open]").forEach(placeMenu);
  },
  true,
);

// The menu of a row is placed again when the table around it is replaced.
document.addEventListener("htmx:afterSwap", () => {
  document.querySelectorAll("details.menu[open]").forEach(placeMenu);
});
