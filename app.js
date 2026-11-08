const durations = {
  work: 25 * 60,
  short: 5 * 60,
  long: 15 * 60
};

const labels = {
  work: "Focus",
  short: "Short break",
  long: "Long break"
};

const storageKey = "pomodoro-focus-space-v1";
const timerDisplay = document.getElementById("timerDisplay");
const timerStatus = document.getElementById("timerStatus");
const startButton = document.getElementById("startButton");
const resetButton = document.getElementById("resetButton");
const sessionCount = document.getElementById("sessionCount");
const storageNotice = document.getElementById("storageNotice");
const currentTaskTitle = document.getElementById("currentTaskTitle");
const currentTaskProgress = document.getElementById("currentTaskProgress");
const taskFormPanel = document.getElementById("taskFormPanel");
const taskForm = document.getElementById("taskForm");
const taskTitleInput = document.getElementById("taskTitleInput");
const taskNoteInput = document.getElementById("taskNoteInput");
const taskProjectInput = document.getElementById("taskProjectInput");
const taskEstimateInput = document.getElementById("taskEstimateInput");
const projectOptions = document.getElementById("projectOptions");
const projectFilter = document.getElementById("projectFilter");
const taskList = document.getElementById("taskList");
const emptyTasks = document.getElementById("emptyTasks");
const emptyTasksTitle = document.getElementById("emptyTasksTitle");
const emptyTasksHint = document.getElementById("emptyTasksHint");
const taskCount = document.getElementById("taskCount");
const modeButtons = [...document.querySelectorAll(".session-tab")];
const filterButtons = [...document.querySelectorAll(".filter-button")];
const addTaskButton = document.getElementById("addTaskButton");
const cancelTaskButtons = [
  document.getElementById("cancelTaskButton"),
  document.getElementById("cancelTaskButtonSecondary")
];

function showStorageNotice(message) {
  storageNotice.textContent = message;
  storageNotice.hidden = !message;
}

function getSavedState() {
  try {
    const saved = localStorage.getItem(storageKey);
    if (!saved) {
      return {
        tasks: [],
        projects: [],
        totalFocusSessions: 0,
        completedFocusSessions: 0,
        selectedTaskId: null
      };
    }

    const parsed = JSON.parse(saved);
    if (!parsed || typeof parsed !== "object" || !Array.isArray(parsed.tasks)) {
      showStorageNotice("Saved data could not be read. New changes will be saved over it.");
      return {
        tasks: [],
        projects: [],
        totalFocusSessions: 0,
        completedFocusSessions: 0,
        selectedTaskId: null
      };
    }

    const tasks = parsed.tasks
      .filter((task) => task && typeof task.id === "string" && typeof task.title === "string")
      .map((task) => ({
        id: task.id,
        title: task.title.slice(0, 120),
        note: typeof task.note === "string" ? task.note.slice(0, 500) : "",
        project: typeof task.project === "string" ? task.project.slice(0, 60) : "",
        estimate: Number.isInteger(task.estimate) ? Math.min(12, Math.max(1, task.estimate)) : 1,
        pomodoros: Number.isInteger(task.pomodoros) ? Math.max(0, task.pomodoros) : 0,
        completed: task.completed === true
      }));
    const projects = Array.isArray(parsed.projects)
      ? parsed.projects.filter((project) => typeof project === "string").map((project) => project.slice(0, 60))
      : [];
    const selectedTaskId = tasks.some((task) => task.id === parsed.selectedTaskId && !task.completed)
      ? parsed.selectedTaskId
      : null;

    return {
      tasks,
      projects: [...new Set(projects)],
      totalFocusSessions: Number.isInteger(parsed.totalFocusSessions)
        ? Math.max(0, parsed.totalFocusSessions)
        : 0,
      completedFocusSessions: Number.isInteger(parsed.completedFocusSessions)
        ? Math.min(4, Math.max(0, parsed.completedFocusSessions))
        : 0,
      selectedTaskId
    };
  } catch {
    showStorageNotice("Your browser could not read saved data. New changes may not be saved.");
    return {
      tasks: [],
      projects: [],
      totalFocusSessions: 0,
      completedFocusSessions: 0,
      selectedTaskId: null
    };
  }
}

const savedState = getSavedState();
let tasks = savedState.tasks;
let projects = savedState.projects;
let totalFocusSessions = savedState.totalFocusSessions;
let selectedTaskId = savedState.selectedTaskId;
let taskFilter = "active";
let mode = "work";
let remaining = durations[mode];
let deadline = null;
let intervalId = null;
let completedFocusSessions = savedState.completedFocusSessions;

function persist() {
  try {
    localStorage.setItem(storageKey, JSON.stringify({
      tasks,
      projects,
      totalFocusSessions,
      completedFocusSessions,
      selectedTaskId
    }));
    showStorageNotice("");
  } catch {
    showStorageNotice("Could not save your changes. Check your browser's storage settings.");
  }
}

