// 3D model + walk pane for the house-design-estimate skill. Reads window.DATA (inches; x east, y north, z up).
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
const DATA = window.DATA, IN = 0.0254;
const MAT = {wall:'#EDE6DA',slab:'#CFC9BE',tile:'#F4F2EE',tilew:'#DCE8EC',deck:'#D9C7A8',court:'#B9C9A2',stone:'#D8D2C8',
  glass:'#8EC3DA',col:'#BDB5A8',duct:'#C8B59A',rail:'#3d4a52',san:'#FAFAFA',steel:'#B8BEC2',wood:'#A47B52',wood2:'#C9A77E',
  fab:'#7D8FA3',fab2:'#9C8B7A',dark:'#2E3236',pv:'#22384F',green:'#6E9A57',car:'#D8CBB0',furn:'#B0A898',parq:'#C8A57A',beam:'#A8998A',rw:'#1098AD',lacq:'#5E7480',wmirr:'#C9D6DC',
  pvc:'#8F979C',cold:'#2F7FD0',hot:'#D0462F',wire:'#E0A100',exh:'#C3CBD1',sw:'#F4F3EF',gear:'#9AA3A9',grille:'#E4E6E6',gully:'#6F767A',water:'#3E7FA8',tank:'#55626B'};
const mats = {};
const POCHE = new THREE.MeshBasicMaterial({color: '#2B3940'}); // cut wall faces
const matOf = k => mats[k] || (mats[k] = k === 'glass'
  ? new THREE.MeshStandardMaterial({color: MAT.glass, transparent: true, opacity: .35, roughness: .1, depthWrite: false})
  : new THREE.MeshStandardMaterial({color: MAT[k] || '#bbb', roughness: .85}));
const W = DATA.building.w * IN, D = DATA.building.d * IN;
const scene = new THREE.Scene(); scene.background = new THREE.Color('#dfe7ec');
const view = document.getElementById('view');
const renderer = new THREE.WebGLRenderer({antialias: true}); renderer.shadowMap.enabled = true;
renderer.setPixelRatio(Math.min(2, devicePixelRatio)); view.appendChild(renderer.domElement);
Object.assign(renderer.domElement.style, {width: '100%', height: '100%', display: 'block'});
const cam = new THREE.PerspectiveCamera(40, 1, .1, 500);
const ctl = new OrbitControls(cam, renderer.domElement); ctl.target.set(W / 2, 3, -D / 2);
const HTOT = (DATA.levels.at(-1).ffl + DATA.levels.at(-1).h) * IN;
// frame the whole house in the 3D pane from direction (dx, dy, dz), whatever its size and the pane's shape
function fit(dx = 1, dy = .8, dz = 1.1, tgtY = HTOT / 2) {
  const R = Math.hypot(W, D, HTOT) / 2 * 0.85, vf = cam.fov * Math.PI / 360, hf = Math.atan(Math.tan(vf) * cam.aspect);
  const dist = R / Math.sin(Math.min(vf, hf)); const n = Math.hypot(dx, dy, dz);
  ctl.target.set(W / 2, tgtY, -D / 2); cam.position.set(W / 2 + dx / n * dist, tgtY + dy / n * dist, -D / 2 + dz / n * dist);
  cam.near = dist / 100; cam.far = dist * 10; cam.updateProjectionMatrix(); ctl.update(); }
fit();
const hemi = new THREE.HemisphereLight('#ffffff', '#8a8070', .75); scene.add(hemi);
const sun = new THREE.DirectionalLight('#fff4e0', 1.6); sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, {left: -30, right: 30, top: 30, bottom: -30, near: .5, far: 120}); scene.add(sun, sun.target);
sun.target.position.set(W / 2, 0, -D / 2);
const ground = new THREE.Mesh(new THREE.PlaneGeometry(200, 200), new THREE.MeshStandardMaterial({color: '#cfd8c4'}));
ground.rotation.x = -Math.PI / 2; ground.position.set(W / 2, -0.01, -D / 2); ground.receiveShadow = true; scene.add(ground);
const meshes = [], byLv = {};
for (const b of DATA.boxes) {
  if (b.w <= 0 || b.d <= 0 || b.h <= 0) continue;
  const g = new THREE.BoxGeometry(b.w * IN, b.h * IN, b.d * IN);
  const m = new THREE.Mesh(g, matOf(b.m));
  m.position.set((b.x + b.w / 2) * IN, (b.z + b.h / 2) * IN, -(b.y + b.d / 2) * IN);
  m.castShadow = b.m !== 'glass'; m.receiveShadow = true; m.userData = b; scene.add(m); meshes.push(m);
  (byLv[b.lv] = byLv[b.lv] || []).push(m);
}
const lvIds = DATA.levels.map(l => l.id);
let curLv = null, only = true, cutOn = false, ELEV = null;
// layer toggles: services and furniture can be switched off; doors, lights, switches and sockets always show
const LAYER = {rwp: 'tPlumb', fixw: 'tFurn', plumb: 'tPlumb', cold: 'tPlumb', hot: 'tPlumb', tankx: 'tPlumb', stack: 'tPlumb', wire: 'tElec', exh: 'tExh', fix: 'tFurn', fixg: 'tFurn'};
const layerOn = k => { const e = LAYER[k] && document.getElementById(LAYER[k]); return k === 'stack' ? true : !e || e.checked; };
const lvVis = lv => { if (lv === '*' || !curLv) return true; const i = lvIds.indexOf(lv), k = curLv ? lvIds.indexOf(curLv) : lvIds.length - 1; return only ? i === k : i <= k; };
function refresh() { meshes.forEach(m => m.visible = lvVis(m.userData.lv) && layerOn(m.userData.k) && !m.userData.del && !((cutOn || curLv) && ['lamp', 'fan', 'beam'].includes(m.userData.k)) && !(ELEV && (m.userData.k === 'site' || m.userData.k === 'name')) && !(m.userData.k === 'name' && curLv && m.userData.lv !== curLv));
  for (const [c, id] of [['plumb', 'tPlumb'], ['wire', 'tElec'], ['exh', 'tExh']]) { const on = document.getElementById(id)?.checked;
    document.querySelectorAll('#plan2d .svc-' + c).forEach(g => g.style.display = on ? '' : 'none'); } }
const SVCK = new Set(['rwp', 'plumb', 'cold', 'hot', 'tankx', 'wire', 'exh']);
function showLevel(id) {
  curLv = id; const k = id ? lvIds.indexOf(id) : lvIds.length - 1; refresh();
  if (!cutOn) cut(id || '*', id ? 84 : null); // one floor: walls cut at 7' with dark cut faces
  const L = DATA.levels[k]; const dy = (L.ffl + 30) * IN - ctl.target.y; ctl.target.y += dy; cam.position.y += dy; ctl.update();
}
// sun position (NOAA approximation)
function sunDir(month, hour) {
  const P = DATA.project.location, lat = P.lat * Math.PI / 180, doy = [21,52,80,111,141,172,202,233,264,294,325,355][month];
  const g = 2 * Math.PI / 365 * (doy - 1 + (hour - 12) / 24);
  const eq = 229.18 * (0.000075 + 0.001868 * Math.cos(g) - 0.032077 * Math.sin(g) - 0.014615 * Math.cos(2 * g) - 0.040849 * Math.sin(2 * g));
  const de = 0.006918 - 0.399912 * Math.cos(g) + 0.070257 * Math.sin(g) - 0.006758 * Math.cos(2 * g) + 0.000907 * Math.sin(2 * g) - 0.002697 * Math.cos(3 * g) + 0.00148 * Math.sin(3 * g);
  const tst = hour * 60 + eq + 4 * P.lon - 60 * P.tz, ha = (tst / 4 - 180) * Math.PI / 180;
  const cz = Math.sin(lat) * Math.sin(de) + Math.cos(lat) * Math.cos(de) * Math.cos(ha), alt = Math.asin(Math.max(-1, Math.min(1, cz)));
  let az = Math.atan2(Math.sin(ha), Math.cos(ha) * Math.sin(lat) - Math.tan(de) * Math.cos(lat)) + Math.PI;
  az -= (DATA.project.north_deg || 0) * Math.PI / 180;
  return {alt, az, x: Math.sin(az) * Math.cos(alt), y: Math.cos(az) * Math.cos(alt), z: Math.sin(alt)};
}
const MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
// slider runs from 45 min before sunrise to 1 h 45 min after sunset (dusk shows the lights); Play animates the day
function riseSet(mo) { let r = 6, st = 18; for (let h = 3; h < 12; h += .02) if (sunDir(mo, h).z > 0) { r = h; break; }
  for (let h = 21; h > 12; h -= .02) if (sunDir(mo, h).z > 0) { st = h; break; } return [r, st]; }
