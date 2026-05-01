/* app.js — Smart Agriculture AI Frontend Logic */

// ── Preset values for quick testing ────────────────────────────────────────
const PRESETS = {
  rice:   { N: 90,  P: 42,  K: 43,  temperature: 20.9, humidity: 82.0, ph: 6.5,  rainfall: 202.9 },
  coffee: { N: 101, P: 18,  K: 19,  temperature: 25.5, humidity: 58.9, ph: 6.8,  rainfall: 158.0 },
  maize:  { N: 78,  P: 48,  K: 22,  temperature: 22.6, humidity: 65.0, ph: 6.2,  rainfall: 84.5  },
  banana: { N: 100, P: 82,  K: 50,  temperature: 27.4, humidity: 80.9, ph: 5.8,  rainfall: 105.5 },
};

// Emoji map for crop names
const CROP_EMOJI = {
  rice: "🌾", maize: "🌽", banana: "🍌", apple: "🍎", grapes: "🍇",
  orange: "🍊", mango: "🥭", papaya: "🍈", watermelon: "🍉", muskmelon: "🍈",
  coconut: "🥥", coffee: "☕", cotton: "🌿", jute: "🌿", lentil: "🫘",
  chickpea: "🫘", kidneybeans: "🫘", blackgram: "🫘", mungbean: "🫘",
  mothbeans: "🫘", pigeonpeas: "🫘", pomegranate: "🍎",
};

function cropEmoji(name) {
  return CROP_EMOJI[name.toLowerCase()] || "🌱";
}

// ── DOM refs ────────────────────────────────────────────────────────────────
const form        = document.getElementById("predict-form");
const submitBtn   = document.getElementById("submit-btn");
const btnText     = document.getElementById("btn-text");
const btnSpinner  = document.getElementById("btn-spinner");

const emptyState  = document.getElementById("empty-state");
const resultsDiv  = document.getElementById("results");
const errorState  = document.getElementById("error-state");
const errorMsg    = document.getElementById("error-msg");

// ── Preset buttons ──────────────────────────────────────────────────────────
document.querySelectorAll(".preset-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const key = btn.dataset.preset;
    const p   = PRESETS[key];
    if (!p) return;
    Object.entries(p).forEach(([field, val]) => {
      const el = document.getElementById(field);
      if (el) el.value = val;
    });
    // Clear any previous validation styles
    document.querySelectorAll(".field input").forEach(i => i.classList.remove("invalid"));
  });
});

// ── Form validation ─────────────────────────────────────────────────────────
function validateForm() {
  const fields = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"];
  let valid = true;
  fields.forEach(id => {
    const el = document.getElementById(id);
    const v  = el.value.trim();
    if (v === "" || isNaN(parseFloat(v))) {
      el.classList.add("invalid");
      valid = false;
    } else {
      el.classList.remove("invalid");
    }
  });
  return valid;
}

// ── Show / hide states ──────────────────────────────────────────────────────
function showLoading() {
  btnText.classList.add("hidden");
  btnSpinner.classList.remove("hidden");
  submitBtn.disabled = true;

  emptyState.classList.add("hidden");
  resultsDiv.classList.add("hidden");
  errorState.classList.add("hidden");
}

function showError(msg) {
  btnText.classList.remove("hidden");
  btnSpinner.classList.add("hidden");
  submitBtn.disabled = false;

  errorMsg.textContent = msg;
  errorState.classList.remove("hidden");
  resultsDiv.classList.add("hidden");
  emptyState.classList.add("hidden");
}

function showResults() {
  btnText.classList.remove("hidden");
  btnSpinner.classList.add("hidden");
  submitBtn.disabled = false;

  errorState.classList.add("hidden");
  emptyState.classList.add("hidden");
  resultsDiv.classList.remove("hidden");
}

// ── Render helpers ──────────────────────────────────────────────────────────
function fmtUSD(n) {
  return "$" + Number(n).toLocaleString("en-US", { maximumFractionDigits: 0 });
}
function fmtNum(n, dec = 1) {
  return Number(n).toLocaleString("en-US", { maximumFractionDigits: dec });
}

