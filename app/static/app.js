"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const openNotes = new Set();
const prevProgress = new Map();   // task id -> last rendered progress, so bars can grow smoothly
let flash = null;                 // {id, kind} — one-shot animation for the next render
const motionOn = () => document.documentElement.dataset.motion === "on";

// ---------- little celebrations ----------

const YUMS = ["yum!", "served!", "bon appétit", "délicieux!", "chef's kiss"];

function celebrate(anchor) {
  if (!motionOn()) return Promise.resolve();
  const r = anchor.getBoundingClientRect();
  const x = r.left + r.width / 2, y = r.top + r.height / 2;
  for (let i = 0; i < 16; i++) {
    const s = document.createElement("span");
    s.className = "sprinkle";
    const angle = Math.random() * Math.PI * 2, dist = 30 + Math.random() * 45;
    s.style.left = `${x}px`;
    s.style.top = `${y}px`;
    s.style.setProperty("--dx", `${Math.cos(angle) * dist}px`);
    s.style.setProperty("--dy", `${Math.sin(angle) * dist}px`);
    s.style.setProperty("--rot", `${Math.random() * 360}deg`);
    s.addEventListener("animationend", () => s.remove());
    document.body.append(s);
  }
  const yum = document.createElement("span");
  yum.className = "yum";
  yum.textContent = YUMS[Math.floor(Math.random() * YUMS.length)];
  yum.style.left = `${x + 40}px`;
  yum.style.top = `${y - 24}px`;
  yum.addEventListener("animationend", () => yum.remove());
  document.body.append(yum);
  return new Promise(resolve => setTimeout(resolve, 750));
}

// ---------- API ----------

async function api(method, path, body) {
  const res = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try {
      const data = await res.json();
      if (data.detail) msg = typeof data.detail === "string" ? data.detail : data.detail.map(d => d.msg).join("; ");
    } catch { /* keep default message */ }
    throw new Error(msg);
  }
  return res.status === 204 ? null : res.json();
}

async function run(action) {
  try {
    hideError();
    await action();
    await refresh();
  } catch (err) {
    showError(err.message);
  }
}

function showError(msg) { const el = $("#error"); el.textContent = msg; el.hidden = false; }
function hideError() { $("#error").hidden = true; }

// ---------- formatting ----------

