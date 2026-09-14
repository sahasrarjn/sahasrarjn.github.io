/* Charts and audio traces for "Measuring turn detection in OpenAI's Realtime API".
   Reads window.DATA (data.js, generated from the turnprobe runs). Every value a tooltip
   shows is also in the figure's data table. */

(function () {
  "use strict";
  var DATA = window.DATA;
  if (!DATA) return;

  var NS = "http://www.w3.org/2000/svg";
  function S(tag, attrs, parent) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function T(tag, attrs, text, parent) { var e = S(tag, attrs, parent); e.textContent = text; return e; }
  function H(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function secs(ms, d) { return (ms / 1000).toFixed(d == null ? 2 : d) + " s"; }
  function pct(v) { return Math.round(v * 100) + "%"; }

  var SET = {
    server:   { label: "server_vad · 500 ms", color: "var(--s-server)" },
    sem_high: { label: "semantic_vad · high", color: "var(--s-high)" },
    sem_auto: { label: "semantic_vad · auto", color: "var(--s-auto)" },
    sem_low:  { label: "semantic_vad · low",  color: "var(--s-low)" }
  };
  var ORDER = ["server", "sem_high", "sem_auto", "sem_low"].filter(function (k) { return DATA.pause[k]; });

  // ------------------------------------------------------------- tooltip
  var tip = document.getElementById("tip");
  function showTip(evt, title, rows) {
    tip.replaceChildren(H("div", "t", title));
    rows.forEach(function (r) {
      var row = H("div", "r");
      if (r.color) { var i = H("i"); i.style.background = r.color; row.appendChild(i); }
      row.appendChild(H("b", null, r.value));
      if (r.label) row.appendChild(H("span", null, r.label));
      tip.appendChild(row);
    });
    tip.hidden = false;
    var w = tip.offsetWidth, h = tip.offsetHeight, x = evt.clientX + 14, y = evt.clientY + 14;
    if (x + w > innerWidth - 8) x = evt.clientX - w - 14;
    if (y + h > innerHeight - 8) y = evt.clientY - h - 14;
    tip.style.left = x + "px"; tip.style.top = y + "px";
  }
  function hideTip() { tip.hidden = true; }

  function legend(items) {
    var el = H("div", "legend");
    items.forEach(function (it) {
      var s = H("span"), i = H("i", it.kind); i.style.background = it.color;
      s.appendChild(i); s.appendChild(document.createTextNode(it.label)); el.appendChild(s);
    });
    return el;
  }
  function dataTable(head, rows) {
    var d = H("details"), sum = H("summary", null, "Data table"), wrap = H("div", "dtable"), t = H("table");
    var tr = H("tr"); head.forEach(function (h) { tr.appendChild(H("th", null, h)); });
    var th = H("thead"); th.appendChild(tr); t.appendChild(th);
    var tb = H("tbody");
    rows.forEach(function (r) { var row = H("tr"); r.forEach(function (c) { row.appendChild(H("td", null, String(c))); }); tb.appendChild(row); });
    t.appendChild(tb); wrap.appendChild(t); d.appendChild(sum); d.appendChild(wrap);
    return d;
  }
  function mount(fig, nodes) {
    var cap = fig.querySelector("figcaption");
    nodes.forEach(function (n) { fig.insertBefore(n, cap); });
  }

  // ------------------------------------------------------------- pause sweep panels
  (function () {
    var fig = document.getElementById("fig-pauses");
    if (!fig) return;
    fig.classList.add("viz");
    var grid = H("div", "multiples"), rows = [];
    var W = 300, Hh = 200, L = 36, R = 10, Tp = 12, B = 38;
    var pauses = DATA.pause[ORDER[0]].map(function (p) { return p.pause; });
    var pmin = 0, pmax = Math.max.apply(null, pauses) + 150;
    function x(p) { return L + (p - pmin) / (pmax - pmin) * (W - L - R); }
    function y(v) { return Tp + (1 - v) * (Hh - Tp - B); }
    ORDER.forEach(function (key) {
      var pts = DATA.pause[key], panel = H("div"), h4 = H("h4"), dot = H("i");
      dot.style.background = SET[key].color; h4.appendChild(dot); h4.appendChild(document.createTextNode(SET[key].label));
      panel.appendChild(h4);
      var svg = S("svg", { viewBox: "0 0 " + W + " " + Hh, role: "img", "aria-label": SET[key].label + ": turn ended and heard cut-in by pause length" });
      [0, 0.5, 1].forEach(function (g) {
        S("line", { x1: L, x2: W - R, y1: y(g), y2: y(g), "class": g === 0 ? "ax" : "gl" }, svg);
        T("text", { x: L - 6, y: y(g) + 3.5, "text-anchor": "end", "class": "tx" }, pct(g), svg);
      });
      pts.forEach(function (p) { T("text", { x: x(p.pause), y: Hh - B + 15, "text-anchor": "middle", "class": "tx" }, String(p.pause / 1000), svg); });
      T("text", { x: (L + W - R) / 2, y: Hh - 5, "text-anchor": "middle", "class": "at" }, "pause (s)", svg);
      function line(field, color, area) {
        var q = pts.map(function (p) { return [x(p.pause), y(p[field] / p.n)]; });
        var d = "M" + q.map(function (a) { return a.join(","); }).join("L");
        if (area) S("path", { d: d + "L" + q[q.length - 1][0] + "," + y(0) + "L" + q[0][0] + "," + y(0) + "Z", fill: color, opacity: 0.1 }, svg);
        S("path", { d: d, fill: "none", stroke: color, "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
        q.forEach(function (a) { S("circle", { cx: a[0], cy: a[1], r: 4, fill: color, stroke: "var(--paper-2)", "stroke-width": 2 }, svg); });
      }
      line("split", "var(--ended)", true);
      line("audible", "var(--heard)", false);
      var cross = S("line", { x1: 0, x2: 0, y1: Tp, y2: y(0), "class": "cross", visibility: "hidden" }, svg);
      var hit = S("rect", { x: L, y: Tp, width: W - L - R, height: y(0) - Tp, "class": "hit", tabindex: 0 }, svg);
      function nearest(cx) { return pts.reduce(function (a, b) { return Math.abs(x(b.pause) - cx) < Math.abs(x(a.pause) - cx) ? b : a; }); }
      function show(evt, p) {
        cross.setAttribute("x1", x(p.pause)); cross.setAttribute("x2", x(p.pause)); cross.setAttribute("visibility", "visible");
        showTip(evt, SET[key].label + " · " + p.pause + " ms pause · n=" + p.n, [
          { color: "var(--ended)", value: p.split + "/" + p.n, label: "turn ended (95% CI " + pct(p.split_ci[0]) + "–" + pct(p.split_ci[1]) + ")" },
          { color: "var(--heard)", value: p.audible + "/" + p.n, label: "heard it (95% CI " + pct(p.audible_ci[0]) + "–" + pct(p.audible_ci[1]) + ")" }
        ]);
      }
      hit.addEventListener("pointermove", function (evt) { var r = svg.getBoundingClientRect(); show(evt, nearest((evt.clientX - r.left) * W / r.width)); });
      hit.addEventListener("pointerleave", function () { cross.setAttribute("visibility", "hidden"); hideTip(); });
      hit.addEventListener("blur", function () { cross.setAttribute("visibility", "hidden"); hideTip(); });
      hit.addEventListener("focus", function () { var r = svg.getBoundingClientRect(), p = pts[pts.length - 1]; show({ clientX: r.left + r.width * x(p.pause) / W, clientY: r.top + 20 }, p); });
      panel.appendChild(svg); grid.appendChild(panel);
      pts.forEach(function (p) { rows.push([SET[key].label, p.pause, p.split + "/" + p.n, p.audible + "/" + p.n]); });
    });
    mount(fig, [legend([
      { kind: "kl", color: "var(--ended)", label: "Server ended your turn during the pause" },
      { kind: "kl", color: "var(--heard)", label: "You heard the model before you finished" }
    ]), grid]);
    fig.appendChild(dataTable(["Setting", "Pause (ms)", "Turn ended", "Heard it"], rows));
  })();

  // ------------------------------------------------------------- reply-gap strip
  (function () {
    var fig = document.getElementById("fig-waits");
    if (!fig) return;
    fig.classList.add("viz");
    var keys = ORDER, W = 960, rowH = 76, L = 170, R = 24, Tp = 24, B = 40;
    var Hh = Tp + keys.length * rowH + B;
    var maxv = Math.max.apply(null, keys.map(function (k) { return DATA.gaps[k].max; }));
    var xmax = Math.ceil(maxv / 1000) * 1000;
    function x(v) { return L + v / xmax * (W - L - R); }
    var svg = S("svg", { viewBox: "0 0 " + W + " " + Hh, role: "img", "aria-label": "Reply gap per trial by setting" });
    for (var s = 0; s <= xmax / 1000; s++) {
      S("line", { x1: x(s * 1000), x2: x(s * 1000), y1: Tp - 6, y2: Hh - B, "class": s === 0 ? "ax" : "gl" }, svg);
      T("text", { x: x(s * 1000), y: Hh - B + 15, "text-anchor": "middle", "class": "tx" }, s + " s", svg);
    }
    S("rect", { x: x(0), y: Tp - 6, width: Math.max(2, x(200) - x(0)), height: Hh - B - Tp + 6, fill: "var(--user)", opacity: 0.15 }, svg);
    T("text", { x: x(200) + 5, y: Tp - 10, "class": "dl2" }, "people ≈ 0.2 s", svg);
    T("text", { x: (L + W - R) / 2, y: Hh - 5, "text-anchor": "middle", "class": "at" }, "silence from the end of your sentence to the first audible reply", svg);
    keys.forEach(function (key, i) {
      var cy = Tp + i * rowH + rowH / 2, g = DATA.gaps[key];
      S("circle", { cx: 8, cy: cy - 4, r: 4.5, fill: SET[key].color }, svg);
      T("text", { x: 20, y: cy, "class": "dl" }, SET[key].label, svg);
      g.values.forEach(function (v, j) {
        var jit = ((j * 7919) % 23 - 11) * 1.3;
        S("circle", { cx: x(v), cy: cy + jit, r: 3.6, fill: SET[key].color, stroke: "var(--paper-2)", "stroke-width": 1.4 }, svg);
        var hc = S("circle", { cx: x(v), cy: cy + jit, r: 8, fill: "transparent" }, svg);
        hc.addEventListener("pointermove", function (evt) { showTip(evt, SET[key].label, [{ color: SET[key].color, value: secs(v), label: "one trial" }]); });
        hc.addEventListener("pointerleave", hideTip);
      });
      S("line", { x1: x(g.p50), x2: x(g.p50), y1: cy - 20, y2: cy + 20, stroke: "var(--ink)", "stroke-width": 2 }, svg);
      T("text", { x: x(g.p50), y: cy - 24, "text-anchor": "middle", "class": "dl" }, "p50 " + secs(g.p50), svg);
      S("circle", { cx: x(g.p90), cy: cy + 22, r: 4, fill: "var(--paper-2)", stroke: "var(--ink)", "stroke-width": 1.5 }, svg);
      T("text", { x: x(g.p90) + 8, y: cy + 26, "class": "dl2" }, "p90 " + secs(g.p90), svg);
    });
    var wrap = H("div"); wrap.appendChild(svg);
    mount(fig, [legend(keys.map(function (k) { return { kind: "kd", color: SET[k].color, label: SET[k].label }; })), wrap]);
    fig.appendChild(dataTable(["Setting", "Trials", "p10", "Median", "p90", "Max"], keys.map(function (k) {
      var g = DATA.gaps[k]; return [SET[k].label, g.values.length, secs(g.p10), secs(g.p50), secs(g.p90), secs(g.max)];
    })));
  })();

  // ------------------------------------------------------------- anatomy
  (function () {
    var fig = document.getElementById("fig-anatomy");
    if (!fig) return;
    fig.classList.add("viz");
    var keys = ORDER, W = 960, rowH = 44, L = 170, R = 90, Tp = 8, B = 30, bar = 22;
    var Hh = Tp + keys.length * rowH + B;
    var tot = Math.max.apply(null, keys.map(function (k) { return DATA.anatomy[k].decision + DATA.anatomy[k].generation; }));
    var xmax = Math.ceil(tot / 1000) * 1000;
    function x(v) { return L + v / xmax * (W - L - R); }
    var svg = S("svg", { viewBox: "0 0 " + W + " " + Hh, role: "img", "aria-label": "Median decision and generation time by setting" });
    for (var s = 0; s <= xmax / 1000; s++) {
      S("line", { x1: x(s * 1000), x2: x(s * 1000), y1: Tp, y2: Hh - B, "class": s === 0 ? "ax" : "gl" }, svg);
      T("text", { x: x(s * 1000), y: Hh - B + 15, "text-anchor": "middle", "class": "tx" }, s + " s", svg);
    }
    var rows = [];
    keys.forEach(function (key, i) {
      var a = DATA.anatomy[key], cy = Tp + i * rowH + rowH / 2, top = cy - bar / 2;
      T("text", { x: 0, y: cy + 4, "class": "dl" }, SET[key].label, svg);
      var segs = [["Deciding you're done", a.decision, "var(--ended)", "#fff"], ["Producing the first audio", a.generation, "var(--model)", "#1A201E"]];
      var acc = 0;
      segs.forEach(function (sg, j) {
        var x0 = x(acc) + (j ? 1 : 0), x1 = x(acc + sg[1]) - (j ? 0 : 1), w = x1 - x0, r = 4;
        var d = j === segs.length - 1
          ? "M" + x0 + "," + top + "H" + (x1 - r) + "Q" + x1 + "," + top + " " + x1 + "," + (top + r) + "V" + (top + bar - r) + "Q" + x1 + "," + (top + bar) + " " + (x1 - r) + "," + (top + bar) + "H" + x0 + "Z"
          : "M" + x0 + "," + top + "H" + x1 + "V" + (top + bar) + "H" + x0 + "Z";
        var p = S("path", { d: d, fill: sg[2] }, svg), label = secs(sg[1]);
        if (w > label.length * 7 + 14) T("text", { x: x0 + w / 2, y: cy + 4, "text-anchor": "middle", "class": "dl", style: "fill:" + sg[3] }, label, svg);
        p.addEventListener("pointermove", function (evt) { showTip(evt, SET[key].label, [{ color: sg[2], value: label, label: sg[0] }]); });
        p.addEventListener("pointerleave", hideTip);
        acc += sg[1];
      });
      T("text", { x: x(acc) + 8, y: cy + 4, "class": "dl" }, "≈ " + secs(a.gap), svg);
      rows.push([SET[key].label, secs(a.decision), secs(a.generation), secs(a.playout), secs(a.gap)]);
    });
    var wrap = H("div"); wrap.appendChild(svg);
    mount(fig, [legend([
      { kind: "kr", color: "var(--ended)", label: "Deciding you're done" },
      { kind: "kr", color: "var(--model)", label: "Producing the first audio" }
    ]), wrap]);
    fig.appendChild(dataTable(["Setting", "Deciding (median)", "First audio (median)", "Playback (median)", "Total gap (median)"], rows));
  })();

  // ------------------------------------------------------------- overlap dot plot
  (function () {
    var fig = document.getElementById("fig-overlap");
    if (!fig) return;
    fig.classList.add("viz");
    var order = ["mmhm", "yeah", "okay", "right", "stop", "repeat", "yeah_but"];
    var keys = ["server", "sem_auto"], M = DATA.meta;
    var W = 960, rowH = 34, L = 280, R = 30, Tp = 30, B = 40, gap = 22;
    var Hh = Tp + order.length * rowH + gap + B;
    var maxv = Math.max.apply(null, DATA.overlap.map(function (r) { return r.reply_gap_ms || 0; }));
    var xmax = Math.max(6000, Math.ceil(maxv / 1000) * 1000);
    function x(v) { return L + v / xmax * (W - L - R); }
    function rowY(i) { return Tp + i * rowH + rowH / 2 + (i >= 4 ? gap : 0); }
    var svg = S("svg", { viewBox: "0 0 " + W + " " + Hh, role: "img", "aria-label": "Silence before the model resumes, by what the user said" });
    for (var s = 0; s <= xmax / 1000; s++) {
      S("line", { x1: x(s * 1000), x2: x(s * 1000), y1: Tp - 8, y2: Hh - B, "class": s === 0 ? "ax" : "gl" }, svg);
      T("text", { x: x(s * 1000), y: Hh - B + 15, "text-anchor": "middle", "class": "tx" }, s + " s", svg);
    }
    T("text", { x: (L + W - R) / 2, y: Hh - 5, "text-anchor": "middle", "class": "at" }, "silence after the user's clip, before the model speaks again", svg);
    T("text", { x: 0, y: Tp - 12, "class": "tx" }, "BACKCHANNEL · SHOULD KEEP GOING", svg);
    T("text", { x: 0, y: rowY(4) - rowH / 2 - 6, "class": "tx" }, "INTERRUPTION · SHOULD STOP", svg);
    var rows = [];
    order.forEach(function (clip, i) {
      var cy = rowY(i);
      T("text", { x: 0, y: cy + 4, "class": "dl" }, "“" + M.clips[clip].text.replace(/\.$/, "") + "”", svg);
      keys.forEach(function (k, kk) {
        var rs = DATA.overlap.filter(function (r) { return r.clip === clip && r.setting === k; });
        rs.forEach(function (r) {
          if (r.reply_gap_ms == null) return;
          var yy = cy + (kk ? 6 : -6);
          S("circle", { cx: x(r.reply_gap_ms), cy: yy, r: 4.5, fill: SET[k].color, stroke: "var(--paper-2)", "stroke-width": 2 }, svg);
          var hc = S("circle", { cx: x(r.reply_gap_ms), cy: yy, r: 10, fill: "transparent" }, svg);
          hc.addEventListener("pointermove", function (evt) {
            showTip(evt, SET[k].label + " · voice " + r.voice, [
              { color: SET[k].color, value: secs(r.reply_gap_ms), label: "until it spoke again" },
              { value: Math.round(r.stop_latency_ms) + " ms", label: "to stop talking" }
            ]);
          });
          hc.addEventListener("pointerleave", hideTip);
        });
        rows.push([SET[k].label, M.clips[clip].text, rs.filter(function (r) { return r.outcome !== "kept_talking"; }).length + "/" + rs.length,
          rs.map(function (r) { return Math.round(r.stop_latency_ms) + " ms"; }).join(", "),
          rs.map(function (r) { return r.reply_gap_ms == null ? "–" : secs(r.reply_gap_ms); }).join(", ")]);
      });
    });
    var wrap = H("div"); wrap.appendChild(svg);
    mount(fig, [legend(keys.map(function (k) { return { kind: "kd", color: SET[k].color, label: SET[k].label }; })), wrap]);
    fig.appendChild(dataTable(["Setting", "User said", "Stopped", "Time to stop", "Silence before resuming"], rows));
  })();

  // ------------------------------------------------------------- audio traces
  (function () {
    var byName = {};
    DATA.examples.forEach(function (e) { byName[e.name] = e; });
    function ev(e, type, n) { return e.events.filter(function (x) { return x.type === type; })[n || 0]; }
    function stim(e) { return DATA.meta.stimuli[e.meta.stimulus] || {}; }

    var SPEC = {
      "audible-cut-in": {
        title: "Cut off mid-number",
        user: function (e) { return ["“" + stim(e).a + "”", "“" + stim(e).b + "”"]; },
        events: function (e) {
          var st = ev(e, "user_speech_stopped", 0), tr = ev(e, "client_truncate", 0);
          return [
            [st.t_ms, "e", "Server decides you're done, " + secs(st.t_ms - e.marks["A.end"]) + " into a " + secs(e.meta.pause_ms, 1) + " pause"],
            [ev(e, "first_audio", 0).t_ms, "m", "The model starts talking while the caller is mid-number"],
            [tr.t_ms, "u", "You resume; the server hears you " + Math.round(tr.t_ms - e.marks["B.start"]) + " ms later and playback is cut"],
            [ev(e, "user_speech_stopped", 1).t_ms, "e", "The real end of your turn"],
            [ev(e, "first_audio", 1).t_ms, "m", "The actual answer"]
          ];
        },
        take: "The model could tell the user wasn't done — it says so. Server VAD had already handed it the turn."
      },
      "hidden-split": {
        title: "The turn you never heard end",
        user: function (e) { return ["“" + stim(e).a + "”", "“" + stim(e).b + "”"]; },
        events: function (e) {
          var st = ev(e, "user_speech_stopped", 0), resume = ev(e, "user_speech_started", 1);
          return [
            [st.t_ms, "e", "Server decides you're done, " + secs(st.t_ms - e.marks["A.end"]) + " into a " + secs(e.meta.pause_ms, 1) + " pause"],
            [ev(e, "response_created", 0).t_ms, "e", "It starts building a reply"],
            [resume.t_ms, "u", "You resume; " + Math.round(resume.t_ms - e.marks["B.start"]) + " ms later it cancels the reply, before any audio"],
            [ev(e, "user_speech_stopped", 1).t_ms, "e", "The real end of your turn"],
            [ev(e, "first_audio", 0).t_ms, "m", "First audio of the real reply"]
          ];
        },
        take: "Nothing audible went wrong, so this trial counts as clean. Underneath, one sentence became two turns and a discarded response."
      },
      "patient-wait": {
        title: function (e) { return Math.round(e.analysis.final_gap_ms / 1000) + " seconds for Canberra"; },
        user: function (e) { return ["“" + stim(e).a + "”", "“" + stim(e).b + "”"]; },
        events: function (e) {
          var st = ev(e, "user_speech_stopped", 0);
          return [
            [e.marks["B.end"], "u", "You finish a complete question"],
            [st.t_ms, "e", "Semantic VAD decides you're done, " + secs(st.t_ms - e.marks["B.end"]) + " later"],
            [ev(e, "first_audio", 0).t_ms, "m", "First audio, heard " + secs(e.analysis.final_gap_ms) + " after you stopped"]
          ];
        },
        take: "The question was finished. After the pause, “Australia is?” on its own sounded like a fragment."
      },
      "yeah-stops-it": {
        title: "One “yeah” costs four seconds",
        user: function (e) { return ["“" + DATA.meta.question + "”", "“" + DATA.meta.clips[e.meta.clip].text + "”"]; },
        events: function (e) {
          var tr = ev(e, "client_truncate", 0), st = ev(e, "user_speech_stopped", 1);
          return [
            [e.marks["model.onset"], "m", "The model starts its walkthrough"],
            [e.marks["X.start"], "u", "You say “yeah”, meaning keep going"],
            [tr.t_ms, "e", "Server reports speech; playback stops " + Math.round(tr.t_ms - e.marks["X.start"]) + " ms after you started"],
            [st.t_ms, "e", "Semantic VAD waits to see if “yeah” was the start of something: " + secs(st.t_ms - e.marks["X.end"])],
            [ev(e, "first_audio", 1).t_ms, "m", "The model resumes after " + secs(e.analysis.reply_gap_ms) + " of silence"]
          ];
        },
        take: "A listener's “yeah” is the cheapest signal in conversation. Here it cost the user four seconds of dead air."
      }
    };

    Array.prototype.forEach.call(document.querySelectorAll("figure.trace"), function (fig) {
      var name = fig.getAttribute("data-example"), e = byName[name], spec = SPEC[name];
      if (!e || !spec) return;
      var items;
      try { items = spec.events(e).filter(function (it) { return it[0] != null; }); }
      catch (err) { items = []; }
      // the window comes from the data build, which cuts the audio clip to exactly this span:
      // audio time 0 = w0, so the player clock, axis labels and event times all agree
      var w0 = e.window[0], w1 = e.window[1];
      function rel(t) { return t - w0; }

      var top = H("div", "tr-top");
      top.appendChild(H("span", "tr-title", typeof spec.title === "function" ? spec.title(e) : spec.title));
      top.appendChild(H("span", "tr-sub", SET[e.setting].label + " · recorded trial"));
      fig.appendChild(top);

      var W = 960, L = 60, R = 10, Hh = 212, lanes = { u: [12, 68], m: [128, 184] };
      function x(t) { return L + (t - w0) / (w1 - w0) * (W - L - R); }
      var svg = S("svg", { viewBox: "0 0 " + W + " " + Hh, role: "img", "aria-label": "Recorded user and model audio with server events", "class": "viz" });
      T("text", { x: 0, y: 44, "class": "lane" }, "USER", svg);
      T("text", { x: 0, y: 102, "class": "lane" }, "SERVER", svg);
      T("text", { x: 0, y: 160, "class": "lane" }, "MODEL", svg);
      function env(arr, lane, cls) {
        var mid = (lane[0] + lane[1]) / 2, half = (lane[1] - lane[0]) / 2, step = 20;
        var i0 = Math.max(0, Math.floor(w0 / step)), i1 = Math.min(arr.length - 1, Math.ceil(w1 / step));
        var topPath = "", bot = [];
        for (var i = i0; i <= i1; i++) {
          var px = x(i * step).toFixed(1), a = Math.max(0.015, arr[i]) * half;
          topPath += (i === i0 ? "M" : "L") + px + "," + (mid - a).toFixed(1);
          bot.push(px + "," + (mid + a).toFixed(1));
        }
        S("path", { d: topPath + "L" + bot.reverse().join("L") + "Z", "class": cls }, svg);
      }
      env(e.user, lanes.u, "env-u");
      env(e.model, lanes.m, "env-m");
      S("line", { x1: L, x2: W - R, y1: 194, y2: 194, "class": "ax" }, svg);
      for (var t = w0; t <= w1; t += 1000) {
        T("text", { x: x(t), y: 208, "text-anchor": "middle", "class": "tx" }, ((t - w0) / 1000) + " s", svg);
      }
      var colors = { m: "var(--model)", u: "var(--user)", e: "var(--ended)" }, prev = -Infinity;
      items.forEach(function (it, i) {
        var tx = x(it[0]), dx = Math.max(tx, prev + 21);
        prev = dx;
        S("line", { x1: tx, x2: tx, y1: lanes.u[0], y2: lanes.m[1], "class": "mark" }, svg);
        if (dx !== tx) S("line", { x1: tx, x2: dx, y1: 98, y2: 98, "class": "mark" }, svg);
        S("circle", { cx: dx, cy: 98, r: 9, fill: colors[it[1]], stroke: "var(--paper-2)", "stroke-width": 2 }, svg);
        T("text", { x: dx, y: 101.5, "class": "evn", fill: it[1] === "m" ? "#1A201E" : "#fff" }, String(i + 1), svg);
      });
      var head = S("line", { x1: x(w0), x2: x(w0), y1: 6, y2: 194, "class": "head", visibility: "hidden" }, svg);
      fig.appendChild(svg);

      var body = H("div", "tr-body"), left = H("div"), right = H("div");
      var audio = H("audio"); audio.controls = true; audio.preload = "none"; audio.src = "audio/" + name + ".mp3";
      audio.addEventListener("timeupdate", function () {
        var ms = w0 + audio.currentTime * 1000;
        if (ms >= w0 && ms <= w1) { head.setAttribute("x1", x(ms)); head.setAttribute("x2", x(ms)); head.setAttribute("visibility", "visible"); }
        else head.setAttribute("visibility", "hidden");
      });
      left.appendChild(audio);
      var ol = H("ol", "ev");
      items.forEach(function (it, i) {
        var li = H("li"), n = H("span", "n", String(i + 1));
        n.style.background = colors[it[1]]; if (it[1] === "m") n.style.color = "#1A201E";
        li.appendChild(n); li.appendChild(H("span", "t", secs(rel(it[0])))); li.appendChild(H("span", null, it[2]));
        ol.appendChild(li);
      });
      left.appendChild(ol);

      var said = H("div", "said");
      spec.user(e).forEach(function (u) { said.appendChild(H("div", "who", "User")); said.appendChild(H("p", null, u)); });
      e.responses.forEach(function (r) {
        var who = H("div", "who", "Model");
        var label = r.status !== "cancelled" ? "played" : (r.heard ? "cut off mid-reply" : "cancelled before any audio");
        who.appendChild(H("span", "chip " + (r.status === "cancelled" ? "bad" : "ok"), label));
        said.appendChild(who);
        var txt = (r.text || "").replace(/\s+/g, " ").trim();
        said.appendChild(H("p", null, txt ? "“" + (txt.length > 200 ? txt.slice(0, 200) + "…" : txt) + "”" : "(cancelled before any words were generated)"));
      });
      right.appendChild(said);
      right.appendChild(H("div", "take", spec.take));
      body.appendChild(left); body.appendChild(right);
      fig.appendChild(body);
    });
  })();
})();