function getSelectedTask() {
  return tasks.find((task) => task.id === selectedTaskId && !task.completed) || null;
}

function renderTime() {
  const minutes = Math.floor(remaining / 60);
  const seconds = remaining % 60;
  const time = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  timerDisplay.textContent = time;
  timerDisplay.setAttribute("aria-label", `${minutes} minutes and ${seconds} seconds remaining`);
  document.title = intervalId ? `${time} - ${labels[mode]} | Pomodoro Timer` : "Pomodoro Timer | Joshua Omamalin";
  startButton.textContent = intervalId ? "Pause" : mode === "work" ? "Start focus" : "Start break";
}

function renderSessions() {
  sessionCount.textContent = `${completedFocusSessions} of 4 focus sessions completed`;
}

function renderCurrentTask() {
  const task = getSelectedTask();
  if (!task) {
    currentTaskTitle.textContent = "Choose a task to begin";
    currentTaskProgress.textContent = "Your next 25 minutes are yours.";
    return;
  }

  currentTaskTitle.textContent = task.title;
  const projectLabel = task.project ? `${task.project} · ` : "";
  currentTaskProgress.textContent = `${projectLabel}${task.pomodoros} of ${task.estimate} pomodoros`;
}

function createButton(text, className, label, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.textContent = text;
  button.setAttribute("aria-label", label);
  button.addEventListener("click", onClick);
  return button;
}

function renderProjects() {
  const names = [...new Set([
    ...projects,
    ...tasks.map((task) => task.project).filter(Boolean)
  ])].sort((a, b) => a.localeCompare(b));
  const selectedProject = projectFilter.value;

  projectOptions.replaceChildren();
  projectFilter.replaceChildren(new Option("All projects", "all"));

  names.forEach((name) => {
    const option = document.createElement("option");
    option.value = name;
    projectOptions.append(option);
    projectFilter.append(new Option(name, name));
  });

  projectFilter.value = names.includes(selectedProject) ? selectedProject : "all";
}

function getVisibleTasks() {
  return tasks.filter((task) => {
    const matchesStatus = taskFilter === "all" ||
      (taskFilter === "completed" ? task.completed : !task.completed);
    const matchesProject = projectFilter.value === "all" || task.project === projectFilter.value;
    return matchesStatus && matchesProject;
  });
}

function renderTasks() {
  renderProjects();
  taskList.replaceChildren();
  const visibleTasks = getVisibleTasks();

  visibleTasks.forEach((task) => {
    const item = document.createElement("li");
    item.className = `task-item${task.id === selectedTaskId ? " is-selected" : ""}${task.completed ? " is-completed" : ""}`;

    const check = createButton(
      task.completed ? "✓" : "",
      "task-check",
      task.completed ? `Mark ${task.title} as not completed` : `Mark ${task.title} as completed`,
      () => toggleTask(task.id)
    );
    check.setAttribute("aria-pressed", String(task.completed));
    item.append(check);

    const copy = document.createElement("div");
    copy.className = "task-copy";
    const title = createButton(
      task.title,
      "task-title",
      task.id === selectedTaskId ? `Selected task: ${task.title}` : `Focus on task: ${task.title}`,
      () => selectTask(task.id)
    );
    title.disabled = task.completed;
    copy.append(title);

    const meta = document.createElement("div");
    meta.className = "task-meta";
    if (task.project) {
      const project = document.createElement("span");
      project.className = "task-project";
      project.textContent = task.project;
      meta.append(project);
    }
    const progress = document.createElement("span");
    progress.textContent = `${task.pomodoros} / ${task.estimate} pomodoros`;
    meta.append(progress);
    copy.append(meta);

    if (task.note) {
      const note = document.createElement("p");
      note.className = "task-note";
      note.textContent = task.note;
      copy.append(note);
    }
    item.append(copy);

    const actions = document.createElement("div");
    actions.className = "task-item-actions";
    if (task.id === selectedTaskId) {
      const selected = document.createElement("span");
      selected.className = "task-estimate";
      selected.textContent = "Selected";
      actions.append(selected);
    }
    actions.append(createButton(
      "Delete",
      "task-action",
      `Delete ${task.title}`,
      () => deleteTask(task.id)
    ));
    item.append(actions);
    taskList.append(item);
  });

  emptyTasks.hidden = visibleTasks.length > 0;
  if (tasks.length === 0) {
    emptyTasksTitle.textContent = "A fresh start.";
    emptyTasksHint.textContent = "Add a task and give your focus somewhere to go.";
  } else if (visibleTasks.length === 0) {
    emptyTasksTitle.textContent = "Nothing here just yet.";
    emptyTasksHint.textContent = "Try another filter or add a new task.";
  }

  const activeCount = tasks.filter((task) => !task.completed).length;
  const taskLabel = activeCount === 1 ? "task left" : "tasks left";
  taskCount.textContent = `${activeCount} ${taskLabel}${projects.length ? ` · ${projects.length} ${projects.length === 1 ? "project" : "projects"}` : ""}`;
  renderCurrentTask();
}

