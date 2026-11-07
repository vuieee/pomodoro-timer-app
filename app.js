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

const timerDisplay = document.getElementById("timerDisplay");
const timerStatus = document.getElementById("timerStatus");
const startButton = document.getElementById("startButton");
const resetButton = document.getElementById("resetButton");
const sessionCount = document.getElementById("sessionCount");
const modeButtons = [...document.querySelectorAll(".session-tab")];

let mode = "work";
let remaining = durations[mode];
let deadline = null;
let intervalId = null;
let completedFocusSessions = 0;

function renderTime() {
  const minutes = Math.floor(remaining / 60);
  const seconds = remaining % 60;
  const time = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  timerDisplay.textContent = time;
  document.title = intervalId ? `${time} - ${labels[mode]} | Pomodoro Timer` : "Pomodoro Timer | Joshua Omamalin";
}

function renderSessions() {
  sessionCount.textContent = `${completedFocusSessions} of 4 focus sessions completed`;
}

function stopTimer() {
  if (intervalId !== null) {
    window.clearInterval(intervalId);
    intervalId = null;
  }
  deadline = null;
  startButton.textContent = "Start";
  renderTime();
}

function selectMode(nextMode) {
  stopTimer();
  mode = nextMode;
  remaining = durations[mode];
  timerStatus.textContent = mode === "work" ? "Ready to focus" : "Ready for a break";
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
    completedFocusSessions += 1;
    renderSessions();
    selectMode(completedFocusSessions === 4 ? "long" : "short");
  } else {
    if (completedMode === "long") {
      completedFocusSessions = 0;
      renderSessions();
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
  startButton.textContent = "Pause";
  timerStatus.textContent = `${labels[mode]} session in progress`;
  intervalId = window.setInterval(tick, 250);
  renderTime();
}

modeButtons.forEach((button) => {
  button.addEventListener("click", () => selectMode(button.dataset.mode));
});

startButton.addEventListener("click", startTimer);
resetButton.addEventListener("click", () => {
  stopTimer();
  remaining = durations[mode];
  timerStatus.textContent = mode === "work" ? "Ready to focus" : "Ready for a break";
  renderTime();
});

renderTime();
renderSessions();