const hm = h => { const t = Math.round(h * 60); return String(Math.floor(t / 60) % 24).padStart(2, '0') + ':' + String(t % 60).padStart(2, '0'); };
const warm = new THREE.Color('#ffb070'), day = new THREE.Color('#fff4e0'), skyD = new THREE.Color('#dfe7ec'), skyN = new THREE.Color('#1c2533'), skyT = new THREE.Color();
let sunAlt = 30;
function hourNow() { const mo = +document.getElementById('sunM').value, [r, st] = riseSet(mo); return r - .75 + (st - r + 2.5) * (+document.getElementById('sunT').value) / 1000; }
function setSun() {
  const mo = +document.getElementById('sunM').value, hr = hourNow(), s = sunDir(mo, hr), [r, st] = riseSet(mo);
  sunAlt = s.alt * 180 / Math.PI; const up = s.z > 0, k = Math.min(1, Math.max(0, sunAlt / 18)), kn = Math.min(1, Math.max(0, (sunAlt + 6) / 12));
  const real = document.getElementById('sunOn').checked; document.getElementById('sunT').disabled = !real; document.getElementById('sunM').disabled = !real;
  if (!real) { sun.visible = true; sun.position.set(W / 2 + 25, 40, -D / 2 + 30); sun.intensity = 1.6; sun.color.copy(day); hemi.intensity = .75; scene.background = skyT.copy(skyD); sunAlt = 45;
    document.getElementById('sunInfo').textContent = 'Off: fixed studio light.'; document.getElementById('sunTxt').textContent = 'Studio light'; document.getElementById('sunChart2').style.display = 'none'; setLights(); return; }
  sun.visible = up; sun.position.set(W / 2 + s.x * 60, Math.max(.5, s.z * 60), -D / 2 - s.y * 60);
  sun.intensity = .25 + 1.35 * k; sun.color.copy(warm).lerp(day, k);
  hemi.intensity = .1 + .65 * kn; scene.background = skyT.copy(skyN).lerp(skyD, kn);
  let noon = (r + st) / 2, na = 0; for (let h = r; h < st; h += .05) { const a = sunDir(mo, h).alt; if (a > na) { na = a; noon = h; } }
  const sh = up && sunAlt > .5 ? (1 / Math.tan(s.alt)).toFixed(1) + ' × height' : 'very long', az = trueAz(s);
  document.getElementById('sunInfo').innerHTML = `<b>21 ${MON[mo]}, ${h12(hr)}</b> · ` + (up ? `sun ${sunAlt.toFixed(0)}° high, from the ${card(az)} (${az.toFixed(0)}°) · shadow ${sh}` : 'sun below the horizon, lights on') +
    `<br>Sunrise ${h12(r)} · noon ${h12(noon)} at ${(na * 180 / Math.PI).toFixed(0)}° · sunset ${h12(st)} · ${(st - r).toFixed(1)} h of sun`;
  document.getElementById('sunTxt').textContent = `☀ ${h12(hr)}, 21 ${MON[mo]} · ` + (up ? `${sunAlt.toFixed(0)}° high, from ${card(az)}` : 'after dark');
  sunChart(mo, hr); setLights();
}
let playing = null;
function play(on) { if (playing) { cancelAnimationFrame(playing); playing = null; } const b = document.getElementById('sunPlay');
  b.setAttribute('aria-pressed', !!on); b.textContent = on ? '❚❚ Pause' : '▶ Play day'; if (!on) return; let last = performance.now();
  const stepP = t => { const el = document.getElementById('sunT'); let v = +el.value + (t - last) * .07; last = t; if (v > 1000) v = 0; el.value = v; setSun(); playing = requestAnimationFrame(stepP); };
  playing = requestAnimationFrame(stepP); }
document.getElementById('sunPlay').onclick = () => play(!playing);
['sunM', 'sunT'].forEach(i => document.getElementById(i).addEventListener('input', setSun));
['sunOn', 'sunChart'].forEach(i => document.getElementById(i).addEventListener('change', setSun));
{ const m = new Date().getMonth(), el = document.getElementById('sunM'); el.value = m; const [r, st] = riseSet(m); document.getElementById('sunT').value = Math.round(Math.min(1, Math.max(0, (10 - (r - .75)) / (st - r + 2.5))) * 1000); }
// ---------------- sun chart, sun info, real-sun switch ----------------
const h12 = h => { const t = Math.round(((h % 24) + 24) % 24 * 60), H = Math.floor(t / 60), M = t % 60; return `${(H + 11) % 12 + 1}:${String(M).padStart(2, '0')} ${H < 12 ? 'AM' : 'PM'}`; };
const CARD = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
const trueAz = s => (((s.az * 180 / Math.PI) + (DATA.project.north_deg || 0)) % 360 + 360) % 360, card = a => CARD[Math.round(a / 22.5) % 16];
function sunChart(mo, hr) { const el = document.getElementById('sunChart2'); if (!el) return; el.style.display = document.getElementById('sunChart').checked ? '' : 'none';
  const R = 62, xy = (alt, az) => { const r = (90 - Math.max(0, alt)) / 90 * R, a = az * Math.PI / 180; return [r * Math.sin(a), -r * Math.cos(a)]; };
  const [r0, s0] = riseSet(mo); let path = '';
  for (let h = r0; h <= s0 + .01; h += 1 / 6) { const s = sunDir(mo, h), [x, y] = xy(s.alt * 180 / Math.PI, trueAz(s)); path += (path ? 'L' : 'M') + x.toFixed(1) + ',' + y.toFixed(1); }
  const s = sunDir(mo, hr), up = s.z > 0, [sx, sy] = xy(s.alt * 180 / Math.PI, trueAz(s));
  el.innerHTML = `<div style="text-align:right"><b>☀ ${h12(hr)}, 21 ${MON[mo]}</b><br><span class="muted">${up ? (s.alt * 180 / Math.PI).toFixed(0) + '° high, from ' + card(trueAz(s)) : 'sun below the horizon'}</span></div>
  <svg width="150" height="150" viewBox="-75 -75 150 150"><circle r="${R}" fill="#EEF2F4" stroke="#B9C3C8"/><circle r="${R * 2 / 3}" fill="none" stroke="#D3DADD"/><circle r="${R / 3}" fill="none" stroke="#D3DADD"/>
  <line x1="-${R}" x2="${R}" stroke="#D3DADD"/><line y1="-${R}" y2="${R}" stroke="#D3DADD"/>
  <text y="-${R + 4}" text-anchor="middle" font-size="9">N</text><text y="${R + 11}" text-anchor="middle" font-size="9">S</text><text x="${R + 7}" y="3" text-anchor="middle" font-size="9">E</text><text x="-${R + 7}" y="3" text-anchor="middle" font-size="9">W</text>
  <path d="${path}" fill="none" stroke="#D9961A" stroke-width="2"/>${up ? `<line x1="0" y1="0" x2="${sx.toFixed(1)}" y2="${sy.toFixed(1)}" stroke="#D9961A" stroke-dasharray="2 2"/><circle cx="${sx.toFixed(1)}" cy="${sy.toFixed(1)}" r="5" fill="#F2B632" stroke="#9A6A0A"/>` : ''}</svg>`; }
// ---------------- floors, cameras, straight-on elevations ----------------
const ROAD = ((DATA.project.road || 'S') + '')[0], OPP = {S: 'N', N: 'S', E: 'W', W: 'E'}, DV = {S: [0, 1], N: [0, -1], E: [1, 0], W: [-1, 0]};
function clearElev() { if (!ELEV) return; ELEV = null; refresh(); cam.fov = 40; ctl.enableRotate = true; document.querySelectorAll('[data-elev]').forEach(b => b.setAttribute('aria-pressed', false)); }
function camView(side, el = .42, skew = .4) { const [x, z] = DV[side]; fit(x + z * skew, el, z - x * skew, tgtNow()); }
const tgtNow = () => cutOn && document.getElementById('tSpread').checked ? (HTOT + SPREAD * (lvIds.length - 1)) / 2 : HTOT / 2;
const presets = {front: () => camView(ROAD), back: () => camView(OPP[ROAD]), S: () => camView('S'), N: () => camView('N'), E: () => camView('E'), W: () => camView('W'),
  top: () => fit(0, 1, .001, tgtNow()), iso: () => fit(1, .8, 1.1, tgtNow())};
document.querySelectorAll('[data-cam]').forEach(b => b.onclick = () => { clearElev(); presets[b.dataset.cam]();
  document.querySelectorAll('[data-cam]').forEach(x => x.setAttribute('aria-pressed', x === b)); });
function setElev(side) { ELEV = side; refresh(); cam.fov = 12; const [x, z] = DV[side]; fit(x, .0001, z, tgtNow()); ctl.enableRotate = false;
  document.querySelectorAll('[data-elev]').forEach(b => b.setAttribute('aria-pressed', b.dataset.elev === side));
  document.querySelectorAll('[data-cam]').forEach(x => x.setAttribute('aria-pressed', false)); }
