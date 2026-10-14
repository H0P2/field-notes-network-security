import * as THREE from 'three';

const PROJECTS = [
  ['FlowLens', '01', 'NETWORK FLOWS', '#cec6b8'],
  ['AuthSentry', '02', 'AUTHENTICATION', '#cec6b8'],
  ['SecretFence', '03', 'SECRET DETECTION', '#cec6b8'],
  ['PublishGate', '04', 'RELEASE INTEGRITY', '#cec6b8'],
  ['SampleScope', '05', 'DATA FORENSICS', '#cec6b8'],
];
const clamp = THREE.MathUtils.clamp;
const smooth = (a, b, v) => { const t = clamp((v - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };

/** Original procedural scene; all graphics and text textures are generated locally. */
export async function createScene(canvas, { onSelect, reducedMotion = false, onUnavailable } = {}) {
  const noop = { setProgress() {}, setReducedMotion() {}, setActive() {}, resize() {}, dispose() {} };
  if (!canvas) return noop;
  let disposed = false, lost = false, hidden = document.hidden, raf = 0, progress = 0;
  let active = -1, width = 1, height = 1, mobile = false, lastFrame = -Infinity;
  let elapsed = 0, previousTime = 0, dragging = false, downPoint = null;
  const pointer = new THREE.Vector2(), smoothedPointer = new THREE.Vector2();
  const fallback = (reason) => {
    canvas.classList.add('scene-unavailable');
    canvas.parentElement?.classList.add('scene-unavailable');
    if (typeof onUnavailable === 'function') onUnavailable(reason);
  };
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, powerPreference: 'low-power' });
  } catch { fallback('webgl-unavailable'); return noop; }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.setClearColor(0x04070c, 0);
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x040911, 0.026);
  const camera = new THREE.PerspectiveCamera(48, 1, 0.045, 100);
  const root = new THREE.Group(); scene.add(root);
  const textures = new Set(), materials = new Set(), geometries = new Set();
  const material = (type, props) => { const m = new type(props); materials.add(m); return m; };
  const geometry = (g) => { geometries.add(g); return g; };
  const mesh = (g, m, parent = root) => { const obj = new THREE.Mesh(geometry(g), m); parent.add(obj); return obj; };
  const lineMat = (color, opacity = 1) => material(THREE.LineBasicMaterial, { color, transparent: true, opacity, depthWrite: false });
  const glowMat = (color, opacity = 1) => material(THREE.MeshBasicMaterial, { color, transparent: true, opacity, blending: THREE.AdditiveBlending, depthWrite: false });
  const wire = (g, color, opacity, parent = root) => {
    const edges = geometry(new THREE.EdgesGeometry(g)); g.dispose();
    const object = new THREE.LineSegments(edges, lineMat(color, opacity)); parent.add(object); return object;
  };
  const glowCanvas = document.createElement('canvas'); glowCanvas.width = glowCanvas.height = 128;
  const gx = glowCanvas.getContext('2d');
  if (gx) {
    const gradient = gx.createRadialGradient(64, 64, 1, 64, 64, 64);
    gradient.addColorStop(0, 'rgba(223,255,252,1)'); gradient.addColorStop(0.15, 'rgba(118,228,255,.75)');
    gradient.addColorStop(0.45, 'rgba(87,130,242,.12)'); gradient.addColorStop(1, 'rgba(50,70,140,0)');
    gx.fillStyle = gradient; gx.fillRect(0, 0, 128, 128);
  }
  const glowTexture = new THREE.CanvasTexture(glowCanvas); textures.add(glowTexture);
  const glow = (size, color, parent, opacity = 0.8) => {
    const object = new THREE.Sprite(material(THREE.SpriteMaterial, { map: glowTexture, color, transparent: true, opacity, blending: THREE.AdditiveBlending, depthWrite: false }));
    object.scale.set(size, size, 1); parent.add(object); return object;
  };
  scene.add(new THREE.HemisphereLight(0xe9e4da, 0x101114, 1.3));
  const key = new THREE.DirectionalLight(0xfff1dd, 5); key.position.set(-4, 6, 8); scene.add(key);
  const fill = new THREE.DirectionalLight(0x9cabb9, 2.4); fill.position.set(5, 0, 3); scene.add(fill);
  const rim = new THREE.DirectionalLight(0xffffff, 6); rim.position.set(1, 4, -5); scene.add(rim);

  // Continuous folded metal ribbon. Geometry carries the visual, without neon outlines.
  const core = new THREE.Group(); core.position.set(0, 0.9, -1.1); core.rotation.z = -0.38; root.add(core);
  const ribbonGeo = new THREE.BufferGeometry();
  const positions = [], indices = [], uvs = [];
  const steps = 240, cross = 24;
  for (let i = 0; i <= steps; i++) {
    const u = i / steps * Math.PI * 2;
    for (let j = 0; j <= cross; j++) {
      const v = (j / cross - 0.5) * 1.5;
      const twist = u * 1.5 + 0.25;
      const radius = 2.15 + v * Math.cos(twist) + 0.16 * Math.cos(u * 3);
      positions.push(radius * Math.cos(u), radius * Math.sin(u) * 1.2, v * Math.sin(twist) + 0.42 * Math.sin(u * 2));
      uvs.push(i / steps, j / cross);
      if (i < steps && j < cross) {
        const a = i * (cross + 1) + j, b = a + cross + 1;
        indices.push(a, b, a + 1, b, b + 1, a + 1);
      }
    }
  }
  ribbonGeo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  ribbonGeo.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  ribbonGeo.setIndex(indices); ribbonGeo.computeVertexNormals();
  const sculptureMaterial = material(THREE.MeshPhysicalMaterial, {
    color: 0xaeb1b2, metalness: 0.68, roughness: 0.29, clearcoat: 0.38,
    clearcoatRoughness: 0.25, side: THREE.DoubleSide, transparent: true, opacity: 1,
  });
  const sculpture = mesh(ribbonGeo, sculptureMaterial, core);
  sculpture.rotation.set(0.35, -0.45, 0);

  // Compact workstation with a luminous screen that the scroll camera approaches.
  const pc = new THREE.Group(); pc.position.set(0, -1.3, 2.45); root.add(pc);
  const pcMetal = material(THREE.MeshStandardMaterial, { color: 0x17252d, metalness: 0.78, roughness: 0.35 });
  const desk = mesh(new THREE.BoxGeometry(4.3, 0.08, 1.65), pcMetal, pc); desk.position.y = -0.67;
  const monitor = mesh(new THREE.BoxGeometry(2.65, 1.65, 0.14), pcMetal, pc); monitor.position.y = 0.43;
  const screenCanvas = document.createElement('canvas'); screenCanvas.width = 1024; screenCanvas.height = 640;
  const screenContext = screenCanvas.getContext('2d');
  if (screenContext) {
    const bg = screenContext.createLinearGradient(0, 0, 1024, 640);
    bg.addColorStop(0, '#242629'); bg.addColorStop(1, '#111315');
    screenContext.fillStyle = bg; screenContext.fillRect(0, 0, 1024, 640);
    screenContext.strokeStyle = '#807b72'; screenContext.lineWidth = 2; screenContext.strokeRect(20, 20, 984, 600);
    screenContext.font = '600 65px system-ui, sans-serif'; screenContext.fillStyle = '#f0fffd'; screenContext.fillText('FIELD NOTES', 60, 111);
    screenContext.font = '21px monospace'; screenContext.fillStyle = '#bcb5a7'; screenContext.fillText('NETWORK / SECURITY / PRIVATE SPACE', 64, 157);
    PROJECTS.forEach((project, i) => {
      const y = 225 + i * 67;
      screenContext.fillStyle = i % 2 ? '#202224' : '#26282a'; screenContext.fillRect(50, y - 35, 924, 57);
      screenContext.shadowColor = project[3]; screenContext.shadowBlur = 0;
      screenContext.fillStyle = project[3]; screenContext.font = '25px monospace'; screenContext.fillText(project[1], 70, y);
      screenContext.font = '500 31px system-ui, sans-serif'; screenContext.fillText(project[0], 140, y);
      screenContext.shadowBlur = 0; screenContext.font = '19px monospace'; screenContext.fillText(project[2], 520, y);
      screenContext.fillText('↗', 910, y);
    });
    screenContext.fillStyle = '#bcb5a7'; screenContext.font = '17px monospace'; screenContext.fillText('SELECTED RESEARCH / 2026', 64, 600);
  }
  const screenTexture = new THREE.CanvasTexture(screenCanvas); screenTexture.colorSpace = THREE.SRGBColorSpace; textures.add(screenTexture);
  const display = mesh(new THREE.PlaneGeometry(2.48, 1.48), material(THREE.MeshBasicMaterial, { map: screenTexture, color: 0xffffff }), pc);
  display.position.set(0, 0.43, 0.081);
  const displayWire = wire(new THREE.BoxGeometry(2.67, 1.67, 0.15), 0x8b8983, 0.65, pc); displayWire.position.copy(monitor.position);
  const stand = mesh(new THREE.BoxGeometry(0.16, 0.56, 0.14), pcMetal, pc); stand.position.y = -0.42;
  const foot = mesh(new THREE.BoxGeometry(0.84, 0.05, 0.47), pcMetal, pc); foot.position.set(0, -0.64, 0.12);
  const keyboard = wire(new THREE.BoxGeometry(1.3, 0.035, 0.42), 0x8ab6c3, 0.45, pc); keyboard.position.set(0, -0.59, 0.45);
  const screenHalo = glow(3.8, 0xc4beb3, pc, 0.18); screenHalo.position.set(0, 0.43, -0.1);

  const cards = [], clickable = [], cardPositions = [], cardMaterials = [];
  function labelTexture(project) {
    const c = document.createElement('canvas'); c.width = 768; c.height = 384;
    const ctx = c.getContext('2d');
    if (ctx) {
      ctx.fillStyle = '#191b1d'; ctx.fillRect(0, 0, 768, 384);
      ctx.strokeStyle = '#595850'; ctx.lineWidth = 1; ctx.strokeRect(1, 1, 766, 382);
      ctx.fillStyle = '#a8a398'; ctx.font = '20px monospace'; ctx.fillText('SELECTED WORK', 40, 55);
      ctx.font = '300 116px system-ui, sans-serif'; ctx.fillStyle = '#343638'; ctx.fillText(project[1], 578, 142);
      ctx.font = '400 62px system-ui, sans-serif'; ctx.fillStyle = '#eeeae1'; ctx.fillText(project[0], 38, 202);
      ctx.font = '18px monospace'; ctx.fillStyle = '#a8a398'; ctx.fillText(project[2], 42, 246);
      ctx.beginPath(); ctx.moveTo(40, 290); ctx.lineTo(728, 290); ctx.stroke();
      ctx.font = '18px monospace'; ctx.fillText('VIEW CASE STUDY', 42, 342); ctx.fillText('↗', 700, 342);
    }
    const texture = new THREE.CanvasTexture(c); texture.colorSpace = THREE.SRGBColorSpace;
    texture.anisotropy = Math.min(4, renderer.capabilities.getMaxAnisotropy()); textures.add(texture); return texture;
  }
  PROJECTS.forEach((project, index) => {
    const group = new THREE.Group(); root.add(group);
    const frontMaterial = material(THREE.MeshBasicMaterial, { map: labelTexture(project), transparent: true, opacity: 0, side: THREE.DoubleSide, depthWrite: false });
    const panel = mesh(new THREE.PlaneGeometry(2.5, 1.25), frontMaterial, group); panel.userData.projectIndex = index;
    clickable.push(panel);
    const edge = wire(new THREE.BoxGeometry(2.56, 1.31, 0.045), new THREE.Color(project[3]), 0, group);
    const halo = glow(2.8, new THREE.Color(project[3]), group, 0); halo.position.z = -0.07;
    cards.push(group); cardMaterials.push({ front: frontMaterial, edge: edge.material, halo: halo.material }); cardPositions.push(new THREE.Vector3());
  });

  // Private portal sits behind the network and becomes the final camera destination.
  const portal = new THREE.Group(); portal.position.set(0, 0.8, -3.0); root.add(portal);
  const portalBack = mesh(new THREE.PlaneGeometry(3.4, 4.7), material(THREE.MeshBasicMaterial, { color: 0x02050b, transparent: true, opacity: 0, depthWrite: false }), portal);
  const portalFrame = wire(new THREE.BoxGeometry(3.4, 4.7, 0.08), 0xb6ada0, 0, portal);
  const portalInset = wire(new THREE.BoxGeometry(3.15, 4.44, 0.05), 0x827f78, 0, portal); portalInset.position.z = 0.06;
  const lock = new THREE.Group(); portal.add(lock); lock.position.z = 0.12;
  const lockBody = wire(new THREE.BoxGeometry(0.63, 0.49, 0.04), 0xdce7ff, 0, lock); lockBody.position.y = -0.08;
  const lockArc = mesh(new THREE.TorusGeometry(0.22, 0.014, 5, 28, Math.PI), glowMat(0xdce7ff, 0), lock); lockArc.position.y = 0.17;
  const portalHalo = glow(6.2, 0x9a9285, portal, 0); portalHalo.position.z = -0.08;

  // One draw call for the neon particle field, with deterministic seeded positions.
  let seed = 8917; const rand = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
  const particleData = new Float32Array(36 * 3);
  for (let i = 0; i < 36; i++) {
    particleData[i * 3] = (rand() - 0.5) * 23; particleData[i * 3 + 1] = (rand() - 0.5) * 16;
    particleData[i * 3 + 2] = -rand() * 17 + 4;
  }
  const particleGeo = geometry(new THREE.BufferGeometry()); particleGeo.setAttribute('position', new THREE.BufferAttribute(particleData, 3));
  const particles = new THREE.Points(particleGeo, material(THREE.PointsMaterial, { color: 0xaad7f7, size: 0.025, map: glowTexture, transparent: true, opacity: 0.15, blending: THREE.AdditiveBlending, depthWrite: false })); root.add(particles);
  const cameraPoint = new THREE.Vector3(), targetPoint = new THREE.Vector3();
  const raycaster = new THREE.Raycaster();
  const stops = [0, 0.25, 0.6, 1];
  function updateView() {
    const aspect = width / height;
    const fitZ = mobile ? Math.max(13.5, 3.2 / (Math.tan(THREE.MathUtils.degToRad(24)) * aspect)) : 13;
    const heroZ = mobile ? Math.max(12.5, 3.3 / (Math.tan(THREE.MathUtils.degToRad(24)) * aspect)) : 10.8;
    const privateZ = mobile ? Math.max(5.4, 1.95 / (Math.tan(THREE.MathUtils.degToRad(24)) * aspect) - 3) : 5.4;
    const heroPresence = 1 - smooth(0.02, 0.24, progress);
    root.position.x = mobile ? 0 : 3.25 * heroPresence;
    root.scale.setScalar(1 + (mobile ? 0 : 0.2) * heroPresence);
    const positions = [[0, 1.05, heroZ], [0, -0.86, 2.78], [0, 0.8, fitZ], [0, 0.8, privateZ]];
    const targets = [[0, 0.65, 0], [0, -0.86, 1.8], [0, 0.8, -0.5], [0, 0.8, -3]];
    let segment = 0; while (segment < 2 && progress > stops[segment + 1]) segment++;
    const mix = smooth(stops[segment], stops[segment + 1], progress);
    cameraPoint.fromArray(positions[segment]).lerp(new THREE.Vector3().fromArray(positions[segment + 1]), mix);
    targetPoint.fromArray(targets[segment]).lerp(new THREE.Vector3().fromArray(targets[segment + 1]), mix);
    if (!reducedMotion) {
      cameraPoint.x += smoothedPointer.x * (mobile ? 0.12 : 0.38);
      cameraPoint.y += smoothedPointer.y * 0.22;
    }
    camera.position.copy(cameraPoint); camera.lookAt(targetPoint);
    const orbital = smooth(0.29, 0.55, progress) * (1 - smooth(0.77, 0.96, progress));
    const coreVisibility = 1 - smooth(0.68, 0.96, progress);
    sculptureMaterial.opacity = coreVisibility;
    core.visible = coreVisibility > 0.01;
    pc.visible = progress < 0.41;
    const privateVisibility = smooth(0.69, 0.96, progress);
    portalBack.material.opacity = privateVisibility * 0.86; portalFrame.material.opacity = privateVisibility * 0.76;
    portalInset.material.opacity = privateVisibility * 0.36; lockBody.material.opacity = privateVisibility * 0.8;
    lockArc.material.opacity = privateVisibility * 0.8; portalHalo.material.opacity = privateVisibility * 0.32;
    for (let i = 0; i < cards.length; i++) {
      const angle = Math.PI / 2 + i * Math.PI * 2 / 5;
      const radiusX = mobile ? 2.0 : 4.3;
      const radiusY = mobile ? 2.6 : 2.8;
      const p = cardPositions[i];
      p.set(Math.cos(angle) * radiusX, 0.8 + Math.sin(angle) * radiusY, 1.3 + Math.cos(angle * 2) * 0.22);
      const selected = i === active;
      const bob = reducedMotion ? 0 : Math.sin(elapsed * 0.2 + i * 1.6) * 0.018;
      cards[i].position.copy(p); cards[i].position.y += bob;
      cards[i].scale.setScalar((mobile ? 0.69 : 1) * (selected ? 1.025 : 1));
      cards[i].lookAt(camera.position); cards[i].visible = orbital > 0.025;
      cardMaterials[i].front.opacity = orbital * (active < 0 || selected ? 0.97 : 0.65);
      cardMaterials[i].edge.opacity = orbital * (selected ? 0.45 : 0.12);
      cardMaterials[i].halo.opacity = orbital * (selected ? 0.045 : 0);
    }
  }
  function draw() {
    if (disposed || lost || hidden) return;
    updateView();
    try { renderer.render(scene, camera); } catch { lost = true; fallback('webgl-render-failed'); }
  }
  function animate(time) {
    raf = 0; if (disposed || lost || hidden || reducedMotion) return;
    if (time - lastFrame >= 1000 / 30) {
      const delta = previousTime ? Math.min((time - previousTime) / 1000, 0.1) : 0;
      previousTime = time; lastFrame = time; elapsed += delta;
      smoothedPointer.lerp(pointer, 0.09);
      core.rotation.y = elapsed * 0.018; core.rotation.z = -0.38 + Math.sin(elapsed * 0.07) * 0.025;
      particles.rotation.y = elapsed * 0.006;
      draw();
    }
    if (!lost) raf = requestAnimationFrame(animate);
  }
  function wake() {
    if (disposed || lost || hidden) return;
    if (reducedMotion) draw(); else if (!raf) raf = requestAnimationFrame(animate);
  }
  function resize() {
    if (disposed) return;
    const rect = canvas.getBoundingClientRect(); width = Math.max(1, rect.width); height = Math.max(1, rect.height);
    mobile = width < 600 || width / height < 1.15; camera.aspect = width / height; camera.updateProjectionMatrix();
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5)); renderer.setSize(width, height, false);
    draw(); wake();
  }
  function point(event) {
    const rect = canvas.getBoundingClientRect();
    return new THREE.Vector2((event.clientX - rect.left) / Math.max(rect.width, 1) * 2 - 1, -(event.clientY - rect.top) / Math.max(rect.height, 1) * 2 + 1);
  }
  function pick(event) {
    if (disposed || lost || progress < 0.42 || progress > 0.89) return -1;
    camera.updateMatrixWorld(); root.updateMatrixWorld(true);
    raycaster.setFromCamera(point(event), camera);
    const hit = raycaster.intersectObjects(clickable.filter(card => card.parent.visible), false)[0];
    return hit ? hit.object.userData.projectIndex : -1;
  }
  function onMove(event) {
    if (event.pointerType === 'touch') return;
    pointer.copy(point(event));
    canvas.style.cursor = pick(event) >= 0 ? 'pointer' : '';
  }
  function onDown(event) { if (event.button !== 0) return; dragging = false; downPoint = [event.clientX, event.clientY]; }
  function onUp(event) {
    if (!downPoint) return;
    dragging = Math.hypot(event.clientX - downPoint[0], event.clientY - downPoint[1]) > 8; downPoint = null;
    if (dragging) return;
    const index = pick(event); if (index >= 0 && typeof onSelect === 'function') onSelect(index);
  }
  function onLeave() { pointer.set(0, 0); downPoint = null; canvas.style.cursor = ''; }
  function visibility() {
    hidden = document.hidden; previousTime = 0;
    if (hidden && raf) { cancelAnimationFrame(raf); raf = 0; } else wake();
  }
  function contextLost(event) { event.preventDefault(); lost = true; if (raf) cancelAnimationFrame(raf); raf = 0; fallback('webgl-context-lost'); }
  function contextRestored() {
    if (disposed) return; lost = false; canvas.classList.remove('scene-unavailable'); canvas.parentElement?.classList.remove('scene-unavailable');
    previousTime = 0; resize(); wake();
  }
  canvas.addEventListener('pointermove', onMove); canvas.addEventListener('pointerdown', onDown); canvas.addEventListener('pointerup', onUp);
  canvas.addEventListener('pointerleave', onLeave); canvas.addEventListener('pointercancel', onLeave);
  canvas.addEventListener('webglcontextlost', contextLost); canvas.addEventListener('webglcontextrestored', contextRestored);
  document.addEventListener('visibilitychange', visibility); window.addEventListener('resize', resize, { passive: true });
  const observer = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(resize) : null; observer?.observe(canvas);
  resize();
  return {
    setProgress(value) { progress = clamp(Number.isFinite(value) ? value : 0, 0, 1); if (reducedMotion) draw(); else wake(); },
    setReducedMotion(value) {
      reducedMotion = !!value; previousTime = 0; pointer.set(0, 0); smoothedPointer.set(0, 0);
      if (raf) cancelAnimationFrame(raf); raf = 0; draw(); wake();
    },
    setActive(index) { active = Number.isInteger(index) && index >= 0 && index < 5 ? index : -1; if (reducedMotion) draw(); else wake(); },
    resize,
    dispose() {
      if (disposed) return; disposed = true; if (raf) cancelAnimationFrame(raf); observer?.disconnect();
      document.removeEventListener('visibilitychange', visibility); window.removeEventListener('resize', resize);
      canvas.removeEventListener('pointermove', onMove); canvas.removeEventListener('pointerdown', onDown); canvas.removeEventListener('pointerup', onUp);
      canvas.removeEventListener('pointerleave', onLeave); canvas.removeEventListener('pointercancel', onLeave);
      canvas.removeEventListener('webglcontextlost', contextLost); canvas.removeEventListener('webglcontextrestored', contextRestored);
      canvas.style.cursor = ''; geometries.forEach(g => g.dispose()); materials.forEach(m => m.dispose()); textures.forEach(t => t.dispose());
      renderer.dispose(); scene.clear();
    },
  };
}
