// FasalKavach frontend: map picker, form submit, and rendering of the API result.

const $ = (id) => document.getElementById(id);
const b = window.PUNJAB_BOUNDS;

// ---------- Map ----------
// If the map library fails to load (bad network), the form still works with a place name.
let map = null;
let marker = null;
if (window.L) {
  map = L.map("map").fitBounds([[b.lat_min, b.lon_min], [b.lat_max, b.lon_max]]);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18, attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);
  map.on("click", onMapClick);
} else {
  $("map").innerHTML = "<p class='hint'>Map unavailable - please type your village or town name.</p>";
}

function onMapClick(e) {
  const { lat, lng } = e.latlng;
  if (lat < b.lat_min || lat > b.lat_max || lng < b.lon_min || lng > b.lon_max) {
    alert("Please pick a location inside Punjab.");
    return;
  }
  marker ? marker.setLatLng(e.latlng) : (marker = L.marker(e.latlng).addTo(map));
  $("lat").value = lat.toFixed(4);
  $("lon").value = lng.toFixed(4);
  $("place_name").value = "";
  $("place_name").placeholder = `Map point ${lat.toFixed(3)}, ${lng.toFixed(3)}`;
}

// Typing a place name clears the map point
$("place_name").addEventListener("input", () => {
  $("lat").value = ""; $("lon").value = "";
  if (marker) { map.removeLayer(marker); marker = null; }
});

$("crop").addEventListener("change", (e) => {
  const label = e.target.selectedOptions[0].dataset.dateLabel;
  $("date-label").textContent = label.charAt(0).toUpperCase() + label.slice(1);
});

// ---------- Submit ----------
$("advise-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  const body = { costs: {} };
  for (const [k, v] of form.entries()) {
    if (k.startsWith("cost:")) body.costs[k.slice(5)] = v;
    else body[k] = v;
  }

  const btn = $("submit-btn");
  btn.disabled = true;
  btn.textContent = "Checking weather, prices and risks…";
  $("results").hidden = false;
  $("error").hidden = true;
  $("output").hidden = true;

  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 120000);
    const resp = await fetch("/api/advise", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    clearTimeout(timer);
    const data = await resp.json().catch(() => ({ error: "Server returned an invalid response" }));
    if (!resp.ok || data.error) throw new Error(data.error || `Request failed (${resp.status})`);
    render(data);
  } catch (err) {
    $("error").textContent = err.name === "AbortError"
      ? "This is taking too long. Please check your connection and try again."
      : err.message;
    $("error").hidden = false;
  } finally {
    btn.disabled = false;
    btn.textContent = "Get advice";
    $("results").scrollIntoView({ behavior: "smooth" });
  }
});

// ---------- Rendering ----------
const rs = (n) => "₹" + Math.round(n).toLocaleString("en-IN");
const pct = (p) => Math.round(p * 100) + "%";
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function render(d) {
  $("output").hidden = false;
  const adv = d.advisory;
  $("headline").textContent = adv.headline;
  $("advisory-text").textContent = adv.advisory_text;
  $("answer").hidden = !adv.answer_to_question;
  $("answer").textContent = adv.answer_to_question || "";
  $("mode-badge").textContent = d.mode === "agent" ? "AI agent · verified" : "Rule-based";
  $("mode-badge").className = "badge " + (d.mode === "agent" ? "ok" : "muted");

  $("warnings").innerHTML = (d.warnings || []).map((w) => `<div class="warning">⚠ ${esc(w)}</div>`).join("");

  const s = d.stage, p = d.price, dec = d.decision;
  const chips = [
    `📍 ${esc(d.location.name)}${d.location.district ? ", " + esc(d.location.district) : ""}`,
    `🌱 ${esc(s.crop_label)}: ${esc(s.stage.replace(/_/g, " "))} (day ${s.days_since_planting})`,
    `💰 ${rs(p.price_rs_per_q)}/q (${esc(p.basis)})`,
    `📦 Crop value ${rs(dec.crop_value_rs_per_acre)}/acre`,
  ];
  if (d.soil) chips.push(`💧 Topsoil moisture ${d.soil.topsoil_moisture_m3m3} m³/m³`);
  $("chips").innerHTML = chips.map((c) => `<span class="chip">${c}</span>`).join("");

  $("actions").innerHTML = dec.actions.length ? dec.actions.map((a) => `
    <div class="action ${a.recommended ? "rec" : "notrec"}">
      <div class="action-head">
        <strong>${a.recommended ? "✅" : "➖"} ${esc(a.label)}</strong>
        <span class="net">${a.net_benefit_rs_per_acre >= 0 ? "+" : ""}${rs(a.net_benefit_rs_per_acre)}/acre</span>
      </div>
      <div class="bar"><span>Benefit ${rs(a.benefit_rs_per_acre)}</span><span>Cost ${rs(a.cost_rs_per_acre)}</span></div>
      <small>${esc(a.explanation)}</small>
    </div>`).join("") : "<p>No protective actions apply at this crop stage.</p>";

  $("forecast-source").textContent = d.forecast ? d.forecast.source : "";
  renderRiskTable(d.risks);

  $("losses").innerHTML = dec.event_losses.length ? dec.event_losses.map((l) => `
    <div class="loss-row"><span>${esc(l.label)}</span>
    <span>${pct(l.probability_7d)} × ${pct(l.damage_fraction)} damage → <strong>${rs(l.expected_loss_rs_per_acre)}/acre</strong></span></div>`).join("")
    + `<div class="loss-row total"><span>Total (${dec.area_acres} acres)</span><strong>${rs(dec.expected_loss_7d_total_rs)}</strong></div>`
    : "<p>This crop stage is not sensitive to the forecast events.</p>";
  if (dec.soil_note) $("losses").innerHTML += `<p class="hint">${esc(dec.soil_note)}</p>`;

  $("trace-count").textContent = d.trace.length;
  $("trace").innerHTML = d.trace.map((t) => `
    <li class="${t.ok ? "" : "fail"}"><code>${esc(t.tool)}</code>
      ${t.input ? `<small>${esc(JSON.stringify(t.input))}</small>` : ""}
      ${t.ok ? "✓" : "✗ " + esc(t.result || "")}
    </li>`).join("");

  $("sources").innerHTML = d.sources.map((s) =>
    `<li><strong>${esc(s.used_for)}:</strong> ${esc(s.source)}${s.fetched_at ? ` <small>(${esc(s.fetched_at)}${s.stale ? ", cached" : ""})</small>` : ""}</li>`).join("");
}

function renderRiskTable(risks) {
  const keys = Object.keys(risks || {});
  if (!keys.length) { $("risk-table").innerHTML = "<tr><td>No forecast data</td></tr>"; return; }
  const days = risks[keys[0]].daily.slice(0, 7).map((x) => x.date);
  const head = "<tr><th>Event</th>" + days.map((dt) =>
    `<th>${new Date(dt + "T00:00").toLocaleDateString("en-IN", { weekday: "short", day: "numeric" })}</th>`).join("") + "</tr>";
  const rows = keys.map((k) => {
    const r = risks[k];
    const cells = days.map((dt) => {
      const day = r.daily.find((x) => x.date === dt);
      if (!day) return "<td>–</td>";
      const level = day.probability >= 0.6 ? "high" : day.probability >= 0.3 ? "mid" : day.probability > 0 ? "low" : "none";
      return `<td class="p-${level}" title="median ${day.median_value}">${pct(day.probability)}</td>`;
    }).join("");
    return `<tr><td>${esc(r.label)}</td>${cells}</tr>`;
  }).join("");
  $("risk-table").innerHTML = head + rows;
}
