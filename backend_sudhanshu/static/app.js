const taskForm = document.querySelector("#task-form");
const taskIdInput = document.querySelector("#task-id");
const titleInput = document.querySelector("#title");
const descriptionInput = document.querySelector("#description");
const taskList = document.querySelector("#task-list");
const emptyState = document.querySelector("#empty-state");
const formTitle = document.querySelector("#form-title");
const cancelEditButton = document.querySelector("#cancel-edit");
const refreshButton = document.querySelector("#refresh");
const totalCount = document.querySelector("#total-count");
const openCount = document.querySelector("#open-count");
const doneCount = document.querySelector("#done-count");

let tasks = [];

function refreshIcons() {
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

function resetForm() {
  taskForm.reset();
  taskIdInput.value = "";
  formTitle.textContent = "New Task";
  cancelEditButton.hidden = true;
  titleInput.focus();
}

function formatDate(value) {
  return new Date(value).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function renderTasks() {
  const done = tasks.filter((task) => task.completed).length;
  totalCount.textContent = tasks.length;
  openCount.textContent = tasks.length - done;
  doneCount.textContent = done;

  emptyState.hidden = tasks.length > 0;
  taskList.innerHTML = "";

  tasks.forEach((task) => {
    const item = document.createElement("article");
    item.className = `task-item${task.completed ? " done" : ""}`;

    item.innerHTML = `
      <input class="task-check" type="checkbox" ${task.completed ? "checked" : ""} aria-label="Mark complete">
      <div>
        <p class="task-title">${escapeHtml(task.title)}</p>
        <p class="task-desc">${escapeHtml(task.description || "No description")}</p>
        <p class="task-date">Created ${formatDate(task.created_at)}</p>
      </div>
      <div class="task-actions">
        <button class="small-button edit-button" type="button" aria-label="Edit task">
          <i data-lucide="pencil"></i>
        </button>
        <button class="small-button danger delete-button" type="button" aria-label="Delete task">
          <i data-lucide="trash-2"></i>
        </button>
      </div>
    `;

    item.querySelector(".task-check").addEventListener("change", (event) => {
      updateTask(task.id, { completed: event.target.checked });
    });

    item.querySelector(".edit-button").addEventListener("click", () => {
      taskIdInput.value = task.id;
      titleInput.value = task.title;
      descriptionInput.value = task.description || "";
      formTitle.textContent = "Edit Task";
      cancelEditButton.hidden = false;
      titleInput.focus();
    });

    item.querySelector(".delete-button").addEventListener("click", () => {
      deleteTask(task.id);
    });

    taskList.appendChild(item);
  });

  refreshIcons();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function loadTasks() {
  const response = await fetch("/tasks");
  tasks = await response.json();
  renderTasks();
}

async function createTask(payload) {
  await fetch("/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await loadTasks();
  resetForm();
}

async function updateTask(id, payload) {
  await fetch(`/tasks/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await loadTasks();
}

async function deleteTask(id) {
  await fetch(`/tasks/${id}`, { method: "DELETE" });
  await loadTasks();
  if (taskIdInput.value === String(id)) {
    resetForm();
  }
}

taskForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const payload = {
    title: titleInput.value.trim(),
    description: descriptionInput.value.trim() || null,
  };

  if (!payload.title) {
    titleInput.focus();
    return;
  }

  if (taskIdInput.value) {
    await updateTask(taskIdInput.value, payload);
    resetForm();
    return;
  }

  await createTask(payload);
});

cancelEditButton.addEventListener("click", resetForm);
refreshButton.addEventListener("click", loadTasks);

loadTasks();
refreshIcons();
