import { projects, profile } from './portfolio-data.js';
import { createScene } from './orbit-scene.js';

const $ = selector => document.querySelector(selector);
const reducedQuery = matchMedia('(prefers-reduced-motion: reduce)');
let reduced = reducedQuery.matches;
let scene;
let selectedProject = -1;
let returnFocus;
let framePending = false;
const canvas = $('#spatial-canvas');
const dialog = $('#project-dialog');
const chapters = [...document.querySelectorAll('.chapter')];
const motionButton = $('#motion-toggle');

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function renderProjects(filter = 'all') {
  const grid = $('#project-grid');
  const visible = projects.filter(project => filter === 'all' || project.category === filter);
  grid.replaceChildren();
  visible.forEach(project => {
    const index = projects.indexOf(project);
    const card = node('button', 'project-card js-reveal');
    card.type = 'button';
    card.dataset.project = String(index);
    card.style.setProperty('--project-color', project.color);
    card.setAttribute('aria-haspopup', 'dialog');
    card.setAttribute('aria-label', `${project.title} 실제 결과와 설명 열기`);
    const topline = node('span', 'project-topline');
    topline.append(node('span', 'project-number', project.number), node('span', 'project-category', project.tagline));
    const visual = node('span', 'project-thumb');
    const image = node('img');
    image.src = project.image;
    image.alt = project.imageAlt;
    image.loading = 'lazy';
    image.decoding = 'async';
    visual.append(image, node('span', 'project-visual-label', project.title.toUpperCase()));
    const label = node('span', 'project-label');
    label.append(node('h3', '', project.title), node('span', 'project-arrow', '↗'));
    card.append(topline, visual, label, node('span', 'project-summary', project.summary));
    card.addEventListener('click', () => openProject(index, card));
    card.addEventListener('pointermove', event => {
      if (reduced || event.pointerType === 'touch') return;
      const rect = card.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width - .5;
      const y = (event.clientY - rect.top) / rect.height - .5;
      card.style.setProperty('--tilt-x', `${-y * 4}deg`);
      card.style.setProperty('--tilt-y', `${x * 4}deg`);
    });
    card.addEventListener('pointerleave', () => {card.style.setProperty('--tilt-x', '0deg');card.style.setProperty('--tilt-y', '0deg');});
    grid.append(card);
  });
  $('#filter-status').textContent = `${visible.length}개 프로젝트를 표시합니다.`;
  observeReveals();
}

function openProject(index, trigger) {
  const project = projects[index];
  if (!project) return;
  selectedProject = index;
  returnFocus = trigger || document.activeElement;
  $('#dialog-title').textContent = project.title;
  $('#dialog-kicker').textContent = `${project.number} / ${project.tagline} / ${project.year}`;
  $('#dialog-summary').textContent = project.summary;
  $('#dialog-result').textContent = project.result;
  $('#dialog-scope').textContent = project.scope;
  $('#dialog-image').src = project.image;
  $('#dialog-image').alt = project.imageAlt;
  $('#dialog-report').href = project.report;
  $('#dialog-source').href = project.source;
  $('#dialog-metrics').replaceChildren(...project.metrics.map(metric => {
    const item = node('div');
    item.append(node('strong', '', metric.value), node('small', '', metric.label));
    return item;
  }));
  scene?.setActive(index);
  document.body.classList.add('modal-open');
  if (!dialog.open) dialog.showModal();
  $('.dialog-close').focus();
}

function closeProject() { if (dialog.open) dialog.close(); }
dialog.querySelector('.dialog-close').addEventListener('click', closeProject);
dialog.addEventListener('click', event => {
  if (event.target !== dialog) return;
  const rect = dialog.getBoundingClientRect();
  if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) closeProject();
});
dialog.addEventListener('close', () => {
  document.body.classList.remove('modal-open');
  selectedProject = -1;
  scene?.setActive(-1);
  if (returnFocus instanceof HTMLElement && returnFocus.isConnected) returnFocus.focus({preventScroll:true});
});

function renderProfile() {
  $('#interest-list').replaceChildren(...profile.interests.map((interest, index) => {
    const article = node('article', 'js-reveal');
    article.append(node('span', 'interest-index', `0${index + 1}`), node('h3', '', interest.title), node('p', '', interest.description));
    return article;
  }));
  $('#principle-grid').replaceChildren(...profile.principles.map((principle, index) => {
    const article = node('article', 'js-reveal');
    article.append(node('span', 'principle-index', `PRINCIPLE 0${index + 1}`), node('h3', '', principle.title), node('p', '', principle.description));
    if (principle.proof) {
      const link = node('a', '', '근거 기록 보기 ↗');
      link.href = principle.proof;
      article.append(link);
    }
    return article;
  }));
}