document.querySelectorAll('[data-elev]').forEach(b => b.onclick = () => setElev(b.dataset.elev));
document.querySelectorAll('[data-lv]').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('[data-lv]').forEach(x => x.setAttribute('aria-pressed', x === b));
  const id = b.dataset.lv || null; if (cutOn && id) { document.getElementById('tCut').checked = false; setCut(false); }
  showLevel(id);
  document.querySelectorAll('#plan2d svg').forEach(s => s.style.display = (s.dataset.level === (id || lvIds.at(-1))) ? '' : 'none');
}));
document.getElementById('showBelow').onchange = e => { only = !e.target.checked; showLevel(curLv); };
const tog = (id, fn) => { const e = document.getElementById(id); if (e) e.onchange = () => fn(e.checked); };
tog('tFurn', v => { refresh(); document.querySelectorAll('#plan2d .fx').forEach(e => e.style.display = v ? '' : 'none'); });
['tPlumb', 'tElec', 'tExh'].forEach(i => tog(i, refresh));
// X-ray: see-through walls, slabs and floors so pipes, ducts and cables in floors and walls show
const XR = ['wall', 'slab', 'tile', 'tilew', 'deck', 'court', 'stone', 'col', 'parq', 'duct'];
tog('tXray', v => XR.forEach(k => { const m = matOf(k); m.transparent = v; m.opacity = v ? .22 : 1; m.depthWrite = !v; m.needsUpdate = true; }));
tog('tVastu', v => document.querySelectorAll('#plan2d .vastu').forEach(g => g.style.display = v ? 'inline' : 'none'));
// ---------------- doors (real leaves you can open) ----------------
const DMAT = {main: '#6B4A2E', ext: '#8A6440', door: '#B8895A', bath: '#E9E4DA'};
const dmat = {}, dm = t => dmat[t] || (dmat[t] = new THREE.MeshStandardMaterial({color: DMAT[t] || DMAT.door, roughness: .6}));
const MH = new THREE.MeshStandardMaterial({color: '#C9CDCF', metalness: .6, roughness: .3}), MF = new THREE.MeshStandardMaterial({color: '#3A4045', roughness: .5, metalness: .3});
const DOORS = [];
const wrap = a => { while (a > Math.PI) a -= 2 * Math.PI; while (a < -Math.PI) a += 2 * Math.PI; return a; };
function track(o, lv, k) { o.userData = Object.assign(o.userData || {}, {lv, k}); scene.add(o); meshes.push(o); return o; }
for (const d of DATA.doors || []) {
  const z0 = d.z * IN, Hh = (d.h - .5) * IN, T = 1.6 * IN;
  if (d.type === 'slide') {
    const l = (d.b - d.a) * .55, mk = (cx, cy) => { const g = new THREE.Group(), w = l * IN, F = 2 * IN;
      const v = d.o === 'v', box = (a, h) => new THREE.BoxGeometry(v ? T : a, h, v ? a : T);
      g.add(new THREE.Mesh(box(w, Hh), matOf('glass')));
      for (const y of [F / 2 - Hh / 2, Hh / 2 - F / 2]) { const f = new THREE.Mesh(box(w, F), MF); f.position.y = y; g.add(f); }
      for (const s of [-1, 1]) { const f = new THREE.Mesh(box(F, Hh), MF); if (v) f.position.z = s * (w / 2 - F / 2); else f.position.x = s * (w / 2 - F / 2); g.add(f); }
      g.position.set(cx * IN, z0 + Hh / 2, -cy * IN); return track(g, d.lv, 'door'); };
    let A, Bp;
    if (d.o === 'h') { A = mk(d.a + l / 2, d.mid - .9); Bp = mk(d.b - l / 2, d.mid + .9); }
    else { A = mk(d.mid - .9, d.a + l / 2); Bp = mk(d.mid + .9, d.b - l / 2); }
    DOORS.push({d, kind: 'slide', B: Bp, b0: d.o === 'h' ? Bp.position.x : Bp.position.z, travel: (d.b - d.a - l - 2) * IN, t: d.open ? 1 : 0, goal: d.open ? 1 : 0, parts: [A, Bp]});
  } else {
    const L = (d.b - d.a - .8) * IN, piv = new THREE.Group();
    const leaf = new THREE.Mesh(new THREE.BoxGeometry(L, Hh, T), dm(d.type)); leaf.position.set(L / 2, Hh / 2 + .3 * IN, 0); leaf.castShadow = true;
    const hd = new THREE.Mesh(new THREE.BoxGeometry(5 * IN, 1 * IN, 3.6 * IN), MH); hd.position.set(L - 3.5 * IN, 38 * IN, 0); piv.add(leaf, hd);
    const hinge = d.hg === 'a' ? d.a + .4 : d.b - .4, pl = d.face - d.dir * 1.0, s = d.hg === 'a' ? 1 : -1;
    const [px, py] = d.o === 'h' ? [hinge, pl] : [pl, hinge];
    const pc = d.o === 'h' ? Math.atan2(0, s) : Math.atan2(s, 0), po = d.o === 'h' ? Math.atan2(d.dir, 0) : Math.atan2(0, d.dir);
    piv.position.set(px * IN, z0, -py * IN); track(piv, d.lv, 'door');
    const D = {d, kind: 'hinge', piv, pc, dlt: wrap(po - pc) * .97, t: d.open ? 1 : 0, goal: d.open ? 1 : 0, parts: [leaf]};
    piv.rotation.y = pc + D.dlt * D.t; DOORS.push(D);
  }
}
function stepDoors(dt) { for (const D of DOORS) { if (D.t === D.goal) continue; const s = dt * 1.6;
  D.t = D.goal > D.t ? Math.min(D.goal, D.t + s) : Math.max(D.goal, D.t - s); const e = D.t * D.t * (3 - 2 * D.t);
  if (D.kind === 'hinge') D.piv.rotation.y = D.pc + D.dlt * e;
  else if (D.d.o === 'h') D.B.position.x = D.b0 - D.travel * e; else D.B.position.z = D.b0 + D.travel * e; } }
const _b3 = new THREE.Box3(); let doorBox = [];
function doorBoxes() { doorBox = []; for (const D of DOORS) { if (Math.abs(D.d.z * IN - WK.y) > 1.5) continue; for (const p of D.parts) { _b3.setFromObject(p); doorBox.push([_b3.min.clone(), _b3.max.clone()]); } } }
function toggleDoor() { let best = null, bd = 1.9; const fx = -Math.sin(WK.yaw), fz = -Math.cos(WK.yaw);
  for (const D of DOORS) { if (Math.abs(D.d.z * IN - WK.y) > 1) continue; const cx = (D.d.o === 'h' ? (D.d.a + D.d.b) / 2 : D.d.mid) * IN, cz = -(D.d.o === 'h' ? D.d.mid : (D.d.a + D.d.b) / 2) * IN;
    const dx = cx - WK.x, dz = cz - WK.z, dist = Math.hypot(dx, dz), score = dist - .6 * ((dx * fx + dz * fz) / (dist || 1)); if (score < bd) { bd = score; best = D; } }
  if (best) best.goal = best.goal > .5 ? 0 : 1; return best; }
let allOpen = true;
function allDoors(open) { allOpen = open; DOORS.forEach(D => D.goal = open ? 1 : 0);
  const b = document.getElementById('wkDoors'); if (b) b.textContent = open ? 'Doors: close all' : 'Doors: open all'; }
document.getElementById('wkDoors').onclick = () => allDoors(!allOpen);
// ---------------- lights (ceiling oysters, IP65 wall bulkheads) and ceiling fans ----------------
const lampMat = new THREE.MeshStandardMaterial({color: '#FFFDF6', emissive: '#FFE7B8', emissiveIntensity: 0, roughness: .4});
const lampGeo = new THREE.CylinderGeometry(5 * IN, 5 * IN, 1.4 * IN, 20), bulkGeo = new THREE.BoxGeometry(9 * IN, 5 * IN, 3 * IN);
const RL = [];
for (const L of DATA.lights || []) {
  const m = new THREE.Mesh(L.kind === 'wall' ? bulkGeo : lampGeo, lampMat); m.position.set(L.x * IN, L.z * IN, -L.y * IN); track(m, L.lv, 'lamp'); Object.assign(m.userData, {cct: L.cct, sw: L.sw});
  RL.push({lv: L.lv, x: L.x * IN, y: L.z * IN - .25, z: -L.y * IN, cd: (L.ip ? 1.2 : 2) + Math.min(3, L.area / 40)});
}
// a fixed pool of 8 lamps follows the nearest fittings on the walker's floor (a fixed count never recompiles shaders)
const POOL = Array.from({length: 8}, () => { const p = new THREE.PointLight('#ffe3b5', 0, 9, 2); scene.add(p); return p; });
const FANS = [], fanMat = new THREE.MeshStandardMaterial({color: '#EDEDEA', roughness: .5});
for (const F of DATA.fans || []) {
  const g = new THREE.Group(), rod = new THREE.Mesh(new THREE.CylinderGeometry(.5 * IN, .5 * IN, 10 * IN, 8), fanMat); rod.position.y = 6 * IN;
  const hub = new THREE.Mesh(new THREE.CylinderGeometry(4 * IN, 4 * IN, 3 * IN, 16), fanMat), bl = new THREE.Group();
  for (let i = 0; i < 3; i++) { const b = new THREE.Mesh(new THREE.BoxGeometry(22 * IN, .4 * IN, 4.5 * IN), fanMat); b.position.x = 14 * IN; const a = new THREE.Group(); a.rotation.y = i * 2 * Math.PI / 3; a.add(b); bl.add(a); }
  g.add(rod, hub, bl); g.position.set(F.x * IN, F.z * IN, -F.y * IN); track(g, F.lv, 'fan'); Object.assign(g.userData, {cct: F.cct, sw: F.sw}); FANS.push(bl);
}
let lightsOn = false, litKey = '';
function setLights() { const v = document.getElementById('lgt').value; lightsOn = v === 'on' || (v === 'auto' && sunAlt < 8);
  lampMat.emissiveIntensity = lightsOn ? 1.6 : 0; const b = document.getElementById('wkLights'); if (b) b.textContent = lightsOn ? 'Lights: on' : 'Lights: off'; litKey = ''; }
// light the walker's floor and the floor shown in 3D (few lights keep the page fast)
function updLamps() { const wl = (DATA.levels.slice().reverse().find(l => WK.y >= l.ffl * IN - .3) || DATA.levels[0]).id;
  const k = lightsOn + wl + Math.round(WK.x) + ',' + Math.round(WK.z); if (k === litKey) return; litKey = k;
  const near = lightsOn ? RL.filter(L => L.lv === wl).sort((a, b) => Math.hypot(a.x - WK.x, a.z - WK.z) - Math.hypot(b.x - WK.x, b.z - WK.z)) : [];
  POOL.forEach((p, i) => { const L = near[i]; p.intensity = L ? L.cd : 0; if (L) p.position.set(L.x, L.y, L.z); }); }