function stopTimer() {
  if (intervalId !== null) {
    globalThis.clearInterval(intervalId);
    intervalId = null;
  }
  deadline = null;
  renderTime();
}

function selectMode(nextMode) {
  if (!Object.hasOwn(durations, nextMode)) return;
  stopTimer();
  mode = nextMode;
  remaining = durations[mode];
  timerStatus.textContent = mode === "work" ? "Ready when you are" : "Take a little breather";
  modeButtons.forEach((button) => {
    const active = button.dataset.mode === mode;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  renderTime();
}

function finishSession() {
  const completedMode = mode;
  stopTimer();
  if (completedMode === "work") {
    completedFocusSessions = Math.min(4, completedFocusSessions + 1);
    totalFocusSessions += 1;
    const task = getSelectedTask();
    if (task) task.pomodoros += 1;
    persist();
    renderSessions();
    renderTasks();
    selectMode(completedFocusSessions === 4 ? "long" : "short");
  } else {
    if (completedMode === "long") {
      completedFocusSessions = 0;
      renderSessions();
      persist();
    }
    selectMode("work");
  }
  timerStatus.textContent = `${labels[completedMode]} session complete. ${labels[mode]} is ready`;
}

function tick() {
  remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
  renderTime();
  if (remaining === 0) finishSession();
}

function startTimer() {
  if (intervalId !== null) {
    stopTimer();
    timerStatus.textContent = "Timer paused";
    return;
  }

  deadline = Date.now() + remaining * 1000;
  timerStatus.textContent = `${labels[mode]} session in progress`;
  intervalId = globalThis.setInterval(tick, 250);
  renderTime();
}

function selectTask(id) {
  const task = tasks.find((item) => item.id === id && !item.completed);
  if (!task) return;
  selectedTaskId = id;
  persist();
  renderTasks();
  timerStatus.textContent = `Ready to focus on ${task.title}`;
}

function toggleTask(id) {
  const task = tasks.find((item) => item.id === id);
  if (!task) return;
  task.completed = !task.completed;
  if (task.completed && selectedTaskId === id) selectedTaskId = null;
  persist();
  renderTasks();
}

function deleteTask(id) {
  const task = tasks.find((item) => item.id === id);
  tasks = tasks.filter((task) => task.id !== id);
  if (task?.project && !tasks.some((item) => item.project === task.project)) {
    projects = projects.filter((project) => project !== task.project);
  }
  if (selectedTaskId === id) selectedTaskId = null;
  persist();
  renderTasks();
}

function closeTaskForm() {
  taskForm.reset();
  taskEstimateInput.value = "1";
  taskFormPanel.hidden = true;
  addTaskButton.setAttribute("aria-expanded", "false");
}

modeButtons.forEach((button) => {
  button.addEventListener("click", () => selectMode(button.dataset.mode));
});

filterButtons.forEach((button) => {
  button.addEventListener("click", () => {
    taskFilter = button.dataset.filter;
    filterButtons.forEach((filterButton) => {
      const active = filterButton === button;
      filterButton.classList.toggle("is-active", active);
      filterButton.setAttribute("aria-pressed", String(active));
    });
    renderTasks();
  });
});

projectFilter.addEventListener("change", renderTasks);
startButton.addEventListener("click", startTimer);
resetButton.addEventListener("click", () => {
  stopTimer();
  remaining = durations[mode];
  timerStatus.textContent = mode === "work" ? "Ready when you are" : "Take a little breather";
  renderTime();
});

addTaskButton.addEventListener("click", () => {
  taskFormPanel.hidden = false;
  addTaskButton.setAttribute("aria-expanded", "true");
  taskTitleInput.focus();
});

cancelTaskButtons.forEach((button) => button.addEventListener("click", closeTaskForm));

taskForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const title = taskTitleInput.value.trim();
  const estimate = Number(taskEstimateInput.value);
  if (!title || !Number.isInteger(estimate) || estimate < 1 || estimate > 12) return;

  const project = taskProjectInput.value.trim();
  if (project && !projects.includes(project)) projects.push(project);
  const task = {
    id: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
    title,
    note: taskNoteInput.value.trim(),
    project,
    estimate,
    pomodoros: 0,
    completed: false
  };

  tasks.unshift(task);
  selectedTaskId = task.id;
  taskFilter = "active";
  projectFilter.value = "all";
  filterButtons.forEach((button) => {
    const active = button.dataset.filter === taskFilter;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  persist();
  renderTasks();
  closeTaskForm();
  timerStatus.textContent = `Ready to focus on ${task.title}`;
});

renderTime();
renderSessions();
renderTasks();
