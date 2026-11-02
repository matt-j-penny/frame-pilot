// hf-anim.js: THE REGISTRY as code (animations.md + creative-moves.md, executable).
//
// Copy this file into projects/<job>/hf-graphics/gfx/ beside render.sh, and start every hand
// comp from comp-scaffold.html, which loads it as  <script src="hf-anim.js"></script>
// (bare name — the render base is the gfx/ root; a "../" form trips hyperframes'
// invalid_parent_traversal_in_asset_path lint). After gsap, before the comp's own script.
// Nothing in here is retyped into a comp.
//
// Why: eleven hand comps on your-job each re-typed the same four helper blocks and each
// got a different subset wrong, nine of the ten motion defects the review rounds found were
// re-typings (2026-09-02). A comp now DECLARES its rate and calls the registry:
//
//   const DUR = 4.642;
//   const H = HF.init({fps: 30000/1001, stepFps: 12, dur: DUR});
//   //  fps MUST equal the base footage rate (ffprobe the raw) and the render's FPS=:
//   //  30000/1001 for 29.97, 24000/1001 for 23.976.
//   //  stepFps: 12  on a bg-DARK full-screen (rendered STEP_FPS=12: pop/slam/countUp re-express
//   //  themselves in 83 ms states and flash refuses); omit it on overlays and bg-light full-screens.
//   const {tl, F, SF, pop, slam, flash, riseIn, riseOut, exit, slideIn, slideOut, float, arrow, drawOn, countUp, reveal, DRAW} = H;
//   ...
//   H.finish();   // pins DUR, rewinds, exposes window.__timelines.main
//
// Every number below is the registry's. Change it in the owning doc FIRST, then here, never in a
// comp: animations.md for the in/out presets and the arrow, creative-moves.md move 2 for the float
// and 4d for the reveal bursts.
window.HF = (function () {
  const REG = {
    rise:  {in: {dist: 22, dur: 0.55, ease: 'power3.out'}, out: {dist: 18, dur: 0.35, ease: 'power2.in'}},
    slide: {in: {dur: 0.75, ease: 'power2.out'}, out: {dur: 0.38, ease: 'power3.inOut'}},
    pop:   {from: 0.90, over: 1.10, frames: 3, ease: 'power2.out'},   // then set(1.00) on frame 4
    slam:  {from: 1.16, frames: 7, ease: 'power2.out'},
    slamSteps: [1.16, 1.09, 1.03, 1.00],                              // the 12 fps re-expression (four 83 ms states)
    flash: [[0, 0.2], [1, 0], [3, 0.2], [4, 0], [5, 0.2], [6, 1]],
    float: {subtle: [6, 8, 1.25, 0.95], medium: [10, 16, 1.35, 1.05]}, // [travel x, travel y, period x, period y]
    draw:  9,                                                          // frames a stroke takes to arrive
    arrow: {len: 2.27, half: 1.33, sink: 0.27},                        // head geometry in stroke widths
    burst: [3, 5, 2, 4, 6, 3, 2, 5, 4, 3, 6, 2],                        // reveal burst sizes: fixed, irregular, never a modulo
  };
  const AXIS = {bottom: ['y', 1], top: ['y', -1], left: ['x', -1], right: ['x', 1]};
  const FRAME = {x: 1920, y: 1080};

  function init(o) {
    if (!o || !o.fps || !o.dur) throw new Error('HF.init needs {fps, dur[, stepFps]}');
    const fps = o.fps, stepFps = o.stepFps || null, DUR = o.dur;
    const F = 1 / fps;                                   // one TIMELINE frame
    const SF = stepFps ? 1 / stepFps : F;                // one RENDERED step (83 ms at 12 fps)
    const q = t => stepFps ? Math.round(t * stepFps) / stepFps : t;   // snap a time to the step grid
    const tl = gsap.timeline({paused: true});

    // ── the scale family (OBJECTS: props, chips, icons, the mascot, flow nodes) ──
    const pop = (el, at, extra) => {
      const first = Object.assign({opacity: 1, scale: REG.pop.from}, extra || {});
      if (stepFps) {                                     // 0.90 → 1.10 → 1.00, one 83 ms state each
        const a = q(at); tl.set(el, first, a); tl.set(el, {scale: REG.pop.over}, a + SF); tl.set(el, {scale: 1}, a + 2 * SF); return;
      }
      tl.set(el, first, at);
      tl.to(el, {scale: REG.pop.over, duration: REG.pop.frames * F, ease: REG.pop.ease}, at);
      tl.set(el, {scale: 1}, at + (REG.pop.frames + 1) * F);
    };
    const slam = (el, at) => {
      if (stepFps) { const a = q(at); REG.slamSteps.forEach((s, i) => tl.set(el, i ? {scale: s} : {opacity: 1, scale: s}, a + i * SF)); return; }
      tl.set(el, {opacity: 1, scale: REG.slam.from}, at);
      tl.to(el, {scale: 1, duration: REG.slam.frames * F, ease: REG.slam.ease}, at);
    };
    const flash = (el, at) => {
      if (stepFps) throw new Error('HF: flash is banned on a 12 fps graphic (its single-frame gaps vanish), use pop or slam');
      for (const [f, op] of REG.flash) tl.set(el, {opacity: op}, at + f * F);
    };

    // ── the nudge family (TYPE, cards, panels), opacity CUTS in, the travel is the entrance ──
    const riseIn = (el, at, dist = REG.rise.in.dist, dur = REG.rise.in.dur, ease = REG.rise.in.ease) => {
      tl.set(el, {opacity: 1}, at); tl.fromTo(el, {y: dist}, {y: 0, duration: dur, ease}, at);
    };
    const riseOut = (el, at, dist = REG.rise.out.dist) => {   // RELATIVE: rises from wherever it rests
      tl.to(el, {y: '-=' + dist, opacity: 0, duration: REG.rise.out.dur, ease: REG.rise.out.ease}, at);
    };
    // the standard tail: riseOut landing two frames before DUR, hard-kill on the last frame
    const exit = (el, at) => {
      const t = at === undefined ? DUR - REG.rise.out.dur - 2 * F : at;
      riseOut(el, t); tl.set(el, {opacity: 0}, DUR - F);
    };

    // ── the slide family (OFF SCREEN only) ──
    const slideIn = (el, at, from, dist) => { const [ax, sg] = AXIS[from], c = REG.slide.in;
      tl.set(el, {opacity: 1}, at); tl.fromTo(el, {[ax]: sg * (dist || FRAME[ax])}, {[ax]: 0, duration: c.dur, ease: c.ease}, at); };
    const slideOut = (el, at, to, dist) => { const [ax, sg] = AXIS[to], c = REG.slide.out;
      tl.to(el, {[ax]: sg * (dist || FRAME[ax]), duration: c.dur, ease: c.ease}, at); };

    // ── THE FLOAT: hold life, on a position:absolute;inset:0 WRAPPER, 0 → DUR, every time ──
    const float = (target, t0, t1, preset) => {
      const p = REG.float[preset]; if (!p) throw new Error('HF: float preset must be subtle or medium');
      const [AX, AY, PX, PY] = p;
      const leg = (prop, A, per) => { let cur = 0, out = true;
        for (let t = t0; t < t1 - 0.02; t += per) { const rem = Math.min(per, t1 - t);
          cur += ((out ? A : 0) - cur) * (rem / per);            // the last leg scales with the time left: never a truncated excursion
          tl.to(target, {[prop]: cur, duration: rem, ease: 'sine.inOut'}, t); out = !out; } };
      leg('x', AX, PX); leg('y', -AY, PY);
    };

    // ── the arrow: head COMPUTED from the path's end tangent, sized off stroke-width ──
    const DRAW = REG.draw;
    const arrow = (sel) => {                              // call ONCE, after any bloom clone
      for (const svg of document.querySelectorAll(sel)) {
        const p = svg.querySelector('path'), head = svg.querySelector('.head');
        const L = p.getTotalLength(); const sw = parseFloat(getComputedStyle(p).strokeWidth) || 10;
        const p1 = p.getPointAtLength(L), p0 = p.getPointAtLength(Math.max(0, L - 8));
        let tx = p1.x - p0.x, ty = p1.y - p0.y; const n = Math.hypot(tx, ty) || 1; tx /= n; ty /= n;
        const px = -ty, py = tx, A = REG.arrow;
        const tip = {x: p1.x + tx * A.len * sw, y: p1.y + ty * A.len * sw};
        const b = {x: p1.x - tx * A.sink * sw, y: p1.y - ty * A.sink * sw}; const h = A.half * sw;
        if (head) head.setAttribute('points', [[tip.x, tip.y], [b.x + px * h, b.y + py * h], [b.x - px * h, b.y - py * h]]
          .map(c => c[0].toFixed(1) + ',' + c[1].toFixed(1)).join(' '));
        p.style.strokeDasharray = L; p.style.strokeDashoffset = L;
      }
    };
    const drawOn = (sel, at) => {
      tl.set(sel, {opacity: 1}, at);
      tl.to(sel + ' path', {strokeDashoffset: 0, duration: DRAW * F, ease: 'power2.out'}, at);
      tl.set(sel + ' .head', {opacity: 1}, at + (DRAW - 1) * F);
    };

    // ── content reveals: DISCRETE states on the beat grid, zero frame PINNED, never onUpdate ──
    const BEAT = stepFps ? SF : 2 * F;                   // one ~12 fps beat
    const countUp = (sel, at, dur, to, fmt, from, ease) => {
      fmt = fmt || (v => String(v)); from = from || 0; ease = ease || (p => 1 - Math.pow(1 - p, 3));
      const N = Math.max(1, Math.round(dur / BEAT));
      tl.set(sel, {innerText: fmt(from)}, 0);            // PIN THE ZERO FRAME
      for (let i = 1; i <= N; i++) tl.set(sel, {innerText: fmt(Math.round(from + (to - from) * ease(i / N)))}, at + i * BEAT);
      tl.set(sel, {innerText: fmt(to)}, at + N * BEAT);
      return at + N * BEAT;
    };
    // reveal(sel, at, text): bursts of 2-6 words, one beat each, DOUBLE on punctuation; returns the
    // time the text is complete, so the caller budgets the hold backwards (creative-moves.md 4d).
    const reveal = (sel, at, text, opts) => {
      opts = opts || {}; const words = text.split(' '); const sizes = opts.pattern || REG.burst;
      tl.set(sel, {innerText: ''}, 0);                   // PIN THE ZERO FRAME
      let i = 0, t = at, k = 0;
      while (i < words.length) {
        i = Math.min(words.length, i + sizes[k % sizes.length]); k++;
        const shown = words.slice(0, i).join(' ');
        tl.set(sel, {innerText: shown}, t);
        t += /[.,;:!?]$/.test(shown) ? 2 * BEAT : BEAT;
      }
      return t;
    };

    const finish = () => { tl.set({}, {}, DUR); tl.progress(0); window.__timelines = window.__timelines || {}; window.__timelines.main = tl; };

    return {tl, F, SF, DUR, BEAT, REG, pop, slam, flash, riseIn, riseOut, exit, slideIn, slideOut, float, arrow, drawOn, DRAW, countUp, reveal, finish};
  }
  return {init, REG};
})();
