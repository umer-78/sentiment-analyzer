// Project-themed 3D scenes for a page's hero (three.js). One renderer per page: it pauses when the
// hero is off screen or the tab is hidden, holds a still frame for reduced motion, follows the
// pointer, and leaves the page untouched when WebGL is unavailable.
import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.186.1/build/three.module.min.js';

const css = (v, fb) => new THREE.Color((getComputedStyle(document.documentElement).getPropertyValue(v).trim() || fb));
const dark = () => document.documentElement.dataset.theme === 'dark' || (document.documentElement.dataset.theme !== 'light' && matchMedia('(prefers-color-scheme: dark)').matches);

function glowTexture(stops) {
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d'), r = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  for (const [at, a] of stops) r.addColorStop(at, `rgba(255,255,255,${a})`);
  g.fillStyle = r;
  g.fillRect(0, 0, 64, 64);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

export function mount(host, kind = 'ml') {
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: devicePixelRatio < 2, alpha: true, powerPreference: 'low-power' });
  } catch {
    return null;
  }
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches, night = dark();
  const box = document.createElement('div');
  box.className = 'fx-scene';
  box.setAttribute('aria-hidden', 'true');
  box.appendChild(renderer.domElement);
  host.prepend(box);
  renderer.setPixelRatio(Math.min(devicePixelRatio, innerWidth < 760 ? 1.5 : 1.75));
  const scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(40, 2, 0.1, 100);
  camera.position.set(0, 0, 9);
  const A = css('--accent', '#6366f1'), B = css('--fx-2', '#06b6d4'), C = css('--fx-3', '#f59e0b');
  const BAD = new THREE.Color(night ? '#ff6b6b' : '#dc2626'), INK = new THREE.Color(night ? '#e5e7eb' : '#334155');
  // weaker devices skip the costlier touches: clear-coated materials and the light that follows the pointer
  const lite = innerWidth < 760 || (navigator.hardwareConcurrency || 8) <= 4 || (navigator.deviceMemory || 8) <= 4;
  renderer.toneMapping = THREE.NeutralToneMapping;
  // a small painted studio for reflections (soft boxes above and to the sides), so glossy parts catch light
  // the way a product shot does; it is tiny, so turning it into an environment map costs next to nothing
  {
    const c = document.createElement('canvas');
    c.width = 128;
    c.height = 64;
    const g = c.getContext('2d'), sky = g.createLinearGradient(0, 0, 0, 64);
    sky.addColorStop(0, night ? '#2a3040' : '#f4f6fa');
    sky.addColorStop(0.5, night ? '#11141b' : '#b8bec8');
    sky.addColorStop(1, night ? '#050608' : '#5b616b');
    g.fillStyle = sky;
    g.fillRect(0, 0, 128, 64);
    const soft = (x, y, rx, ry, a) => { const r = g.createRadialGradient(x, y, 0, x, y, rx); r.addColorStop(0, `rgba(255,255,255,${a})`); r.addColorStop(1, 'rgba(255,255,255,0)'); g.save(); g.translate(x, y); g.scale(1, ry / rx); g.translate(-x, -y); g.fillStyle = r; g.fillRect(x - rx, y - rx, rx * 2, rx * 2); g.restore(); };
    soft(64, 8, 30, 9, 1);
    soft(20, 26, 12, 16, night ? 0.75 : 0.9);
    soft(104, 30, 10, 14, night ? 0.55 : 0.7);
    const env = new THREE.CanvasTexture(c);
    env.mapping = THREE.EquirectangularReflectionMapping;
    env.colorSpace = THREE.SRGBColorSpace;
    scene.environment = env;
    scene.environmentIntensity = night ? 0.9 : 1.1;
  }
  scene.add(new THREE.HemisphereLight(0xffffff, night ? 0x1b2030 : 0x9aa3b5, night ? 0.55 : 0.7));
  const key = new THREE.DirectionalLight(0xffffff, 1.15);
  key.position.set(4, 6, 8);
  scene.add(key);
  // the scene's own group sits on a stage: the stage carries the fit beside the text, the build-in and the scroll depth
  const stage = new THREE.Group(), root = new THREE.Group();
  scene.add(stage);
  stage.add(root);
  // a soft glow for halos; on a light page, particles get a firmer dot so they read against white
  const tex = glowTexture([[0, 1], [0.22, 0.75], [0.5, 0.18], [1, 0]]), dot = night ? tex : glowTexture([[0, 1], [0.42, 0.95], [0.68, 0.4], [1, 0]]), blend = night ? THREE.AdditiveBlending : THREE.NormalBlending;
  const std = (c, o = {}) => lite
    ? new THREE.MeshStandardMaterial({ color: c, roughness: 0.32, metalness: 0.15, emissive: c, emissiveIntensity: night ? 0.3 : 0.06, ...o })
    : new THREE.MeshPhysicalMaterial({ color: c, roughness: 0.26, metalness: 0.1, clearcoat: 0.85, clearcoatRoughness: 0.16, emissive: c, emissiveIntensity: night ? 0.22 : 0.04, ...o });
  const line = (c, opacity = 0.35) => new THREE.LineBasicMaterial({ color: c, transparent: true, opacity, depthWrite: false });
  const glowMat = (c, size, opacity = 1) => new THREE.PointsMaterial({ color: c, size, map: dot, transparent: true, opacity, depthWrite: false, blending: blend, sizeAttenuation: true });
  const sprite = (c, s, opacity = 0.9) => { const m = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, color: c, transparent: true, opacity, depthWrite: false, blending: blend })); m.scale.setScalar(s); return m; };
  const points = (n, c, size, opacity) => { const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 3), 3)); const p = new THREE.Points(g, glowMat(c, size, opacity)); p.frustumCulled = false; return p; };
  const colored = (n, size, opacity = 1) => { const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 3), 3)); g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(n * 3), 3)); const m = glowMat(0xffffff, size, opacity); m.vertexColors = true; const p = new THREE.Points(g, m); p.frustumCulled = false; return p; };
  const rand = (() => { let s = 7; return () => ((s = (s * 16807) % 2147483647) / 2147483647); })();
  const tick = [];

  // small builders the scene below is written with
  const add = (o) => { root.add(o); return o; };
  const at = (o, x, y, z = 0) => { o.position.set(x, y, z); return o; };
  const mesh = (g, c, o) => new THREE.Mesh(g, std(c, o));
  const cube = (w, h, d, c, o) => mesh(new THREE.BoxGeometry(w, h, d), c, o);
  const ball = (r, c, o) => mesh(new THREE.SphereGeometry(r, 24, 16), c, o);
  const disc = (r, h, c, o) => mesh(new THREE.CylinderGeometry(r, r, h, 28), c, o);
  const hoop = (r, w, c, o) => mesh(new THREE.TorusGeometry(r, w, 10, 48), c, o);
  const vec = (p) => new THREE.Vector3(p[0], p[1], p[2] || 0);
  const path = (pts, c, op = 0.5) => new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts.map(vec)), line(c, op));
  const segs = (pairs, c, op = 0.35) => new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(pairs.flat().map(vec)), line(c, op));
  const wire = (g, c, op = 0.45) => new THREE.LineSegments(new THREE.EdgesGeometry(g), line(c, op));
  const word = (s, c, size = 0.42) => {
    const cv = document.createElement('canvas'), g = cv.getContext('2d'), font = '600 64px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';
    g.font = font;
    cv.width = Math.ceil(g.measureText(s).width) + 24;
    cv.height = 88;
    const h = cv.getContext('2d');
    h.font = font;
    h.textBaseline = 'middle';
    h.fillStyle = '#' + c.getHexString();
    h.fillText(s, 12, 46);
    const tx = new THREE.CanvasTexture(cv);
    tx.colorSpace = THREE.SRGBColorSpace;
    const m = new THREE.Sprite(new THREE.SpriteMaterial({ map: tx, transparent: true, depthWrite: false }));
    m.scale.set((size * cv.width) / cv.height, size, 1);
    return m;
  };
  // a point part-way round a closed or open run of waypoints, u in 0..1
  const along = (pts, u) => {
    const n = pts.length - 1, f = (((u % 1) + 1) % 1) * n, i = Math.min(n - 1, Math.floor(f)), k = f - i, a = pts[i], b = pts[i + 1];
    return [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, (a[2] || 0) + ((b[2] || 0) - (a[2] || 0)) * k];
  };
  const wave = (t, period, phase = 0) => (((t / period + phase) % 1) + 1) % 1;   // a 0→1 ramp that repeats
  const ease = (x) => x * x * (3 - 2 * x);
  const K = new THREE.Color();
  const shade = (m, a, b, k) => { m.material.color.copy(K.copy(a).lerp(b, Math.max(0, Math.min(1, k)))); m.material.emissive.copy(m.material.color); };
  const fill = (p) => { p.geometry.attributes.position.needsUpdate = true; if (p.geometry.attributes.color) p.geometry.attributes.color.needsUpdate = true; };

  const S = {
    // a review's words drop onto a balance, each weighted by how much more often it appears in positive or negative reviews, and the beam settles on the classifier's verdict
    scale() {
      const V = { loved: 1.3, great: 0.9, perfect: 1.1, fun: 0.7, fine: 0.15, slow: -0.6, boring: -1.0, awful: -1.5, waste: -1.3, not: -0.35 };
      const reviews = [['loved', 'fun', 'slow', 'great'], ['boring', 'not', 'fun', 'waste'], ['fine', 'great', 'awful', 'perfect'], ['slow', 'boring', 'fine', 'awful']];
      add(at(mesh(new THREE.ConeGeometry(0.32, 0.75, 4), INK, { transparent: true, opacity: 0.85 }), 0, -1.68, 0));
      const beam = add(at(cube(4.7, 0.08, 0.22, INK), 0, -1.3, 0)), arm = 2.25;
      const pans = [B, BAD].map((c) => add(disc(0.6, 0.05, c, { transparent: true, opacity: 0.85 })));
      const ropes = [0, 1].map(() => add(segs([[0, 0, 0], [0, 0.55, 0]], INK, 0.5)));
      const items = reviews.map((r) => r.map((w) => ({ v: V[w], s: add(word(w, V[w] > 0.25 ? B : V[w] < -0.25 ? BAD : INK, 0.26 + Math.abs(V[w]) * 0.08)) })));
      const verdict = [add(word('positive', B, 0.42)), add(word('negative', BAD, 0.42))];
      let tilt = 0;
      tick.push((t, dt) => {
        const k = Math.floor(t / 7) % reviews.length, u = (t % 7) / 7, cur = items[k];
        items.forEach((r, q) => r.forEach((it) => { it.s.visible = q === k; }));
        let sum = 0;
        const land = cur.map((it, i) => { const d = Math.max(0, Math.min(1, (u * 7 - 0.4 - i * 1.1) / 0.7)); if (d >= 1) sum += it.v; return d; });
        const target = Math.max(-0.3, Math.min(0.3, sum * 0.12));
        tilt += (target - tilt) * (1 - Math.exp(-dt * 4));
        beam.rotation.z = tilt;
        const ends = [-1, 1].map((sgn) => [sgn * arm * Math.cos(tilt), -1.3 + sgn * arm * Math.sin(tilt)]);
        pans.forEach((p, i) => { p.position.set(ends[i][0], ends[i][1] - 0.55, 0); ropes[i].position.set(ends[i][0], ends[i][1] - 0.55, 0); });
        const stack = [0, 0];
        cur.forEach((it, i) => {
          const side = it.v >= 0 ? 0 : 1, p = pans[side].position, h = stack[side]++, d = ease(land[i]), y0 = 2.3;
          it.s.position.set(p.x + (h % 2 ? 0.28 : -0.28), y0 + (p.y + 0.3 + h * 0.34 - y0) * d, 0.2);
          it.s.material.opacity = land[i] > 0 ? 1 : 0;
        });
        const done = u > 0.8;
        verdict[0].visible = done && sum >= 0;
        verdict[1].visible = done && sum < 0;
        verdict.forEach((v) => v.position.set(0, -0.55, 0.2));
      });
    },
  };
  Object.values(S)[0]();

  // the field behind the scene; each project picks its own on <html data-backdrop>
  const look = document.documentElement.dataset, back = look.backdrop || 'motes', hero = look.hero || 'right';
  const field = new THREE.Group(), drift = [];
  let pip = false, shell = null;   // the corner window the scene moves to once the hero scrolls away
  scene.add(field);
  const fade = (pairs, c, alphas) => {   // line pairs whose ends fade out with distance
    const g = new THREE.BufferGeometry().setFromPoints(pairs.flat().map(vec)), col = new Float32Array(alphas.length * 4);
    alphas.forEach((a, i) => col.set([c.r, c.g, c.b, a], i * 4));
    g.setAttribute('color', new THREE.BufferAttribute(col, 4));
    return new THREE.LineSegments(g, new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, depthWrite: false }));
  };
  if (back === 'motes' || back === 'dust') {
    const n = back === 'dust' ? 110 : 140, p = points(n, back === 'dust' ? C : B, back === 'dust' ? 0.055 : 0.07, night ? 0.55 : 0.35), a = p.geometry.attributes.position.array;
    for (let i = 0; i < n; i++) a.set([(rand() - 0.5) * 14, (rand() - 0.5) * 8, -2 - rand() * 6], i * 3);
    field.add(p);
    if (back === 'dust') drift.push((t, dt) => { for (let i = 0; i < n; i++) { const y = a[i * 3 + 1] + dt * (0.1 + (i % 7) * 0.03); a[i * 3 + 1] = y > 4 ? y - 8 : y; } fill(p); });
    else drift.push((t) => { field.rotation.y = Math.sin(t * 0.05) * 0.3; });
  } else if (back === 'grid') {
    // a floor of lines running away from the viewer, scrolling slowly toward it
    const pairs = [], al = [], base = night ? 0.28 : 0.2, rows = 11;
    for (let i = -9; i <= 9; i++) { pairs.push([[i * 1.2, -2.9, 3], [i * 1.2, -2.9, -16]]); al.push(base, 0); }
    for (let k = 0; k < rows; k++) { pairs.push([[-12, -2.9, 0], [12, -2.9, 0]]); al.push(base, base); }
    const g = fade(pairs, B, al), pa = g.geometry.attributes.position.array, ca = g.geometry.attributes.color.array, first = 19 * 2;
    field.add(g);
    drift.push((t) => {
      for (let k = 0; k < rows; k++) {
        const z = 3 - ((k / rows + t * 0.035) % 1) * 19, a = base * Math.min(1, (z + 16) / 12) * Math.min(1, (3 - z) / 1.5), v = (first + k * 2) * 3, c = (first + k * 2) * 4;
        pa[v + 2] = pa[v + 5] = z;
        ca[c + 3] = ca[c + 7] = a;
      }
      g.geometry.attributes.position.needsUpdate = g.geometry.attributes.color.needsUpdate = true;
    });
  } else if (back === 'rings') {
    // faint tilted orbits, each turning at its own pace
    for (let k = 0; k < 4; k++) {
      const r = 2.8 + k * 1.35, ring = new THREE.Line(new THREE.BufferGeometry().setFromPoints(Array.from({ length: 129 }, (_, j) => new THREE.Vector3(Math.cos((j / 128) * Math.PI * 2) * r, Math.sin((j / 128) * Math.PI * 2) * r, 0))), line(k % 2 ? B : A, night ? 0.16 : 0.11));
      ring.position.z = -4 - k * 0.6;
      ring.rotation.x = 1.15 + k * 0.08;
      field.add(ring);
      const bead = sprite(k % 2 ? B : A, 0.22, night ? 0.9 : 0.6);
      field.add(bead);
      const v = new THREE.Vector3();
      drift.push((t) => { const u = t * (0.12 - k * 0.02) + k * 1.7; v.set(Math.cos(u) * r, Math.sin(u) * r, 0).applyEuler(ring.rotation); bead.position.set(v.x, v.y, v.z + ring.position.z); ring.rotation.z = t * 0.01 * (k % 2 ? 1 : -1); });
    }
  } else if (back === 'stars') {
    // a wide, fine star field in two layers that twinkle out of step
    for (let L = 0; L < 2; L++) {
      const n = 130, p = points(n, L ? B : INK, L ? 0.05 : 0.035, night ? 0.7 : 0.32), a = p.geometry.attributes.position.array;
      for (let i = 0; i < n; i++) a.set([(rand() - 0.5) * 18, (rand() - 0.5) * 10, -3 - rand() * 8], i * 3);
      field.add(p);
      const o = p.material.opacity;
      drift.push((t) => { p.material.opacity = o * (0.6 + 0.4 * Math.sin(t * (0.9 + L * 0.5) + L * 2)); field.rotation.z = t * 0.004; });
    }
  }

  // what the scene spans, measured once: every mesh, label and line, shown or not (a hidden part still marks
  // where it will appear), leaving out anything parked far off; the scene is then fitted beside the text
  let t = reduce ? 2.5 : 0;
  for (const f of tick) f(t, 0);
  const span = new THREE.Box3(), part = new THREE.Box3(), mid = new THREE.Vector3(), size = new THREE.Vector3();
  root.updateMatrixWorld(true);
  root.traverse((o) => {
    if (o === root || !o.geometry) return;
    if (o.isPoints) {   // particles one by one, so those parked out of sight do not count
      const a = o.geometry.attributes.position;
      for (let i = 0; i < a.count; i++) {
        mid.fromBufferAttribute(a, i).applyMatrix4(o.matrixWorld);
        if (Math.max(Math.abs(mid.x), Math.abs(mid.y), Math.abs(mid.z)) < 30) span.expandByPoint(mid);
      }
      return;
    }
    o.geometry.computeBoundingBox();
    part.copy(o.geometry.boundingBox).applyMatrix4(o.matrixWorld);
    part.getCenter(mid);
    if (Math.max(Math.abs(mid.x), Math.abs(mid.y), Math.abs(mid.z)) < 30) span.union(part);
  });
  if (span.isEmpty()) span.set(new THREE.Vector3(-3, -2, 0), new THREE.Vector3(3, 2, 0));
  span.getCenter(mid);
  span.getSize(size);
  const half = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
  let fitS = 1;
  const fitP = new THREE.Vector3();
  const words = () => {   // the box the hero's text occupies, in page pixels
    let r = null;
    for (const el of host.children) {
      if (el === box || getComputedStyle(el).position === 'absolute') continue;
      const q = el.getBoundingClientRect();
      if (!q.width || !q.height) continue;
      r = r ? { l: Math.min(r.l, q.left), r: Math.max(r.r, q.right), t: Math.min(r.t, q.top), b: Math.max(r.b, q.bottom) } : { l: q.left, r: q.right, t: q.top, b: q.bottom };
    }
    return r;
  };
  const fit = () => {
    const w = box.clientWidth, h = box.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    // the part of the canvas no text covers, in canvas pixels
    let x0 = 0, x1 = w, y0 = 0, y1 = h;
    const c = box.getBoundingClientRect(), q = !pip && innerWidth > 760 && words();
    if (pip) { /* the corner window is all scene */ }
    else if (innerWidth <= 760) y1 = h * 0.82;   // a phone banner fades out at its foot
    else if (q && hero === 'left') x1 = Math.min(w, q.l - c.left - 20);
    else if (q && hero === 'band') y1 = Math.min(h, q.t - c.top - 6);
    else if (q && hero === 'center') y0 = Math.max(0, q.b - c.top + 6);
    else if (q) x0 = Math.max(0, q.r - c.left + 20);
    if (x1 - x0 < w * 0.3) { x0 = 0; x1 = w; }
    if (y1 - y0 < h * 0.3) { y0 = 0; y1 = h; }
    const u = (2 * camera.position.z * half) / h;   // world units per canvas pixel where the scene stands
    const deep = 1.08 + size.z / (2 * camera.position.z);   // margin for tilt, plus near parts drawn larger
    const s = Math.max(0.5, Math.min(1.35, ((x1 - x0) * u - 0.4) / (size.x * deep + 1e-3), ((y1 - y0) * u - 0.4) / (size.y * deep + 1e-3)));
    fitS = s;
    fitP.set(((x0 + x1) / 2 - w / 2) * u - mid.x * s, (h / 2 - (y0 + y1) / 2) * u - mid.y * s, -mid.z * s);
  };
  const ro = new ResizeObserver(() => fit());
  ro.observe(box);
  ro.observe(host);
  document.fonts?.ready.then(fit);
  fit();
  const aim = { x: 0, y: 0 };
  const ptr = { x: 0, y: 0, live: false };   // the pointer over the canvas, from -1 to 1
  addEventListener('pointermove', (e) => {
    aim.x = (e.clientY / innerHeight - 0.5) * 0.35;
    aim.y = (e.clientX / innerWidth - 0.5) * 0.5;
    if (e.pointerType !== 'mouse') return;
    const r = box.getBoundingClientRect();
    ptr.x = ((e.clientX - r.left) / Math.max(1, r.width)) * 2 - 1;
    ptr.y = 1 - ((e.clientY - r.top) / Math.max(1, r.height)) * 2;
    ptr.live = Math.abs(ptr.x) < 1.3 && Math.abs(ptr.y) < 1.3;
  }, { passive: true });
  // a soft light follows the pointer across the scene and shows up the glossy parts; with no pointer it drifts on its own
  const glint = lite ? null : new THREE.PointLight(0xffffff, night ? 16 : 11, 10, 2);
  if (glint) { glint.position.set(2, 1, 3); scene.add(glint); }
  let born = 0;
  let raf = 0, visible = true, last = performance.now(), stopped = false;
  const still = () => reduce || document.documentElement.classList.contains('fx-still');
  function frame(now) {
    raf = 0;
    if (stopped || (!visible && !pip) || document.hidden) return;
    const dt = Math.max(0, Math.min(0.05, (now - last) / 1000));   // a frame stamp can predate performance.now()
    last = now;
    if (!still()) t += dt;
    const step = still() ? 0 : dt;
    for (const f of tick) f(t, step);
    for (const f of drift) f(t, step);
    // the scene builds itself in, then recedes and tilts away as the hero scrolls up
    if (!born) born = now;
    const k = still() ? 1 : Math.min(1, (now - born) / 1300), e = 1 - Math.pow(1 - k, 3);
    let p = 0;
    if (!pip) { const r = host.getBoundingClientRect(); p = Math.max(0, Math.min(1, -r.top / Math.max(1, r.height))); }
    stage.scale.setScalar(fitS * (0.8 + 0.2 * e));
    stage.position.set(fitP.x, fitP.y - (1 - e) * 0.8, fitP.z - p * 2.4);
    stage.rotation.set(p * 0.32, (1 - e) * -0.7, 0);
    if (glint) {
      const gx = ptr.live ? ptr.x * 4.6 : Math.cos(t * 0.35) * 3.2, gy = ptr.live ? ptr.y * 2.6 : Math.sin(t * 0.27) * 1.8;
      glint.position.x += (gx - glint.position.x) * 0.08;
      glint.position.y += (gy - glint.position.y) * 0.08;
    }
    scene.rotation.x += (aim.x - scene.rotation.x) * 0.04;
    scene.rotation.y += (aim.y - scene.rotation.y) * 0.04;
    renderer.render(scene, camera);
    if (!still()) raf = requestAnimationFrame(frame);
  }
  const wake = () => { if (!stopped && (visible || pip) && !raf) { last = performance.now(); raf = requestAnimationFrame(frame); } };
  addEventListener('fx:motion', wake);
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; wake(); }).observe(host);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) wake(); });
  raf = requestAnimationFrame((n) => { frame(n); box.classList.add('on'); });
  return {
    box,
    stop() {
      stopped = true;
      ro.disconnect();
      cancelAnimationFrame(raf);
      removeEventListener('fx:motion', wake);
      renderer.dispose();
      renderer.forceContextLoss?.();
      box.remove();
      shell?.remove();
    },
  };
}