let revealObserver;
function observeReveals() {
  if (!revealObserver) revealObserver = new IntersectionObserver(entries => {
    entries.forEach(entry => {if (entry.isIntersecting) {entry.target.classList.add('is-visible');revealObserver.unobserve(entry.target);}});
  }, {threshold:.08});
  document.querySelectorAll('.js-reveal:not(.is-visible)').forEach(element => {
    if (reduced) element.classList.add('is-visible');
    else revealObserver.observe(element);
  });
}

function updateScroll() {
  framePending = false;
  const scrollMax = document.documentElement.scrollHeight - innerHeight;
  const progress = Math.max(0, Math.min(1, scrollY / Math.max(1, scrollMax)));
  $('#progress-fill').style.transform = `scaleX(${progress})`;
  // Match camera destinations to the visible chapters rather than the total page length.
  const sectionPositions = chapters.map(chapter => chapter.getBoundingClientRect().top + scrollY);
  const orbit = $('#orbit-stage');
  const orbitPosition = orbit.getBoundingClientRect().top + scrollY;
  const positions = [sectionPositions[0], sectionPositions[1] - 100, orbitPosition - 100, sectionPositions[2], sectionPositions[3], Math.max(scrollMax, sectionPositions[3] + 1)];
  const cameraStops = [0, .27, .60, .72, .88, 1];
  let section = 0;
  while (section < positions.length - 2 && scrollY > positions[section + 1]) section++;
  const sectionMix = Math.max(0, Math.min(1, (scrollY - positions[section]) / Math.max(1, positions[section + 1] - positions[section])));
  scene?.setProgress(cameraStops[section] + (cameraStops[section + 1] - cameraStops[section]) * sectionMix);
  const target = [...chapters].reverse().find(chapter => chapter.getBoundingClientRect().top < innerHeight * .48) || chapters[0];
  document.body.dataset.chapter = target.id;
  document.querySelectorAll('.chapter-nav a').forEach(link => {
    const active = link.hash === `#${target.id}`;
    link.classList.toggle('active', active);
    if (active) link.setAttribute('aria-current', 'location');
    else link.removeAttribute('aria-current');
  });
}
addEventListener('scroll', () => {if (!framePending) {framePending=true;requestAnimationFrame(updateScroll);}}, {passive:true});

function setReduced(value) {
  reduced = value;
  document.documentElement.classList.toggle('reduced-motion', value);
  motionButton.setAttribute('aria-pressed', String(value));
  motionButton.textContent = value ? '모션 OFF' : '모션 ON';
  motionButton.setAttribute('aria-label', value ? '움직임 켜기' : '움직임 줄이기');
  scene?.setReducedMotion(value);
  observeReveals();
}
motionButton.addEventListener('click', () => setReduced(!reduced));
reducedQuery.addEventListener('change', event => setReduced(event.matches));

const menu = $('#mobile-menu');
const menuButton = $('#menu-toggle');
function setMenu(open) {
  menu.hidden = !open;
  menuButton.setAttribute('aria-expanded', String(open));
  menuButton.setAttribute('aria-label', open ? '메뉴 닫기' : '메뉴 열기');
}
menuButton.addEventListener('click', () => setMenu(menu.hidden));
menu.querySelectorAll('a').forEach(link => link.addEventListener('click', () => setMenu(false)));
addEventListener('keydown', event => {if (event.key==='Escape') setMenu(false);});

document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('[data-filter]').forEach(other => {
    other.classList.toggle('active', other === button);
    other.setAttribute('aria-pressed', String(other === button));
  });
  renderProjects(button.dataset.filter);
}));

$('#enter-work').addEventListener('click', () => {
  if (reduced) return;
  document.body.classList.add('entering-space');
  setTimeout(() => document.body.classList.remove('entering-space'), 1000);
});

renderProfile();
renderProjects();
setReduced(reduced);
updateScroll();
const legacyAnchors = {experiments:'work',destinations:'work',principles:'about',scope:'about',top:'home'};
if (legacyAnchors[location.hash.slice(1)]) location.hash = legacyAnchors[location.hash.slice(1)];
if (!location.hash && /(?:about|dashboard)\.html$/.test(location.pathname)) {
  location.hash = location.pathname.endsWith('about.html') ? 'about' : 'work';
}
function initScene() {return createScene(canvas, {onSelect: index => openProject(index, $(`[data-project="${index}"]`)), reducedMotion:reduced, onUnavailable:showFallback}).then(controller => {
  scene = controller;
  if (controller && !document.documentElement.classList.contains('scene-unavailable')) {document.documentElement.classList.add('scene-ready');$('.loading-status').hidden = true;updateScroll();}
  else showFallback();
}).catch(showFallback);}
initScene();
function showFallback() {
  document.documentElement.classList.add('scene-unavailable');
  $('.loading-status').hidden = true;
  $('.scene-note').hidden = false;
}
addEventListener('pagehide', () => {scene?.dispose();scene=null;revealObserver?.disconnect();});
addEventListener('pageshow', event => {if (event.persisted) {initScene();observeReveals();}});
