const API_BASE_URL = "http://127.0.0.1:8000";

const eventSelect = document.getElementById("eventSelect");
const eventsList = document.getElementById("eventsList");
const registerForm = document.getElementById("registerForm");
const registerBtn = document.getElementById("registerBtn");
const registerMsg = document.getElementById("registerMsg");
const lookupBtn = document.getElementById("lookupBtn");
const lookupEmail = document.getElementById("lookupEmail");
const regResults = document.getElementById("regResults");

let eventsCache = [];

function showMsg(el, text, type) {
  el.textContent = text;
  el.className = "msg show " + type;
}

function hideMsg(el) {
  el.className = "msg";
}

function statusFromEvent(ev) {
  const remaining = ev.capacity - ev.registeredCount;
  if (remaining <= 0) return { label: "Full", cls: "full" };
  if (remaining <= Math.max(1, Math.floor(ev.capacity * 0.15))) return { label: "Limited", cls: "limited" };
  return { label: "Available", cls: "available" };
}

async function loadEvents() {
  try {
    const res = await fetch(`${API_BASE_URL}/events`);
    if (!res.ok) throw new Error("Failed to load events");
    const data = await res.json();
    eventsCache = data.events || data;
    renderEventsList(eventsCache);
    renderEventSelect(eventsCache);
  } catch (err) {
    eventsList.innerHTML = `<div class="empty">Couldn't load events. Check the API is reachable.</div>`;
    if (eventSelect) eventSelect.innerHTML = `<option value="">Unable to load events</option>`;
    console.error(err);
  }
}

function renderEventsList(events) {
  if (!events.length) {
    eventsList.innerHTML = `<div class="empty">No events scheduled yet.</div>`;
    return;
  }
  eventsList.innerHTML = events.map(ev => {
    const status = statusFromEvent(ev);
    const dateLabel = new Date(ev.date).toLocaleDateString("en-US", { day: "numeric", month: "short", year: "numeric" });
    return `
      <div class="event-row">
        <span class="event-name">${escapeHtml(ev.name)}</span>
        <span class="event-date">${dateLabel}</span>
        <span class="badge ${status.cls}">${status.label}</span>
      </div>`;
  }).join("");
}

function renderEventSelect(events) {
  if (!events.length) {
    if (eventSelect) eventSelect.innerHTML = `<option value="">No events available</option>`;
    return;
  }
  if (eventSelect) {
    eventSelect.innerHTML = `<option value="">Select an event</option>` +
      events.map(ev => {
        const full = (ev.capacity - ev.registeredCount) <= 0;
        return `<option value="${ev.eventId}" ${full ? "disabled" : ""}>${escapeHtml(ev.name)}${full ? " (Full)" : ""}</option>`;
      }).join("");
  }
}

if (registerForm) {
  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideMsg(registerMsg);

    const eventId = eventSelect.value;
    const email = document.getElementById("emailInput").value.trim();

    if (!eventId || !email) {
      showMsg(registerMsg, "Select an event and enter your email.", "error");
      return;
    }

    registerBtn.disabled = true;
    registerBtn.textContent = "Registering…";

    try {
      const res = await fetch(`${API_BASE_URL}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ eventId, email })
      });

      const data = await res.json().catch(() => ({}));

      if (res.status === 409) {
        showMsg(registerMsg, data.error || "You're already registered for this event.", "error");
      } else if (res.status === 400) {
        showMsg(registerMsg, data.error || "Please check your details and try again.", "error");
      } else if (!res.ok) {
        showMsg(registerMsg, data.error || "Registration failed. Please try again.", "error");
      } else {
        showMsg(registerMsg, "You're registered! Check your email for confirmation.", "success");
        registerForm.reset();
        loadEvents();
      }
    } catch (err) {
      showMsg(registerMsg, "Couldn't reach the server. Please try again.", "error");
      console.error(err);
    } finally {
      registerBtn.disabled = false;
      registerBtn.textContent = "Register →";
    }
  });
}

if (lookupBtn) {
  lookupBtn.addEventListener("click", async () => {
    const email = lookupEmail.value.trim();
    if (!email) {
      regResults.innerHTML = `<div class="empty">Enter an email address first.</div>`;
      return;
    }
    regResults.innerHTML = `<div class="loading">Looking up registrations…</div>`;

    try {
      const res = await fetch(`${API_BASE_URL}/registrations/${encodeURIComponent(email)}`);
      if (!res.ok) throw new Error("Lookup failed");
      const data = await res.json();
      const registrations = data.registrations || data;
      renderRegistrations(registrations);
    } catch (err) {
      regResults.innerHTML = `<div class="empty">Couldn't load registrations right now.</div>`;
      console.error(err);
    }
  });
}

function renderRegistrations(registrations) {
  if (!registrations.length) {
    regResults.innerHTML = `<div class="empty">No registrations found for that email.</div>`;
    return;
  }
  regResults.innerHTML = `<div class="events-list">` + registrations.map(reg => `
    <div class="reg-row">
      <span class="reg-info">
        <span class="name">${escapeHtml(reg.eventName || reg.eventId)}</span>
        ${reg.status ? escapeHtml(reg.status) : ""}
      </span>
      <button class="cancel-btn" data-id="${reg.registrationId}">Cancel</button>
    </div>
  `).join("") + `</div>`;

  regResults.querySelectorAll(".cancel-btn").forEach(btn => {
    btn.addEventListener("click", () => cancelRegistration(btn.dataset.id, btn));
  });
}

async function cancelRegistration(id, btn) {
  btn.disabled = true;
  btn.textContent = "Cancelling…";
  try {
    const res = await fetch(`${API_BASE_URL}/registration/${encodeURIComponent(id)}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Cancel failed");
    lookupBtn.click();
    loadEvents();
  } catch (err) {
    btn.disabled = false;
    btn.textContent = "Cancel";
    alert("Couldn't cancel that registration. Please try again.");
    console.error(err);
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

if (document.getElementById("eventSelect") || document.getElementById("lookupBtn")) {
  loadEvents();
}