document.getElementById('lgt').onchange = setLights;
document.getElementById('wkLights').onclick = () => { const s = document.getElementById('lgt'); s.value = lightsOn ? 'off' : 'on'; setLights(); };
// flash a room in 3D + put the walker there
const flash = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshBasicMaterial({color: '#E8590C', transparent: true, opacity: .45, depthTest: false}));
flash.visible = false; scene.add(flash);
function pickRoom(id) {
  const r = DATA.rooms.find(x => x.id === id); if (!r) return;
  const [x, y, w, d] = r.r; flash.scale.set(w * IN, 2.6, d * IN); flash.position.set((x + w / 2) * IN, r.ffl * IN + 1.3, -(y + d / 2) * IN);
  let n = 0; const t = setInterval(() => { flash.visible = !flash.visible; if (++n >= 6) { clearInterval(t); flash.visible = false; } }, 260);
  WK.place(r);
  const card = document.getElementById('roomCard'); if (card) card.innerHTML = r.card;
}
document.getElementById('plan2d').addEventListener('click', e => { const g = e.target.closest('[data-room]'); if (g) pickRoom(g.dataset.room); });
// ---------------- colour schemes (five presets, plus doors and floors) ----------------
const FINS = {fWall: () => [matOf('wall')], fSlab: () => [matOf('slab'), matOf('col')], fSteel: () => [matOf('rail'), matOf('steel')],
  fFrame: () => [MF], fGlass: () => [matOf('glass')], fDoor: () => [dm('door'), dm('ext')], fFloor: () => [matOf('tile')]};
const PRESET = {def: ['#efece5', '#c6c9c1', '#4a555b', '#3a4045', '#8fc3da', '#b8895a', '#f4f2ee'],
  warm: ['#e8dcc4', '#b9ab92', '#5a4a3a', '#6b4f35', '#9cc0c8', '#8a6440', '#e9dcc5'],
  terra: ['#c9765a', '#e9e4da', '#1f2326', '#1f2326', '#8fb4c4', '#3a2a20', '#e2d6c4'],
  grey: ['#c9cdd0', '#f2f2ef', '#2e3438', '#f4f4f2', '#a5c9d8', '#e9e9e6', '#eceeef'],
  cream: ['#f1e6cf', '#8a6a4a', '#3b3530', '#7a4e2c', '#93bccb', '#7a4e2c', '#efe3cb']};
const FKEY = 'hdfin:' + DATA.project.name;
function setFin(id, v) { const el = document.getElementById(id); if (!el) return; el.value = v; FINS[id]().forEach(m => m.color.set(v)); }
const saveFin = () => { try { localStorage.setItem(FKEY, JSON.stringify(Object.keys(FINS).map(id => document.getElementById(id).value))); } catch (e) {} };
Object.keys(FINS).forEach(id => document.getElementById(id)?.addEventListener('input', e => { setFin(id, e.target.value); saveFin(); }));
document.getElementById('fPreset').addEventListener('change', e => { const p = PRESET[e.target.value]; if (p) { Object.keys(FINS).forEach((id, i) => setFin(id, p[i])); saveFin(); } e.target.value = ''; });
try { const sv = JSON.parse(localStorage.getItem(FKEY) || 'null'); if (sv) Object.keys(FINS).forEach((id, i) => sv[i] && setFin(id, sv[i])); } catch (e) {}
// ---------------- walkway check while furniture moves (same rules as scripts/paths.py) ----------------
// a person is a disc of R inches: R 15 = 750 mm clear path (warn), R 10 = nobody gets through (fail)
function pathGrid(lid, R, skip) {
  const P = DATA.walk[lid], G = 3, W0 = DATA.building.w, D0 = DATA.building.d, nx = Math.floor(W0 / G) + 1, ny = Math.floor(D0 / G) + 1;
  const free = new Uint8Array(nx * ny), L = DATA.levels.find(l => l.id === lid);
  const each = (x, y, w, d, g, fn) => { for (let j = Math.max(0, Math.floor((y - g) / G)); j <= Math.min(ny - 1, Math.floor((y + d + g) / G)); j++)
    for (let i = Math.max(0, Math.floor((x - g) / G)); i <= Math.min(nx - 1, Math.floor((x + w + g) / G)); i++) fn(i, j, i * G + G / 2, j * G + G / 2); };
  const carve = ([x, y, w, d]) => each(x, y, w, d, 0, (i, j, cx, cy) => { if (cx >= x && cx <= x + w && cy >= y && cy <= y + d) free[j * nx + i] = 1; });
  const block = ([x, y, w, d], g) => each(x, y, w, d, g, (i, j, cx, cy) => { const ex = Math.max(x - cx, 0, cx - x - w), ey = Math.max(y - cy, 0, cy - y - d);
    if (ex * ex + ey * ey < g * g) free[j * nx + i] = 0; });
  P.rooms.forEach(carve); P.solids.forEach(r => block(r, R));
  const targets = [];
  for (const o of P.doors) { const rr = o.rr, k = Math.max(1, Math.floor((o.b - o.a - 2) / G)), along = [];
    for (let t = 0; t <= k; t++) along.push(o.a + 1 + (o.b - o.a - 2) * t / k);
    let sides; if (o.o === 'h') { carve([o.a, rr[1] - R - 3, o.b - o.a, rr[3] + 2 * R + 6]); sides = [along.map(u => [u, rr[1] - R - 1]), along.map(u => [u, rr[1] + rr[3] + R + 1])]; }
    else { carve([rr[0] - R - 3, o.a, rr[2] + 2 * R + 6, o.b - o.a]); sides = [along.map(u => [rr[0] - R - 1, u]), along.map(u => [rr[0] + rr[2] + R + 1, u])]; }
    for (let pts of sides) { pts = pts.filter(p => p[0] >= 0 && p[0] < W0 && p[1] >= 0 && p[1] < D0 && P.rooms.some(r => r[0] <= p[0] && p[0] <= r[0] + r[2] && r[1] <= p[1] && p[1] <= r[1] + r[3]));
      if (pts.length) targets.push({id: o.id, pts, main: o.main}); } }
  const fx = meshes.filter(m => m.userData.k === 'fix' && m.userData.lv === lid && !m.userData.del && !skip.has(m.userData.id) &&
    !P.noblock.includes(m.userData.t) && m.userData.z - L.ffl < 36);
  fx.forEach(m => block([m.userData.x, m.userData.y, m.userData.w, m.userData.d], R));
  for (const s of P.stairs) { const r = P.stairRects[s]; targets.push({id: s, pts: [[r[0] + r[2] / 2, r[1] + r[3] / 2]], stair: true}); }
  P.flights.forEach(carve);
  return {free, targets, nx, ny, G, fx};
}
function pathReach(g, start) { const {free, nx, ny, G} = g, seen = new Uint8Array(nx * ny); let si = Math.floor(start[0] / G), sj = Math.floor(start[1] / G), b = -1;
  for (let rad = 0; rad < 12 && b < 0; rad++) for (let j = sj - rad; j <= sj + rad && b < 0; j++) for (let i = si - rad; i <= si + rad; i++)
    if (i >= 0 && j >= 0 && i < nx && j < ny && free[j * nx + i]) { b = j * nx + i; break; }
  if (b < 0) return seen; const q = [b]; seen[b] = 1;
  while (q.length) { const c = q.pop(), i = c % nx, j = (c - i) / nx;
    for (const [a, e] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const u = i + a, v = j + e, n = v * nx + u; if (u >= 0 && v >= 0 && u < nx && v < ny && free[n] && !seen[n]) { seen[n] = 1; q.push(n); } } }
  return seen; }
const pathOk = (g, seen, pts) => pts.some(([x, y]) => { const i = Math.floor(x / g.G), j = Math.floor(y / g.G);
  for (let a = -1; a <= 1; a++) for (let b = -1; b <= 1; b++) { const u = i + a, v = j + b; if (u >= 0 && v >= 0 && u < g.nx && v < g.ny && seen[v * g.nx + u]) return true; } return false; });
function pathCheck(lid) { const P = DATA.walk && DATA.walk[lid]; if (!P || P.roof) return []; const res = [], li = lvIds.indexOf(lid);
  for (const [sev, R] of [['fail', 10], ['warn', 15]]) {
    const g = pathGrid(lid, R, new Set()); if (!g.targets.length) continue;
    const st = (li === 0 && g.targets.find(t => t.main)) || g.targets.find(t => t.stair) || g.targets[0];
    const start = st.pts[Math.floor(st.pts.length / 2)], seen = pathReach(g, start);
    const g0 = pathGrid(lid, R, new Set(meshes.filter(m => m.userData.k === 'fix').map(m => m.userData.id))), seen0 = pathReach(g0, start);
    for (const t of g.targets) { if (pathOk(g, seen, t.pts) || !pathOk(g0, seen0, t.pts) || res.some(x => x.id === t.id)) continue;
      const q = t.pts[Math.floor(t.pts.length / 2)], who = [];
      for (const m of g.fx.slice().sort((a, b) => Math.abs(a.userData.x + a.userData.w / 2 - q[0]) + Math.abs(a.userData.y + a.userData.d / 2 - q[1]) - Math.abs(b.userData.x + b.userData.w / 2 - q[0]) - Math.abs(b.userData.y + b.userData.d / 2 - q[1])).slice(0, 8)) {
        const g1 = pathGrid(lid, R, new Set([m.userData.id])); if (pathOk(g1, pathReach(g1, start), t.pts)) who.push(m.userData.id); }
      res.push({sev, id: t.id, who}); } }
  return res; }
const RNAME = Object.fromEntries(DATA.rooms.map(r => [r.id, r.n]));
function pathShow(lid) { const box = document.getElementById('ePath'); if (!box) return;
  document.querySelectorAll('#plan2d .fu.blk').forEach(g => g.classList.remove('blk'));
  const res = pathCheck(lid);
  res.forEach(r => r.who.forEach(id => document.querySelectorAll(`#plan2d [data-fx="${id}"]`).forEach(g => g.classList.add('blk'))));
  box.className = res.length ? 'bad' : 'good';
  box.innerHTML = res.length ? res.map(r => `${r.sev === 'fail' ? '⛔ Blocked' : '⚠ Under 750 mm'}: way to ${RNAME[r.id] || 'door ' + r.id}${r.who.length ? ' (' + r.who.join(', ') + ')' : ''}`).join('<br>')
    : '✓ Every door and stair has a 750 mm clear way'; return res; }