function renderPrimary(primary) {
  // Crop name + confidence
  document.getElementById("primary-crop-name").textContent =
    cropEmoji(primary.crop) + " " + capitalize(primary.crop);

  const conf = primary.confidence;
  document.getElementById("primary-conf").textContent = conf + "%";
  const bar = document.getElementById("conf-bar");
  // Animate width after a tick
  bar.style.width = "0%";
  setTimeout(() => { bar.style.width = conf + "%"; }, 50);

  // Stats row
  const statsEl = document.getElementById("primary-stats");
  statsEl.innerHTML = `
    <div class="stat-box">
      <div class="stat-label">Est. Yield</div>
      <div class="stat-value">${fmtNum(primary.yield_kg_ha, 0)}</div>
      <div class="stat-unit">kg / ha</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">Market Price</div>
      <div class="stat-value">${fmtUSD(primary.price_usd_tonne)}</div>
      <div class="stat-unit">USD / tonne</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">Est. Profit</div>
      <div class="stat-value">${fmtUSD(primary.profit_usd_ha)}</div>
      <div class="stat-unit">USD / ha</div>
    </div>
  `;
}

function renderTop3(top3) {
  const grid = document.getElementById("top3-grid");
  grid.innerHTML = top3.map(item => `
    <div class="top3-card ${item.rank === 1 ? "rank-1" : ""}">
      <div class="rank-badge">${item.rank}</div>
      <div class="top3-info">
        <div class="crop-name">${cropEmoji(item.crop)} ${capitalize(item.crop)}</div>
        <div class="crop-detail">
          Confidence: <strong>${item.confidence}%</strong>
          &nbsp;·&nbsp; Yield: <strong>${fmtNum(item.yield_kg_ha, 0)} kg/ha</strong>
          &nbsp;·&nbsp; Price: <strong>${fmtUSD(item.price_usd_tonne)}/t</strong>
        </div>
      </div>
      <div class="top3-profit">
        <div class="profit-val">${fmtUSD(item.profit_usd_ha)}</div>
        <div class="profit-sub">USD / ha</div>
      </div>
    </div>
  `).join("");
}

function renderBarChart(top3) {
  const chart  = document.getElementById("bar-chart");
  const maxVal = Math.max(...top3.map(i => i.profit_usd_ha));

  chart.innerHTML = top3.map(item => {
    const pct = maxVal > 0 ? (item.profit_usd_ha / maxVal) * 100 : 0;
    return `
      <div class="bar-row ${item.rank === 1 ? "rank-1" : ""}">
        <div class="bar-label">${cropEmoji(item.crop)} ${capitalize(item.crop)}</div>
        <div class="bar-bg">
          <div class="bar-fill" style="width:0%" data-width="${pct.toFixed(1)}%"></div>
        </div>
        <div class="bar-value">${fmtUSD(item.profit_usd_ha)}</div>
      </div>
    `;
  }).join("");

  // Animate bars after paint
  setTimeout(() => {
    chart.querySelectorAll(".bar-fill").forEach(el => {
      el.style.width = el.dataset.width;
    });
  }, 80);
}

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}


// ── Render AI explanation ───────────────────────────────────────────────────
function renderExplanation(expl) {
  if (!expl) return;

  document.getElementById("expl-summary").textContent = expl.summary || "";

  const ul = document.getElementById("expl-details");
  ul.innerHTML = (expl.details || [])
    .map(d => `<li>${d}</li>`)
    .join("");

  const tipEl = document.getElementById("expl-tip");
  if (expl.tip) {
    tipEl.innerHTML = `<span class="tip-icon">💡</span> <strong>Tip:</strong> ${expl.tip}`;
    tipEl.classList.remove("hidden");
  } else {
    tipEl.classList.add("hidden");
  }
}

// ── Main form submit ────────────────────────────────────────────────────────
form.addEventListener("submit", async (e) => {
  e.preventDefault();

  if (!validateForm()) {
    showError("Please fill in all fields with valid numeric values.");
    return;
  }

  showLoading();

  const payload = {
    N:           parseFloat(document.getElementById("N").value),
    P:           parseFloat(document.getElementById("P").value),
    K:           parseFloat(document.getElementById("K").value),
    temperature: parseFloat(document.getElementById("temperature").value),
    humidity:    parseFloat(document.getElementById("humidity").value),
    ph:          parseFloat(document.getElementById("ph").value),
    rainfall:    parseFloat(document.getElementById("rainfall").value),
  };

  try {
    const res  = await fetch("/predict", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(payload),
    });

    const data = await res.json();

    if (!res.ok) {
      showError(data.error || `Server error ${res.status}`);
      return;
    }

    // Render all sections
    renderPrimary(data.primary);
    renderTop3(data.top3);
    renderBarChart(data.top3);
    renderExplanation(data.explanation);
    showResults();

    // Smooth scroll to results on mobile
    resultsDiv.scrollIntoView({ behavior: "smooth", block: "start" });

  } catch (err) {
    showError("Network error — is the Flask server running on port 5000?");
    console.error(err);
  }
});