function localISODate(d) {
  const pad = n => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function fmtDate(iso) {
  const d = new Date(iso.length === 10 ? iso + "T00:00:00" : iso);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function fmtDateTime(iso) {
  return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

function fmtGroupDate(iso) {
  const d = new Date(iso + "T00:00:00");
  const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1);
  if (iso === localISODate(tomorrow)) return "Tomorrow";
  return d.toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" });
}

// ---------- rendering ----------

function renderTask(task) {
  const li = $("#task-template").content.firstElementChild.cloneNode(true);
  li.dataset.id = task.id;
  li.classList.toggle("done", task.status === "done");

  const check = $(".task-check", li);
  check.checked = task.status === "done";
  check.addEventListener("change", async () => {
    if (check.checked) {
      li.classList.add("serving");
      await celebrate(check);
    }
    run(() => api("PATCH", `/api/tasks/${task.id}`, { progress: check.checked ? 100 : 0 }));
  });

  const star = $(".star", li);
  star.classList.toggle("on", task.important);
  star.setAttribute("aria-pressed", task.important);
  star.addEventListener("click", () => {
    if (!task.important) flash = { id: task.id, kind: "heart" };
    run(() => api("PATCH", `/api/tasks/${task.id}`, { important: !task.important }));
  });

  if (flash && flash.id === task.id) {
    if (flash.kind === "new") li.classList.add("plate-in");
    if (flash.kind === "heart") star.classList.add("pop");
  }

  const title = $(".task-title", li);
  title.textContent = task.title;
  title.addEventListener("dblclick", () => startEditTitle(title, task));

  $(".overdue-tag", li).hidden = !task.overdue;
  if (task.overdue) {
    const planned = $(".planned-tag", li);
    planned.hidden = false;
    planned.textContent = `was for ${fmtDate(task.planned_date)}`;
  }

  $(".delete", li).addEventListener("click", () => {
    if (confirm(`Remove "${task.title}" from the menu?`)) run(() => api("DELETE", `/api/tasks/${task.id}`));
  });

  // progress bar
  const bar = $(".bar", li);
  // grow the bar from its last rendered value to the new one
  const fill = $(".bar-fill", li);
  const before = prevProgress.get(task.id);
  fill.style.width = `${before ?? task.progress}%`;
  if (before !== undefined && before !== task.progress) {
    requestAnimationFrame(() => requestAnimationFrame(() => { fill.style.width = `${task.progress}%`; }));
  }
  prevProgress.set(task.id, task.progress);
  $(".pct", li).textContent = `${task.progress}%`;
  bar.setAttribute("aria-valuenow", task.progress);
  const setProgress = p => run(() => api("PATCH", `/api/tasks/${task.id}`, { progress: p }));
  bar.addEventListener("click", e => {
    const rect = bar.getBoundingClientRect();
    const raw = ((e.clientX - rect.left) / rect.width) * 100;
    setProgress(Math.max(0, Math.min(100, Math.round(raw / 5) * 5)));
  });
  bar.addEventListener("keydown", e => {
    if (e.key === "ArrowRight" || e.key === "ArrowUp") { e.preventDefault(); setProgress(Math.min(100, task.progress + 5)); }
    if (e.key === "ArrowLeft" || e.key === "ArrowDown") { e.preventDefault(); setProgress(Math.max(0, task.progress - 5)); }
  });
  li.querySelectorAll(".quick button").forEach(b =>
    b.addEventListener("click", () => setProgress(Number(b.dataset.p))));

  // meta
  let dates = `ordered ${fmtDate(task.created_at)} · updated ${fmtDateTime(task.updated_at)}`;
  if (task.completed_at) dates += ` · served ${fmtDateTime(task.completed_at)}`;
  $(".dates", li).textContent = dates;

  // notes
  const notesBox = $(".notes", li);
  const toggle = $(".notes-toggle", li);
  const setToggleLabel = () => {
    toggle.textContent = `${notesBox.hidden ? "notes" : "hide notes"} (${task.notes.length})`;
  };
  notesBox.hidden = !openNotes.has(task.id);
  setToggleLabel();
  toggle.addEventListener("click", () => {
    notesBox.hidden = !notesBox.hidden;
    notesBox.hidden ? openNotes.delete(task.id) : openNotes.add(task.id);
    setToggleLabel();
    if (!notesBox.hidden) $(".note-form input", li).focus();
  });

  const noteList = $(".note-list", li);
  for (const note of task.notes) {
    const item = document.createElement("li");
    const time = document.createElement("time");
    time.textContent = fmtDateTime(note.created_at);
    item.append(time, document.createTextNode(note.text));
    noteList.append(item);
  }

  $(".note-form", li).addEventListener("submit", e => {
    e.preventDefault();
    const input = $("input", e.target);
    const text = input.value.trim();
    if (!text) return;
    run(() => api("POST", `/api/tasks/${task.id}/notes`, { text }));
  });

  return li;
}

function startEditTitle(el, task) {
  el.contentEditable = "true";
  el.focus();
  document.getSelection().selectAllChildren(el);
  const finish = save => {
    el.contentEditable = "false";
    el.removeEventListener("keydown", onKey);
    el.removeEventListener("blur", onBlur);
    const value = el.textContent.trim();
    if (save && value && value !== task.title) {
      run(() => api("PATCH", `/api/tasks/${task.id}`, { title: value }));
    } else {
      el.textContent = task.title;
    }
  };
  const onKey = e => {
    if (e.key === "Enter") { e.preventDefault(); finish(true); }
    if (e.key === "Escape") finish(false);
  };
  const onBlur = () => finish(true);
  el.addEventListener("keydown", onKey);
  el.addEventListener("blur", onBlur);
}

function render(data) {
  const today = $("#list-today");
  today.replaceChildren(...data.today.map(renderTask));
  $("#empty-today").hidden = data.today.length > 0;
  $("#count-today").textContent = `(${data.today.length})`;

  const upcoming = $("#list-upcoming");
  const groups = new Map();
  for (const t of data.upcoming) {
    if (!groups.has(t.planned_date)) groups.set(t.planned_date, []);
    groups.get(t.planned_date).push(t);
  }
  upcoming.replaceChildren(...[...groups].map(([day, tasks]) => {
    const wrap = document.createElement("div");
    wrap.className = "date-group";
    const h = document.createElement("h3");
    h.textContent = fmtGroupDate(day);
    const ul = document.createElement("ul");
    ul.className = "task-list";
    ul.append(...tasks.map(renderTask));
    wrap.append(h, ul);
    return wrap;
  }));
  $("#empty-upcoming").hidden = data.upcoming.length > 0;
  $("#count-upcoming").textContent = `(${data.upcoming.length})`;

  $("#list-done").replaceChildren(...data.done.map(renderTask));
  $("#count-done").textContent = `(${data.done.length})`;
  flash = null;
}

async function refresh() {
  render(await api("GET", "/api/tasks"));
}

// ---------- add form ----------

$("#add-tomorrow").addEventListener("click", () => {
  const d = new Date(); d.setDate(d.getDate() + 1);
  $("#add-date").value = localISODate(d);
});

$("#add-form").addEventListener("submit", e => {
  e.preventDefault();
  const title = $("#add-title").value.trim();
  if (!title) return;
  const body = { title, important: $("#add-important").checked };
  if ($("#add-date").value) body.planned_date = $("#add-date").value;
  run(async () => {
    const created = await api("POST", "/api/tasks", body);
    flash = { id: created.id, kind: "new" };
    e.target.reset();
    $("#add-title").focus();
  });
});

// ---------- masthead + ink switch ----------

const now = new Date();
$("#side-day").textContent = now.toLocaleDateString(undefined, { weekday: "long" });
$("#side-date").textContent = now.toLocaleDateString(undefined, { month: "short", day: "numeric" })
  + "\n" + now.getFullYear();

function applyInk(ink) {
  document.documentElement.dataset.ink = ink;
  document.querySelectorAll("[data-ink-choice]").forEach(b =>
    b.setAttribute("aria-pressed", b.dataset.inkChoice === ink));
}
applyInk(document.documentElement.dataset.ink || "tomato");
document.querySelectorAll("[data-ink-choice]").forEach(b =>
  b.addEventListener("click", () => {
    applyInk(b.dataset.inkChoice);
    try { localStorage.setItem("ink", b.dataset.inkChoice); } catch { /* storage unavailable */ }
  }));

const motionToggle = $("#motion-toggle");
function showMotionState() {
  const on = motionOn();
  motionToggle.setAttribute("aria-pressed", on);
  motionToggle.textContent = on ? "✦ animations on" : "✧ animations off";
  motionToggle.title = on ? "Turn animations off" : "Turn animations on";
}
showMotionState();
motionToggle.addEventListener("click", () => {
  const next = motionOn() ? "off" : "on";
  document.documentElement.dataset.motion = next;
  try { localStorage.setItem("motion", next); } catch { /* storage unavailable */ }
  showMotionState();
});

refresh().catch(err => showError(`Could not load tasks: ${err.message}`));