// ---------------- move, rotate or delete furniture (drag in 2D; 3D and walk follow) ----------------
const EDKEY = 'hdfurn:' + DATA.project.name, plan2d = document.getElementById('plan2d'), edBar = document.getElementById('editBar');
let EDITS = {}; try { EDITS = JSON.parse(localStorage.getItem(EDKEY) || '{}'); } catch (e) {}
const FX0 = {}; meshes.forEach(m => { const b = m.userData; if (b.k === 'fix' || b.k === 'fixg' || b.k === 'fixw') { b.o = {x: b.x, y: b.y, w: b.w, d: b.d};
  const id = b.fid || (b.k === 'fixg' ? b.id.replace(/-screen$/, '') : b.id); (FX0[id] = FX0[id] || {r: [b.x, b.y, b.w, b.d], lv: b.lv, ms: []}).ms.push(m); } });
const edOn = () => document.getElementById('tEdit').checked;
let edSel = null, edDrag = null, edHist = [];
const E0 = () => ({dx: 0, dy: 0, rot: 0, del: false}), edOf = id => EDITS[id] || E0();
function edRect(id) { const f = FX0[id], e = edOf(id), [x, y, w, d] = f.r, cx = x + w / 2 + e.dx, cy = y + d / 2 + e.dy, [W2, D2] = e.rot % 2 ? [d, w] : [w, d];
  return [cx - W2 / 2, cy - D2 / 2, W2, D2]; }
function edApply(id) { const f = FX0[id]; if (!f) return; const e = edOf(id), [x, y, w, d] = f.r;
  const fcx = x + w / 2, fcy = y + d / 2;
  for (const m of f.ms) { const o = m.userData.o; let rx = o.x + o.w / 2 - fcx, ry = o.y + o.d / 2 - fcy; for (let q = 0; q < e.rot; q++) [rx, ry] = [ry, -rx];
    const cx = fcx + rx + e.dx, cy = fcy + ry + e.dy, [W2, D2] = e.rot % 2 ? [o.d, o.w] : [o.w, o.d];
    Object.assign(m.userData, {x: cx - W2 / 2, y: cy - D2 / 2, w: W2, d: D2, del: e.del}); m.position.x = cx * IN; m.position.z = -cy * IN; m.rotation.y = -e.rot * Math.PI / 2; }
  document.querySelectorAll(`#plan2d [data-fx="${id}"]`).forEach(g => { const cx = x + w / 2, cy = DATA.building.d - (y + d / 2);
    g.setAttribute('transform', `translate(${e.dx} ${-e.dy}) rotate(${e.rot * 90} ${cx} ${cy})`); g.style.display = e.del ? 'none' : ''; }); }
function edSave() { try { localStorage.setItem(EDKEY, JSON.stringify(EDITS)); } catch (e) {} }
function edShow() { plan2d.classList.toggle('editing', edOn()); edBar.hidden = !edOn(); const inf = document.getElementById('eInfo');
  document.querySelectorAll('#plan2d .fsel').forEach(g => g.classList.remove('fsel'));
  if (!edSel || !edOn()) { inf.textContent = 'Nothing selected.'; return; }
  document.querySelectorAll(`#plan2d [data-fx="${edSel}"]`).forEach(g => g.classList.add('fsel'));
  const r = edRect(edSel), ft = v => `${Math.floor(v / 12)}'-${Math.round(v % 12)}"`;
  inf.textContent = `${edSel} · ${ft(r[2])} × ${ft(r[3])} · from west ${ft(r[0])}, from south ${ft(r[1])}`; }
function edDo(fn) { if (!edSel) return; edHist.push([edSel, JSON.stringify(edOf(edSel))]); const e = Object.assign(E0(), edOf(edSel)); fn(e); EDITS[edSel] = e; edSave(); edApply(edSel); refresh(); edShow(); edCheck(); }
const lvNow2 = () => (edSel && FX0[edSel] ? FX0[edSel].lv : [...plan2d.querySelectorAll('svg')].find(x => x.style.display !== 'none')?.dataset.level);
const edCheck = () => { if (edOn()) pathShow(lvNow2()); };
const edRotate = cw => edDo(e => e.rot = (e.rot + (cw ? 1 : 3)) % 4), edDelete = () => { edDo(e => e.del = true); edSel = null; edShow(); };
document.getElementById('eRotL').onclick = () => edRotate(false); document.getElementById('eRotR').onclick = () => edRotate(true);
document.getElementById('eDel').onclick = edDelete;
document.getElementById('eUndo').onclick = () => { const h = edHist.pop(); if (!h) return; EDITS[h[0]] = JSON.parse(h[1]); edSave(); edApply(h[0]); refresh(); edSel = h[0]; edShow(); edCheck(); };
document.getElementById('eReset').onclick = () => { const ids = Object.keys(EDITS); EDITS = {}; edHist = []; edSave(); ids.forEach(edApply); refresh(); edSel = null; edShow(); edCheck(); };
document.getElementById('eCopy').onclick = () => { const out = Object.keys(EDITS).filter(id => FX0[id]).map(id => EDITS[id].del ? {id, delete: true} : {id, r: edRect(id).map(v => Math.round(v * 2) / 2)});
  const ta = document.getElementById('eOut'); ta.hidden = false; ta.value = JSON.stringify({furniture_changes: out});
  try { navigator.clipboard.writeText(ta.value).catch(() => {}); } catch (e) {} ta.select(); };
document.getElementById('tEdit').addEventListener('change', () => { edShow(); edCheck(); });
document.querySelectorAll('[data-lv]').forEach(b => b.addEventListener('click', () => setTimeout(edCheck, 0)));
const toSvg = (svg, e) => { const p = svg.createSVGPoint(); p.x = e.clientX; p.y = e.clientY; return p.matrixTransform(svg.getScreenCTM().inverse()); };
plan2d.addEventListener('pointerdown', e => { if (!edOn()) return; const g = e.target.closest('.fu[data-fx]');
  if (!g) { if (edSel) { edSel = null; edShow(); } return; }
  e.stopPropagation(); e.preventDefault(); edSel = g.dataset.fx; edShow(); const svg = g.ownerSVGElement;
  edDrag = {svg, p0: toSvg(svg, e), e0: {...edOf(edSel)}, moved: false}; plan2d.setPointerCapture(e.pointerId); }, true);
plan2d.addEventListener('pointermove', e => { if (!edDrag) return; const p = toSvg(edDrag.svg, e), dx = Math.round(p.x - edDrag.p0.x), dy = Math.round(edDrag.p0.y - p.y);
  if (!edDrag.moved && Math.hypot(dx, dy) < 2) return; edDrag.moved = true;
  EDITS[edSel] = Object.assign(E0(), edDrag.e0, {dx: edDrag.e0.dx + dx, dy: edDrag.e0.dy + dy}); edApply(edSel); }, true);
plan2d.addEventListener('pointerup', () => { if (!edDrag) return; const d = edDrag; edDrag = null; if (!d.moved) return;
  edHist.push([edSel, JSON.stringify(d.e0)]); edSave(); edShow(); edCheck(); }, true);
plan2d.addEventListener('click', e => { if (edOn() && e.target.closest('.fu')) e.stopPropagation(); }, true);
addEventListener('keydown', e => { if (!edOn() || !edSel || /TEXTAREA|INPUT|SELECT/.test(document.activeElement?.tagName || '')) return; const st = e.shiftKey ? 6 : 1;
  const mv = {ArrowLeft: [-st, 0], ArrowRight: [st, 0], ArrowUp: [0, st], ArrowDown: [0, -st]}[e.key];
  if (mv) { e.preventDefault(); edDo(x => { x.dx += mv[0]; x.dy += mv[1]; }); }
  else if (e.key === 'r' || e.key === 'R') edRotate(!e.shiftKey); else if (e.key === 'Delete' || e.key === 'Backspace') { e.preventDefault(); edDelete(); } });
Object.keys(FX0).forEach(edApply);
tog('tDims', v => document.querySelectorAll('#plan2d .dims').forEach(g => g.style.display = v ? '' : 'none'));
// ---------------- 2D zoom and pan: wheel or pinch to zoom, drag to pan, + / − / Fit buttons ----------------
const svgs2 = [...plan2d.querySelectorAll('svg')]; svgs2.forEach(x => x.dataset.vb0 = x.getAttribute('viewBox'));
const cur2 = () => svgs2.find(x => x.style.display !== 'none') || svgs2[0];
function zoom2(k, cx, cy) { const sv = cur2(), v = sv.viewBox.baseVal, w0 = +sv.dataset.vb0.split(' ')[2];
  k = Math.min(Math.max(k, w0 / 14 / v.width), w0 * 1.6 / v.width); if (cx == null) { cx = v.x + v.width / 2; cy = v.y + v.height / 2; }
  const nx = cx - (cx - v.x) * k, ny = cy - (cy - v.y) * k, nw = v.width * k, nh = v.height * k;
  svgs2.forEach(x => x.setAttribute('viewBox', `${nx} ${ny} ${nw} ${nh}`)); }
plan2d.addEventListener('wheel', e => { e.preventDefault(); const p = toSvg(cur2(), e); zoom2(e.deltaY > 0 ? 1.15 : 1 / 1.15, p.x, p.y); }, {passive: false});
document.getElementById('z2in').onclick = () => zoom2(1 / 1.4); document.getElementById('z2out').onclick = () => zoom2(1.4);
document.getElementById('z2fit').onclick = () => svgs2.forEach(x => x.setAttribute('viewBox', x.dataset.vb0));
const ptrs = new Map(); let pan = null, pinch = null, panMoved = false;
plan2d.addEventListener('pointerdown', e => { if (edDrag) return; ptrs.set(e.pointerId, [e.clientX, e.clientY]); panMoved = false;
  if (ptrs.size === 2) { const [a, b] = [...ptrs.values()]; pinch = Math.hypot(a[0] - b[0], a[1] - b[1]); pan = null; }
  else { pan = [e.clientX, e.clientY]; } });
