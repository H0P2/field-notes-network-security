"use strict";

const motionButton = document.getElementById("motion-toggle");
const systemMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const smallScreen = window.matchMedia("(max-width: 760px)");
const entrance = document.querySelector(".hero-band");
const phaseLabel = document.querySelector(".scene-phase");
const depthCards = [...document.querySelectorAll(".project-card, .principle-card")];
let reduceMotion = false;
let pendingFrame = false;
try { reduceMotion = localStorage.getItem("field-notes-reduce-motion") === "true"; } catch (_) { /* Storage can be unavailable in private browsing. */ }

function renderScene() {
  pendingFrame = false;
  if (!entrance) return;
  const disabled = reduceMotion || systemMotion.matches || smallScreen.matches;
  const distance = Math.max(1, entrance.offsetHeight - entrance.querySelector(".hero-stage").offsetHeight);
  const progress = disabled ? 0 : Math.min(1, Math.max(0, -entrance.getBoundingClientRect().top / distance));
  entrance.style.setProperty("--camera-y", `${-22 + progress * 44}deg`);
  entrance.style.setProperty("--camera-x", `${-7 + progress * 12}deg`);
  entrance.style.setProperty("--camera-z", `${progress * 120}px`);
  entrance.style.setProperty("--operator-turn", `${-18 + progress * 38}deg`);
  entrance.style.setProperty("--operator-rise", `${progress * -46}px`);
  entrance.style.setProperty("--operator-shift", `${progress * -32}px`);
  entrance.style.setProperty("--orbit-turn", `${progress * 160}deg`);
  // Position-based motion reverses naturally when scrolling upward.
  const height = window.innerHeight;
  depthCards.forEach((card) => {
    const rect = card.getBoundingClientRect();
    const offset = disabled ? 0 : Math.max(-1, Math.min(1, (rect.top + rect.height / 2 - height / 2) / height));
    card.style.setProperty("--card-depth-angle", `${offset * 5}deg`);
    card.style.setProperty("--card-depth-shift", `${offset * 16}px`);
  });
  entrance.style.setProperty("--progress", `${progress * 100}%`);
  if (phaseLabel) phaseLabel.textContent = disabled ? "연구실 / 고정 화면" : ["01 / 연구실에 들어서다", "02 / 흐름을 관찰하다", "03 / 근거를 확인하다"][Math.min(2, Math.floor(progress * 3))];
}
function scheduleScene() {
  if (!pendingFrame) { pendingFrame = true; requestAnimationFrame(renderScene); }
}
function applyMotionPreference() {
  const reduced = reduceMotion || systemMotion.matches;
  document.documentElement.dataset.motion = reduced ? "off" : "on";
  if (motionButton) {
    motionButton.hidden = false;
    motionButton.disabled = systemMotion.matches;
    motionButton.setAttribute("aria-pressed", String(reduced));
    motionButton.textContent = systemMotion.matches ? "시스템: 움직임 줄임" : reduced ? "움직임 줄임" : "움직임 줄이기";
  }
  scheduleScene();
}
motionButton?.addEventListener("click", () => {
  reduceMotion = !reduceMotion;
  try { localStorage.setItem("field-notes-reduce-motion", String(reduceMotion)); } catch (_) { /* Preference still works for this page. */ }
  applyMotionPreference();
});
systemMotion.addEventListener("change", applyMotionPreference);
smallScreen.addEventListener("change", scheduleScene);
window.addEventListener("scroll", scheduleScene, { passive: true });
window.addEventListener("resize", scheduleScene);
applyMotionPreference();

document.querySelectorAll(".evidence-toggle").forEach((button) => {
  const panelId = button.getAttribute("aria-controls");
  const panel = panelId ? document.getElementById(panelId) : null;
  if (!panel) return;

  panel.hidden = true;
  button.hidden = false;
  button.addEventListener("click", () => {
    const isExpanded = button.getAttribute("aria-expanded") === "true";
    button.setAttribute("aria-expanded", String(!isExpanded));
    panel.hidden = isExpanded;
    button.textContent = isExpanded ? "근거 보기" : "근거 닫기";
  });
});

const imageDialog = document.getElementById("project-image-dialog");
const previewImage = imageDialog?.querySelector(".image-dialog-preview");
const previewCaption = imageDialog?.querySelector(".image-dialog-caption");
const closeImageButton = imageDialog?.querySelector(".image-dialog-close");
let imageDialogOpener = null;

if (imageDialog && previewImage && previewCaption && closeImageButton && typeof imageDialog.showModal === "function") {
  document.querySelectorAll(".project-image-link").forEach((link) => {
    link.addEventListener("click", (event) => {
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

      const sourceImage = link.querySelector("img");
      if (!sourceImage) return;

      event.preventDefault();
      imageDialogOpener = link;
      previewImage.src = link.href;
      previewImage.alt = sourceImage.alt;
      previewCaption.textContent = link.closest("figure")?.querySelector("figcaption")?.textContent.trim() ?? "프로젝트 결과 이미지";
      imageDialog.showModal();
    });
  });

  closeImageButton.addEventListener("click", () => imageDialog.close());
  imageDialog.addEventListener("click", (event) => {
    if (event.target === imageDialog) imageDialog.close();
  });
  imageDialog.addEventListener("close", () => {
    previewImage.removeAttribute("src");
    previewImage.alt = "";
    previewCaption.textContent = "";
    if (imageDialogOpener?.isConnected) imageDialogOpener.focus({ preventScroll: true });
    imageDialogOpener = null;
  });
}
