const root = document.documentElement;
root.id ||= "site-document";

const scrollbar = document.createElement("div");
const thumb = document.createElement("span");
scrollbar.className = "overlay-scrollbar";
scrollbar.setAttribute("role", "scrollbar");
scrollbar.setAttribute("aria-controls", root.id);
scrollbar.setAttribute("aria-label", "Page scroll position");
scrollbar.setAttribute("aria-orientation", "vertical");
scrollbar.setAttribute("aria-valuemin", "0");
scrollbar.setAttribute("aria-valuemax", "100");
scrollbar.setAttribute("aria-valuenow", "0");
scrollbar.tabIndex = 0;
thumb.className = "overlay-scrollbar-thumb";
scrollbar.append(thumb);
document.body.append(scrollbar);

let trackHeight = 0;
let thumbHeight = 0;
let maxScroll = 0;
let dragStartY = 0;
let dragStartScroll = 0;

function getScrollTop() {
  return globalThis.scrollY || root.scrollTop;
}

function setScrollTop(value) {
  root.scrollTop = value;
  update();
}

function update() {
  const viewportHeight = globalThis.innerHeight;
  const documentHeight = Math.max(root.scrollHeight, document.body.scrollHeight);
  maxScroll = Math.max(0, documentHeight - viewportHeight);

  if (maxScroll === 0 || viewportHeight === 0) {
    scrollbar.hidden = true;
    return;
  }

  scrollbar.hidden = false;
  trackHeight = viewportHeight;
  thumbHeight = Math.min(trackHeight, Math.max(28, trackHeight * viewportHeight / documentHeight));
  const scrollTop = Math.min(maxScroll, getScrollTop());
  const thumbTop = scrollTop / maxScroll * (trackHeight - thumbHeight);
  thumb.style.height = `${thumbHeight}px`;
  thumb.style.transform = `translateY(${thumbTop}px)`;
  scrollbar.setAttribute("aria-valuenow", String(Math.round(scrollTop / maxScroll * 100)));
  scrollbar.setAttribute("aria-valuetext", `${Math.round(scrollTop)} of ${Math.round(maxScroll)} pixels`);
}

function scrollToPointer(clientY) {
  const scrollRange = trackHeight - thumbHeight;
  if (scrollRange <= 0) return;
  const thumbTop = Math.min(scrollRange, Math.max(0, clientY - thumbHeight / 2));
  setScrollTop(thumbTop / scrollRange * maxScroll);
}

scrollbar.addEventListener("pointerdown", (event) => {
  if (scrollbar.hidden || event.button !== 0) return;
  event.preventDefault();
  update();
  scrollbar.focus();
  scrollbar.setPointerCapture(event.pointerId);

  const thumbRect = thumb.getBoundingClientRect();
  if (event.clientY < thumbRect.top || event.clientY > thumbRect.bottom) {
    scrollToPointer(event.clientY);
    return;
  }

  dragStartY = event.clientY;
  dragStartScroll = getScrollTop();
  scrollbar.classList.add("is-dragging");
});

scrollbar.addEventListener("pointermove", (event) => {
  if (!scrollbar.hasPointerCapture(event.pointerId) || !scrollbar.classList.contains("is-dragging")) return;
  const scrollRange = trackHeight - thumbHeight;
  if (scrollRange <= 0) return;
  const startThumbTop = dragStartScroll / maxScroll * scrollRange;
  const thumbTop = Math.min(scrollRange, Math.max(0, startThumbTop + event.clientY - dragStartY));
  setScrollTop(thumbTop / scrollRange * maxScroll);
});

function endDrag(event) {
  if (scrollbar.hasPointerCapture(event.pointerId)) scrollbar.releasePointerCapture(event.pointerId);
  scrollbar.classList.remove("is-dragging");
}

scrollbar.addEventListener("pointerup", endDrag);
scrollbar.addEventListener("pointercancel", endDrag);
scrollbar.addEventListener("keydown", (event) => {
  update();
  const pageStep = globalThis.innerHeight * .9;
  const actions = {
    ArrowDown: () => setScrollTop(getScrollTop() + 40),
    ArrowUp: () => setScrollTop(getScrollTop() - 40),
    PageDown: () => setScrollTop(getScrollTop() + pageStep),
    PageUp: () => setScrollTop(getScrollTop() - pageStep),
    Home: () => setScrollTop(0),
    End: () => setScrollTop(maxScroll)
  };
  const action = actions[event.key];
  if (!action) return;
  event.preventDefault();
  action();
});

globalThis.addEventListener("scroll", update, { passive: true });
globalThis.addEventListener("resize", update);
const resizeObserver = new ResizeObserver(update);
resizeObserver.observe(root);
resizeObserver.observe(document.body);
update();