addEventListener('pointermove', e => { if (!ptrs.has(e.pointerId)) return; ptrs.set(e.pointerId, [e.clientX, e.clientY]);
  const sv = cur2(), v = sv.viewBox.baseVal;
  if (pinch && ptrs.size === 2) { const [a, b] = [...ptrs.values()], dd = Math.hypot(a[0] - b[0], a[1] - b[1]); const p = toSvg(sv, {clientX: (a[0] + b[0]) / 2, clientY: (a[1] + b[1]) / 2});
    zoom2(pinch / dd, p.x, p.y); pinch = dd; panMoved = true; return; }
  if (!pan) return; const dx = e.clientX - pan[0], dy = e.clientY - pan[1]; if (!panMoved && Math.hypot(dx, dy) < 4) return;
  panMoved = true; plan2d.classList.add('panning'); const p0 = toSvg(sv, {clientX: pan[0], clientY: pan[1]}), p1 = toSvg(sv, e); pan = [e.clientX, e.clientY];
  svgs2.forEach(x => x.setAttribute('viewBox', `${v.x - (p1.x - p0.x)} ${v.y - (p1.y - p0.y)} ${v.width} ${v.height}`)); });
const endPtr = e => { ptrs.delete(e.pointerId); if (ptrs.size < 2) pinch = null; if (!ptrs.size) { pan = null; plan2d.classList.remove('panning'); } };
addEventListener('pointerup', endPtr); addEventListener('pointercancel', endPtr);
plan2d.addEventListener('click', e => { if (panMoved) { e.stopPropagation(); panMoved = false; } }, true);
// ---------------- room names (3D), columns and beams, colour by, light and air ----------------
function nameSprite(txt) { const c = document.createElement('canvas'), x = c.getContext('2d'), fs = 44; x.font = `600 ${fs}px Barlow, Arial, sans-serif`;
  const w = Math.ceil(x.measureText(txt).width) + 28; c.width = w; c.height = fs + 22; x.font = `600 ${fs}px Barlow, Arial, sans-serif`;
  x.fillStyle = 'rgba(255,255,255,.86)'; x.beginPath(); x.roundRect ? x.roundRect(0, 0, w, c.height, 12) : x.rect(0, 0, w, c.height); x.fill();
  x.fillStyle = '#1C282D'; x.textBaseline = 'middle'; x.fillText(txt, 14, c.height / 2 + 2);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({map: t, depthTest: false, transparent: true})); s.renderOrder = 20;
  const hgt = .42; s.scale.set(hgt * w / c.height, hgt, 1); return s; }
for (const r of DATA.rooms) { if (['void', 'roof'].includes(r.k) || r.r[2] < 36 || r.r[3] < 30) continue;
  const s = nameSprite(r.n.replace(/ \(.*\)/, '')); s.position.set((r.r[0] + r.r[2] / 2) * IN, (r.ffl + 66) * IN, -(r.r[1] + r.r[3] / 2) * IN); track(s, r.lv, 'name'); }
LAYER.name = 'tNames'; LAYER.beam = 'tCols'; LAYER.site = 'tSite';
const colBase = matOf('col').color.clone();
tog('tNames', refresh);
tog('tCols', v => { matOf('col').color.set(v ? '#B5574B' : colBase); refresh();
  document.querySelectorAll('#plan2d .beams').forEach(g => g.style.display = v ? '' : 'none'); document.querySelectorAll('#plan2d .colm').forEach(c => c.setAttribute('fill', v ? '#B5574B' : '#1C282D')); });
// Colour by (electrical): plain, by switch (what each switch turns on) or by MCB circuit; key in the tab
const PAL = ['#E8590C', '#1971C2', '#2B8A3E', '#AE3EC9', '#C2255C', '#0C8599', '#E67700', '#5F3DC4', '#087F5B', '#A61E4D', '#364FC7', '#5C940D', '#D9480F', '#1864AB'];
const CCTN = {L: 'Lighting + fans', P: 'Power: twin sockets', K: 'Kitchen power (dedicated)', W: 'Wet areas + laundry (RCD)'};
function eColour() { const mode = document.getElementById('colBy').value, sv = [...plan2d.querySelectorAll('svg')].find(x => x.style.display !== 'none') || plan2d.querySelector('svg');
  const leg = document.getElementById('eLeg'), keyOf = el => mode === 'sw' ? el.dataset.sw : el.dataset.cct, cmap = {};
  if (mode !== 'plain' && sv) sv.querySelectorAll('[data-cct]').forEach(el => { const k = keyOf(el); if (k && !(k in cmap)) cmap[k] = PAL[Object.keys(cmap).length % PAL.length]; });
  plan2d.querySelectorAll('[data-cct]').forEach(el => { if (!el.dataset.c0) el.dataset.c0 = el.getAttribute('fill') || ''; if (!el.dataset.s0) el.dataset.s0 = el.getAttribute('stroke') || '';
    if (mode === 'plain' || !keyOf(el)) { el.setAttribute('fill', el.dataset.c0); if (el.dataset.s0) el.setAttribute('stroke', el.dataset.s0); return; }
    const k = keyOf(el); if (!(k in cmap)) { el.setAttribute('fill', el.dataset.c0); if (el.dataset.s0) el.setAttribute('stroke', el.dataset.s0); return; }
    if (el.tagName === 'g') { el.setAttribute('stroke', cmap[k]); } else el.setAttribute('fill', cmap[k]); });
  // 3D and walk: wires, switches, sockets, lights and fans take the same colours
  const ECM = eColour.mats || (eColour.mats = {}), k3 = u => mode === 'sw' ? u.sw : u.cct;
  meshes.forEach(m => { const u = m.userData; if (!u.cct) return; if (mode !== 'plain' && k3(u) && !(k3(u) in cmap)) cmap[k3(u)] = PAL[Object.keys(cmap).length % PAL.length];
    const col = mode === 'plain' ? null : cmap[k3(u)];
    const paint = o => { if (!o.isMesh) return; if (!o.userData.eMat0) o.userData.eMat0 = o.material;
      o.material = col ? (ECM[col + u.k] || (ECM[col + u.k] = u.k === 'lamp' ? new THREE.MeshBasicMaterial({color: col}) : new THREE.MeshStandardMaterial({color: col, emissive: col, emissiveIntensity: .35, roughness: .6}))) : o.userData.eMat0; };
    m.isMesh ? paint(m) : m.traverse(paint); });
  if (mode !== 'plain') { const e = document.getElementById('tElec'); if (!e.checked) { e.checked = true; refresh(); } }
  if (!leg) return; if (mode === 'plain') { leg.style.display = 'none'; return; }
  const lvId = sv?.dataset.level, here = new Set([...(sv?.querySelectorAll('[data-cct]') || [])].map(keyOf));
  const nm = k => mode === 'sw' ? (k === 'path' ? 'Pathway lights (motion sensors + two-way)' : (DATA.rooms.find(r => r.id === k) || {}).n || k) : (CCTN[k.split('-').pop()] || k);
  const lvName = (DATA.levels.find(l => l.id === lvId) || {}).name || '';
  leg.innerHTML = `<b>${lvName}: colour = ${mode === 'sw' ? 'what each switch turns on' : 'which MCB circuit feeds it'}</b>` +
    Object.keys(cmap).filter(k => here.has(k)).map(k => `<div><i style="background:${cmap[k]}"></i>${nm(k)}</div>`).join('') +
    `<div class="muted">Every circuit on an RCD${DATA.rcd || ''}. Concept layout for the electrician to refine.</div>`;
  leg.style.display = ''; }
document.getElementById('colBy').onchange = eColour;
document.querySelectorAll('[data-lv]').forEach(b => b.addEventListener('click', () => setTimeout(eColour, 0)));
tog('tLA', v => document.querySelectorAll('#plan2d .la').forEach(g => g.style.display = v ? '' : 'none'));
// ---------------- site: plot, boundary wall with gate, road, drive ----------------
{ const P = DATA.project.plot || {w: DATA.building.w + 240, d: DATA.building.d + 240, bx: 120, by: 120}, bx = P.bx ?? (P.w - DATA.building.w) / 2, by = P.by ?? (P.d - DATA.building.d) / 2;
  const x0 = -bx, y0 = -by, PW = P.w, PD = P.d, T = 9, H = 54, GATE = 144;
  const mk = (x, y, w, d, z, h, col) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w * IN, h * IN, d * IN), new THREE.MeshStandardMaterial({color: col, roughness: .9}));
    m.position.set((x + w / 2) * IN, (z + h / 2) * IN, -(y + d / 2) * IN); m.receiveShadow = true; m.castShadow = h > 6; m.userData = {x, y, w, d, z, h, k: 'site', lv: '*'}; scene.add(m); meshes.push(m); return m; };
  mk(x0, y0, PW, PD, -1, 1.2, '#B9CFA0');
  const main = (DATA.doors || []).find(d => d.type === 'main'), gc = main ? (main.a + main.b) / 2 : DATA.building.w / 2;
  const side = (s, len, fixed, gate) => { // wall along one plot side, with a gate gap centred at 'gate' (or none)
    const segs = gate == null ? [[0, len]] : [[0, Math.max(0, gate - GATE / 2)], [Math.min(len, gate + GATE / 2), len]];
    for (const [a, b] of segs) { if (b - a < 1) continue;
      if (s === 'S' || s === 'N') mk(x0 + a, fixed, b - a, T, 0, H, '#D9D2C5'); else mk(fixed, y0 + a, T, b - a, 0, H, '#D9D2C5'); } };
  side('S', PW, y0, ROAD === 'S' ? gc - x0 : null); side('N', PW, y0 + PD - T, ROAD === 'N' ? gc - x0 : null);
  side('W', PD, x0, ROAD === 'W' ? PD / 2 : null); side('E', PD, x0 + PW - T, ROAD === 'E' ? PD / 2 : null);
  const RW = 240;
  if (ROAD === 'S') { mk(x0 - 120, y0 - RW, PW + 240, RW, -1, 1.4, '#5B6166'); mk(gc - GATE / 2, y0, GATE, by, -1, 1.6, '#CFC6B5'); }
  if (ROAD === 'N') { mk(x0 - 120, y0 + PD, PW + 240, RW, -1, 1.4, '#5B6166'); mk(gc - GATE / 2, DATA.building.d, GATE, PD - by - DATA.building.d, -1, 1.6, '#CFC6B5'); }
  if (ROAD === 'E') mk(x0 + PW, y0 - 120, RW, PD + 240, -1, 1.4, '#5B6166');
  if (ROAD === 'W') mk(x0 - RW, y0 - 120, RW, PD + 240, -1, 1.4, '#5B6166'); }
