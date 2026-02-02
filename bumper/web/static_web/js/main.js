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
        data.status === "complete" ? "success" : "danger"
      );
      console.log(`restart ${service} - ${data.status}`);
    })
    .catch((error) => {
      showToast(error.message, "danger");
      console.error(error);
    });
}

function removeEntity(type, id, el) {
  console.log(`remove ${type}`, id);
  fetch(`${type}/remove/${id}`)
    .then((response) => {
      if (!response.ok) {
        throw new Error(
          `Failed to remove ${type} - ${id}: ${response.statusText}`
        );
      }
      return response.json();
    })
    .then((data) => {
      showToast(
        `Removing ${type} - ${id} - ${data.status}`,
        data.status.includes("success") ? "success" : "danger"
      );
      htmx.trigger(el, "entity-removed");
      console.log(`remove ${type}`, id, data.status);
    })
    .catch((error) => {
      showToast(error.message, "danger");
      console.error(error);
    });
}
