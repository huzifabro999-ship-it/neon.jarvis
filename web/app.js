const $ = (selector) => document.querySelector(selector);
const messages = $("#messages");
const promptBox = $("#prompt");
let history = [];

function addMessage(role, content, extra = "") {
  const node = document.createElement("div");
  node.className = "message " + role + (extra ? " " + extra : "");
  node.textContent = content;
  messages.appendChild(node);
  messages.scrollTop = messages.scrollHeight;
}

function updateClock() {
  const now = new Date();
  $("#clock").textContent = now.toLocaleTimeString([], { hour12: true });
  $("#date").textContent = now.toLocaleDateString([], { weekday: "short", day: "numeric", month: "short", year: "numeric" });
}
setInterval(updateClock, 1000);
updateClock();

async function refreshHealth() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) throw new Error("Backend unavailable");
    const data = await response.json();
    $("#connection").textContent = "Online | Connected";
    $("#backend-status").textContent = "Online";
    $("#ai-status").textContent = data.ai_configured ? "Groq configured" : "Key required";
  } catch {
    $("#connection").textContent = "Offline";
    $("#backend-status").textContent = "Offline";
  }
}
refreshHealth();

async function loadTasks() {
  const list = $("#task-list");
  try {
    const response = await fetch("/api/tasks");
    const tasks = await response.json();
    list.replaceChildren();
    if (!tasks.length) {
      const empty = document.createElement("li");
      empty.className = "empty";
      empty.textContent = "No tasks yet. Add your first task above.";
      list.appendChild(empty);
      return;
    }
    for (const task of tasks) {
      const item = document.createElement("li");
      if (task.done) item.classList.add("done");
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = task.done;
      checkbox.setAttribute("aria-label", "Mark task complete");
      checkbox.addEventListener("change", async () => {
        await fetch("/api/tasks/" + encodeURIComponent(task.id), {
          method: "PATCH", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ done: checkbox.checked })
        });
        loadTasks();
      });
      const label = document.createElement("label");
      label.textContent = task.title;
      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "Delete";
      remove.addEventListener("click", async () => {
        await fetch("/api/tasks/" + encodeURIComponent(task.id), { method: "DELETE" });
        loadTasks();
      });
      item.append(checkbox, label, remove);
      list.appendChild(item);
    }
  } catch {
    list.textContent = "Could not load tasks. Check the backend connection.";
  }
}
loadTasks();

$("#task-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = $("#task-title");
  const title = input.value.trim();
  if (!title) return;
  const response = await fetch("/api/tasks", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title })
  });
  if (response.ok) { input.value = ""; loadTasks(); }
});

async function sendMessage(text) {
  const content = text.trim();
  if (!content) return;
  addMessage("user", content);
  history.push({ role: "user", content });
  promptBox.value = "";
  $("#send").disabled = true;
  const waiting = document.createElement("div");
  waiting.className = "message assistant";
  waiting.textContent = "Processing your request...";
  messages.appendChild(waiting);
  try {
    const response = await fetch("/api/chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: history.slice(-20) })
    });
    const data = await response.json();
    waiting.remove();
    if (!response.ok) throw new Error(data.detail || "Request failed");
    history.push({ role: "assistant", content: data.reply });
    addMessage("assistant", data.reply);
  } catch (error) {
    waiting.remove();
    addMessage("assistant", error.message, "error");
    history.pop();
  } finally {
    $("#send").disabled = false;
    promptBox.focus();
  }
}

$("#chat-form").addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage(promptBox.value);
});
promptBox.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    $("#chat-form").requestSubmit();
  }
});
document.querySelectorAll("[data-command]").forEach((button) => {
  button.addEventListener("click", () => sendMessage(button.dataset.command));
});
$("#focus-input").addEventListener("click", () => promptBox.focus());
$("#clear-chat").addEventListener("click", () => {
  history = [];
  messages.replaceChildren();
  addMessage("assistant", "Conversation cleared. How may I help?");
});