tog('tSite', refresh);
// ---------------- cutaway: every floor, walls cut at 4', floors spread apart ----------------
const SPREAD = 3.2;
function applyOff() { const on = cutOn && document.getElementById('tSpread').checked;
  meshes.forEach(m => { const i = lvIds.indexOf(m.userData.lv), want = on && i > 0 ? i * SPREAD : 0, cur = m.userData.off || 0;
    if (want !== cur) { m.position.y += want - cur; m.userData.off = want; } }); }
function setCut(on) { cutOn = on; clearElev();
  meshes.forEach(m => { if (m.userData.off) { m.position.y -= m.userData.off; m.userData.off = 0; } });
  if (on) { only = false; document.getElementById('showBelow').checked = true; curLv = null; refresh(); cut('*', 48);
    document.querySelectorAll('[data-lv]').forEach(x => x.setAttribute('aria-pressed', x.dataset.lv === ''));
    document.querySelectorAll('#plan2d svg').forEach(s => s.style.display = s.dataset.level === lvIds[0] ? '' : 'none'); }
  else { cut('*', null); refresh(); }
  applyOff(); fit(1, .9, 1.1, tgtNow()); }
tog('tCut', setCut); tog('tSpread', () => { if (cutOn) { applyOff(); fit(1, .9, 1.1, tgtNow()); } });
// ---------------- walk pane ----------------
const wv = document.getElementById('wview'), wr = new THREE.WebGLRenderer({antialias: true});
wr.setPixelRatio(Math.min(2, devicePixelRatio)); wv.appendChild(wr.domElement);
Object.assign(wr.domElement.style, {width: '100%', height: '100%', display: 'block'});
const wcam = new THREE.PerspectiveCamera(70, 1, .05, 300);
const wlamp = new THREE.PointLight('#fff8ee', 1.2, 14, 1.2); wcam.add(wlamp); scene.add(wcam);
const solid = meshes.filter(m => ['wall', 'col', 'rail', 'glass', 'stack'].includes(m.userData.k) || (m.userData.k === 'fix' && m.userData.h > 20 && m.userData.z - DATA.levels.find(l => l.id === m.userData.lv).ffl < 20));
const floors = meshes.filter(m => ['floor', 'slab', 'step'].includes(m.userData.k));
const WK = {x: W / 2, y: -1.5, z: 0, yaw: 0, pitch: 0, keys: {}, eye: 64 * IN,
  place(r) { const [x, y, w, d] = r.r; this.x = (x + w / 2) * IN; this.z = -(y + d / 2) * IN; this.y = r.ffl * IN; this.yaw = 0; },
  floorAt(x, z, y0) { let best = -1e9; for (const m of floors) { const b = m.userData; if (!m.visible && b.k !== 'step') {}
      const X = x / IN, Y = -z / IN; if (X < b.x || X > b.x + b.w || Y < b.y || Y > b.y + b.d) continue;
      const top = (b.z + b.h) * IN; if (top <= y0 + 12 * IN && top > best) best = top; } return best; },
  blocked(x, z, y0) { const X = x / IN, Y = -z / IN, R = 9; for (const m of solid) { const b = m.userData;
      if (b.z * IN > y0 + 60 * IN || (b.z + b.h) * IN < y0 + 10 * IN) continue;
      if (b.del) continue; if (X > b.x - R && X < b.x + b.w + R && Y > b.y - R && Y < b.y + b.d + R) return true; }
    const r = R * IN; for (const [lo, hi] of doorBox) { if (hi.y < y0 + .3 || lo.y > y0 + 1.7) continue;
      if (x > lo.x - r && x < hi.x + r && z > lo.z - r && z < hi.z + r) return true; } return false; },
  step(dt) { const s = (this.keys.ShiftLeft ? 2.6 : 1.4) * dt; let dx = 0, dz = 0;
    if (this.keys.KeyW || this.keys.ArrowUp) { dx -= Math.sin(this.yaw) * s; dz -= Math.cos(this.yaw) * s; }
    if (this.keys.KeyS || this.keys.ArrowDown) { dx += Math.sin(this.yaw) * s; dz += Math.cos(this.yaw) * s; }
    if (this.keys.KeyA) { dx -= Math.cos(this.yaw) * s; dz += Math.sin(this.yaw) * s; }
    if (this.keys.KeyD) { dx += Math.cos(this.yaw) * s; dz -= Math.sin(this.yaw) * s; }
    if (this.keys.ArrowLeft) this.yaw += 1.6 * dt; if (this.keys.ArrowRight) this.yaw -= 1.6 * dt;
    doorBoxes(); if (dx && !this.blocked(this.x + dx, this.z, this.y)) this.x += dx;
    if (dz && !this.blocked(this.x, this.z + dz, this.y)) this.z += dz;
    const f = this.floorAt(this.x, this.z, this.y); if (f > -1e8) this.y += (f - this.y) * Math.min(1, dt * 12);
    wcam.position.set(this.x, this.y + this.eye, this.z); wcam.rotation.set(this.pitch, this.yaw, 0, 'YXZ');
    const rm = DATA.rooms.find(r => { const [x, y, w, d] = r.r, X = this.x / IN, Y = -this.z / IN; return Math.abs(r.ffl * IN - this.y) < 1.2 && X >= x && X <= x + w && Y >= y && Y <= y + d; });
    document.getElementById('wHud').textContent = rm ? rm.n + ' · ' + rm.lvName : 'outside'; }};
WK.place(DATA.rooms.find(r => r.k === 'deck') || DATA.rooms[0]); WK.z += 40 * IN;
addEventListener('keydown', e => { if (wpane.classList.contains('on') || document.activeElement === wv) { WK.keys[e.code] = true; if (e.code.startsWith('Arrow') || e.code === 'Space') e.preventDefault(); } });
addEventListener('keyup', e => { WK.keys[e.code] = false; });
// pointer: click the pane to walk (pointer lock + crosshair, mouse looks), Esc to stop; drag-to-look fallback
let drag = null, locked = false, noLock = false; wv.tabIndex = 0;
const wpane = document.getElementById('walkPane'), cvw = wr.domElement;
const setOn = v => { wpane.classList.toggle('on', v); if (!v) for (const k in WK.keys) WK.keys[k] = false; };
wv.addEventListener('pointerdown', e => { if (e.target.closest('button')) return; wv.focus();
  if (matchMedia('(pointer:coarse)').matches || noLock) { drag = [e.clientX, e.clientY]; setOn(true); return; }
  if (locked) { toggleDoor(); return; }
  if (!locked && cvw.requestPointerLock) { const p = cvw.requestPointerLock(); if (p && p.catch) p.catch(() => { noLock = true; setOn(true); }); } });
document.addEventListener('pointerlockchange', () => { locked = document.pointerLockElement === cvw; setOn(locked); });
document.addEventListener('pointerlockerror', () => { noLock = true; setOn(true); });
addEventListener('pointerup', () => drag = null);
addEventListener('mousemove', e => { if (!locked) return; WK.yaw -= e.movementX * .0025; WK.pitch = Math.max(-1.2, Math.min(1.2, WK.pitch - e.movementY * .0022)); });
addEventListener('pointermove', e => { if (!drag || locked) return; WK.yaw -= (e.clientX - drag[0]) * .005; WK.pitch = Math.max(-1.2, Math.min(1.2, WK.pitch - (e.clientY - drag[1]) * .004)); drag = [e.clientX, e.clientY]; });
addEventListener('keydown', e => { if (!wpane.classList.contains('on')) return;
  if (e.code === 'KeyE') toggleDoor(); if (e.code === 'KeyO') allDoors(true); if (e.code === 'KeyC') allDoors(false);
  if (e.code === 'KeyL') document.getElementById('wkLights').click(); });
addEventListener('keydown', e => { if (e.code === 'Escape' && noLock) setOn(false);
  const n = +e.key; if (wpane.classList.contains('on') && n >= 1 && n <= DATA.levels.length) { const L = DATA.levels[n - 1]; const r = DATA.rooms.find(x => x.lv === L.id && x.k === 'stair') || DATA.rooms.find(x => x.lv === L.id); if (r) WK.place(r); } });
document.querySelectorAll('[data-wlv]').forEach(b => b.onclick = () => { const L = b.dataset.wlv; const r = L === 'yard' ? null : DATA.rooms.find(x => x.lv === L && x.k === 'stair') || DATA.rooms.find(x => x.lv === L);
  if (r) WK.place(r); else { WK.place(DATA.rooms.find(x => x.k === 'deck') || DATA.rooms[0]); WK.z += 40 * IN; } });
document.getElementById('wkFull').onclick = () => document.fullscreenElement ? document.exitFullscreen() : wpane.requestFullscreen && wpane.requestFullscreen();
document.querySelectorAll('[data-walk]').forEach(b => b.onclick = () => { const r = DATA.rooms.find(x => x.id === b.dataset.walk); if (r) WK.place(r); wv.focus(); });
// touch joystick: hold the lower half of the walk pane to move forward
wv.addEventListener('touchstart', e => { WK.keys.KeyW = e.touches[0].clientY > wv.getBoundingClientRect().top + wv.clientHeight / 2; }, {passive: true});
wv.addEventListener('touchend', () => WK.keys.KeyW = false);
// walk camera: 90 degree horizontal field of view like a shooter game, whatever the pane shape
function size() { for (const [el, r, c] of [[view, renderer, cam], [wv, wr, wcam]]) { const w = el.clientWidth, h = el.clientHeight; r.setSize(w, h, false); c.aspect = w / Math.max(1, h);
    if (c === wcam) c.fov = Math.min(80, Math.max(50, 2 * Math.atan(Math.tan(Math.PI / 4) / c.aspect) * 180 / Math.PI));
    c.updateProjectionMatrix(); } }
new ResizeObserver(size).observe(view); new ResizeObserver(size).observe(wv); size();
const SVCM = ['pvc', 'cold', 'hot', 'wire', 'exh', 'rw'].map(matOf);
meshes.forEach(m => { if (SVCK.has(m.userData.k)) m.renderOrder = 5; });
let last = performance.now();
function loop(t) { const dt = Math.min(.05, (t - last) / 1000); last = t; stepDoors(dt); WK.step(dt); updLamps();
  for (const f of FANS) f.rotation.y += dt * (lightsOn ? 9 : 2.5);
  renderer.render(scene, cam);
  // the walk sees every floor (ceilings and stairs above), whatever floor the 3D pane isolates
  const vis = meshes.map(m => m.visible), sc = meshes.map(m => m.scale.y), py = meshes.map(m => m.position.y);
  const wl = (DATA.levels.slice().reverse().find(l => WK.y >= l.ffl * IN - .3) || DATA.levels[0]).id;
  meshes.forEach(m => { const k = m.userData.k; m.visible = k !== 'name' && layerOn(k) && !m.userData.del && (!SVCK.has(k) || m.userData.lv === wl || m.userData.lv === '*');
    if (m.isMesh && m.userData.h && (m.scale.y !== 1 || m.userData.off)) { m.scale.y = 1; m.position.y = (m.userData.z + m.userData.h / 2) * IN; } else if (m.userData.off) m.position.y -= m.userData.off; });
  SVCM.forEach(m => { m.depthTest = false; m.transparent = true; m.opacity = .85; }); wr.render(scene, wcam); SVCM.forEach(m => { m.depthTest = true; m.transparent = false; m.opacity = 1; }); meshes.forEach((m, i) => { m.visible = vis[i]; m.scale.y = sc[i]; m.position.y = py[i]; });
  requestAnimationFrame(loop); }
setSun(); showLevel(lvIds[0]); document.querySelector('[data-lv="' + lvIds[0] + '"]')?.setAttribute('aria-pressed', 'true');
requestAnimationFrame(loop);
function cut(lv, hIn) { // cut walls of one level ('*' = every level) at hIn above its floor (plan-style cutaway); hIn=null restores
  meshes.forEach(m => { const b = m.userData; if (!['wall', 'col', 'stack', 'glass'].includes(b.k)) return;
    let top = b.z + b.h; const L = DATA.levels.find(l => l.id === b.lv);
    if (hIn != null && L && (lv === '*' || b.lv === lv)) top = Math.min(top, L.ffl + hIn);
    const h = Math.max(.01, top - b.z); m.scale.y = h / b.h; m.position.y = (b.z + h / 2) * IN + (b.off || 0); m.visible = m.visible && top > b.z;
    if (b.k !== 'glass') { const m0 = b.mat0c || (b.mat0c = m.material), base = Array.isArray(m0) ? m0[0] : m0; // cut face in dark poché
      m.material = top < b.z + b.h - .5 ? (b.matCut || (b.matCut = [base, base, POCHE, base, base, base])) : m0; } }); }
function focus(x, y, lv) { only = true; const c = document.getElementById('showBelow'); if (c) c.checked = false;
  document.querySelector('[data-lv="' + lv + '"]')?.click(); const L = DATA.levels.find(l => l.id === lv);
  cut(lv, 60); ctl.target.set(x * IN, L.ffl * IN, -y * IN); cam.position.set(x * IN + 3, L.ffl * IN + 9, -y * IN + 4.5); ctl.update(); }
window.HD = {setCut, setElev, presets, EDITS: () => EDITS, FX0, setFin, PRESET, pickRoom, showLevel, focus, cut, WK, setSun, setLights, allDoors, toggleDoor, DOORS, play, scene, cam, ctl};

// ---------------- comments: pin notes on the 2D plan, copy them all into the chat ----------------
const CKEY = 'hdcmt:' + DATA.project.name, cmtBar = document.getElementById('cmtBar');
let CMTS = []; try { CMTS = JSON.parse(localStorage.getItem(CKEY) || '[]'); } catch (e) {}
let cPend = null; const cOn = () => document.getElementById('tCmt').checked;
const cSave = () => { try { localStorage.setItem(CKEY, JSON.stringify(CMTS)); } catch (e) {} };
const ftIn = v => `${Math.floor(v / 12)}'-${Math.round(v % 12)}"`;
const lvNm = id => (DATA.levels.find(l => l.id === id) || {}).name || id;
function cWhere(lv, x, y) { const rs = DATA.rooms.filter(r => r.lv === lv && !['void', 'roof'].includes(r.k) && x >= r.r[0] && x <= r.r[0] + r.r[2] && y >= r.r[1] && y <= r.r[1] + r.r[3]);
  rs.sort((a, b) => a.r[2] * a.r[3] - b.r[2] * b.r[3]); return rs[0] ? rs[0].n : (x < 0 || y < 0 || x > DATA.building.w || y > DATA.building.d ? 'outside the house' : 'wall or opening'); }
const cLabel = c => `${lvNm(c.lv)}, ${c.room} (${ftIn(c.x)} from west, ${ftIn(c.y)} from south)`;
function cDraw() { document.querySelectorAll('#plan2d .cpins').forEach(g => g.remove());
  document.querySelectorAll('#plan2d svg').forEach(svg => { const g = document.createElementNS('http://www.w3.org/2000/svg', 'g'); g.setAttribute('class', 'cpins');
    g.style.display = cOn() ? '' : 'none';
    const all = CMTS.map((c, i) => [c, i + 1]).filter(([c]) => c.lv === svg.dataset.level); if (cPend && cPend.lv === svg.dataset.level) all.push([cPend, '+']);
    for (const [c, n] of all) g.insertAdjacentHTML('beforeend', `<g class="cpin"><circle cx="${c.x}" cy="${DATA.building.d - c.y}" r="11"/><text x="${c.x}" y="${DATA.building.d - c.y}">${n}</text><title>${String(c.t || '').replace(/</g, '&lt;')}</title></g>`);
    svg.appendChild(g); });
  const ol = document.getElementById('cList'); ol.innerHTML = '';
  CMTS.forEach((c, i) => { const li = document.createElement('li'); li.innerHTML = `<span class="muted">${cLabel(c)}</span><br>`; li.append(document.createTextNode(c.t));
    const del = document.createElement('button'); del.textContent = 'Delete'; del.onclick = () => { CMTS.splice(i, 1); cSave(); cDraw(); }; li.append(del); ol.append(li); });
  if (!CMTS.length) ol.innerHTML = '<span class="muted">No comments yet.</span>'; }
function cShow() { cmtBar.hidden = !cOn(); plan2d.classList.toggle('commenting', cOn()); if (!cOn()) { cPend = null; document.getElementById('cNew').hidden = true; } cDraw(); }
document.getElementById('tCmt').addEventListener('change', cShow);
plan2d.addEventListener('click', e => { if (!cOn() || e.cancelBubble || (edOn() && e.target.closest('.fu'))) return; const svg = e.target.closest('svg'); if (!svg || e.target.closest('.cpin')) return;
  e.stopPropagation(); const p = toSvg(svg, e), x = Math.round(p.x), y = Math.round(DATA.building.d - p.y), lv = svg.dataset.level;
  cPend = {lv, x, y, room: cWhere(lv, x, y)}; document.getElementById('cNew').hidden = false; document.getElementById('cAt').textContent = 'At ' + cLabel(cPend);
  const t = document.getElementById('cTxt'); t.value = ''; t.focus(); cDraw(); }, true);
const cAdd = () => { const t = document.getElementById('cTxt').value.trim(); if (!cPend || !t) return; CMTS.push({...cPend, t}); cPend = null; cSave();
  document.getElementById('cNew').hidden = true; cDraw(); };
document.getElementById('cAdd').onclick = cAdd;
document.getElementById('cTxt').addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); cAdd(); } if (e.key === 'Escape') document.getElementById('cCancel').click(); });
document.getElementById('cCancel').onclick = () => { cPend = null; document.getElementById('cNew').hidden = true; cDraw(); };
document.getElementById('cClear').onclick = () => { if (CMTS.length && confirm('Delete all ' + CMTS.length + ' comments?')) { CMTS = []; cSave(); cDraw(); } };
document.getElementById('cCopy').onclick = () => { const ta = document.getElementById('cOut');
  ta.value = `Comments on the ${DATA.project.name} design (${CMTS.length}):\n` + CMTS.map((c, i) => `${i + 1}. ${cLabel(c)}: ${c.t}`).join('\n');
  ta.hidden = false; ta.select(); try { navigator.clipboard.writeText(ta.value).catch(() => {}); } catch (e) {}
  document.getElementById('cCopy').textContent = 'Copied ✓'; setTimeout(() => document.getElementById('cCopy').textContent = 'Copy all for chat', 1500); };
cShow(); window.HD.cmts = () => CMTS;
