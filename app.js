const REVIEW_FORM_ACTION_URL = "https://docs.google.com/forms/d/e/1FAIpQLSezjgoihhcW_OZLbt5ictQ8B9p7gepciIOdv0YMVPU1o2gxrg/formResponse";
const FEEDBACK_FORM_ACTION_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfBaDjHXkAsVflYjAsfQ0PqesjUyoB5xa_I1G5v_RKrgJV3rA/formResponse";
const REVIEW_FIELDS = { timestamp: "entry.1083137322", country: "entry.284631955", restaurant: "entry.1872716998", rating: "entry.49189999", note: "entry.942014209" };
const FEEDBACK_FIELDS = { timestamp: "entry.1002726540", topic: "entry.1301236709", restaurant: "entry.744111579", message: "entry.1754693192", contact: "entry.734363110" };

const IMAGES = {
  "Japan": "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?auto=format&fit=crop&w=1000&q=82",
  "China / Taiwan / Hong Kong": "https://images.unsplash.com/photo-1525755662778-989d0524087e?auto=format&fit=crop&w=1000&q=82",
  "Italy": "https://images.unsplash.com/photo-1579751626657-72bc17010498?auto=format&fit=crop&w=1000&q=82",
  "Mexico": "https://images.unsplash.com/photo-1551504734-5ee1c4a1479b?auto=format&fit=crop&w=1000&q=82",
  "India": "https://images.unsplash.com/photo-1585937421612-70a008356fbe?auto=format&fit=crop&w=1000&q=82",
  "Korea": "https://images.unsplash.com/photo-1498654896293-37aacf113fd9?auto=format&fit=crop&w=1000&q=82",
  "Vietnam": "https://images.unsplash.com/photo-1582878826629-29b7ad1cdc43?auto=format&fit=crop&w=1000&q=82",
  "Thailand": "https://images.unsplash.com/photo-1455619452474-d2be8b1e70cd?auto=format&fit=crop&w=1000&q=82",
  "United States": "https://images.unsplash.com/photo-1550547660-d9450f859349?auto=format&fit=crop&w=1000&q=82",
  "Turkey": "https://images.unsplash.com/photo-1544148103-0773bf10d330?auto=format&fit=crop&w=1000&q=82",
  "France": "https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=1000&q=82",
  "default": "https://images.unsplash.com/photo-1514933651103-005eec06c04b?auto=format&fit=crop&w=1000&q=82",
};

const IMAGE_ALT = {
  "Japan": "A bowl of Japanese ramen",
  "China / Taiwan / Hong Kong": "Chinese cuisine",
  "Italy": "Italian cuisine",
  "Mexico": "Mexican cuisine",
  "India": "Indian cuisine",
  "Korea": "Korean cuisine",
  "Vietnam": "Vietnamese cuisine",
  "default": "Restaurant dining table",
};

const RELATIONSHIP_WEIGHTS = {
  "I grew up with this cuisine": 1,
  "My family cooks this cuisine": 0.9,
  "I lived in this country/region for 3+ years": 0.8,
  "I lived there for 1-3 years": 0.6,
  "I speak the language and regularly eat this cuisine": 0.5,
  "I'm a fan and want to leave a general dining note": 0.1,
  "Legacy HomeTaste check": 1,
};

const FEATURED_COUNTRIES = ["Japan", "China / Taiwan / Hong Kong", "Italy", "Mexico", "India", "Korea", "Vietnam"];
const DATA_VERSION = "2026-08-02-production-2";
const state = {
  restaurants: [],
  cuisines: [],
  checks: [],
  selectedCuisine: "all",
  selectedArea: "all",
  query: "",
  sort: "hometaste",
  visibleCount: 24,
  map: null,
  clusters: null,
};

const byId = id => document.getElementById(id);
const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[character]));
const normalizeName = value => String(value || "").toLowerCase().replace(/[^a-z0-9]/g, "");
const imageFor = country => IMAGES[country] || IMAGES.default;
const imageAltFor = country => IMAGE_ALT[country] || IMAGE_ALT.default;
const cuisineFor = country => state.cuisines.find(item => item.country === country) || { country, label: country, flag: "" };
const subtypeFor = restaurant => String(restaurant.cuisine || cuisineFor(restaurant.country).label).split(/[,;/]/).map(value => value.trim().replaceAll("_", " ")).filter(Boolean).slice(0, 3).join(" · ");

function localChecks() {
  try { return JSON.parse(localStorage.getItem("hometasteChecks") || "[]"); }
  catch { return []; }
}

function dedupeChecks(checks) {
  const seen = new Set();
  return checks.filter(check => {
    const key = [check.timestamp || check.created_at, check.restaurant, check.rating ?? check.score, check.note || check.explanation].join("|");
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  }).map(check => ({
    timestamp: check.timestamp || check.created_at || "",
    country: check.country || "",
    restaurant: check.restaurant || "",
    rating: Number(check.rating ?? check.score),
    note: check.note || check.explanation || "",
    nativeNote: check.nativeNote || "",
    relationship: check.relationship || check.relationship_to_cuisine || "Legacy HomeTaste check",
  })).filter(check => check.restaurant && Number.isFinite(check.rating));
}

function checksFor(name) {
  const key = normalizeName(name);
  return state.checks.filter(check => normalizeName(check.restaurant) === key);
}

function scoreFor(name) {
  const checks = checksFor(name);
  const lived = checks.filter(check => (RELATIONSHIP_WEIGHTS[check.relationship] ?? 0.1) >= 0.5);
  if (!lived.length) return { score: null, count: 0, generalCount: checks.length, checks };
  const totalWeight = lived.reduce((sum, check) => sum + (RELATIONSHIP_WEIGHTS[check.relationship] ?? 0.1), 0);
  const rating = lived.reduce((sum, check) => sum + check.rating * (RELATIONSHIP_WEIGHTS[check.relationship] ?? 0.1), 0) / totalWeight;
  return { score: Math.max(0, Math.min(100, Math.round((rating - 1) * 25))), count: lived.length, generalCount: checks.length - lived.length, checks };
}

function filteredRestaurants() {
  const query = state.query.trim().toLowerCase();
  const filtered = state.restaurants.filter(restaurant => {
    const cuisineMatch = state.selectedCuisine === "all" || restaurant.country === state.selectedCuisine;
    const areaMatch = state.selectedArea === "all" || restaurant.area === state.selectedArea;
    const textMatch = !query || [restaurant.name, restaurant.country, cuisineFor(restaurant.country).label, restaurant.cuisine, restaurant.area].join(" ").toLowerCase().includes(query);
    return cuisineMatch && areaMatch && textMatch;
  });
  const distance = restaurant => ((restaurant.latitude - 42.3601) ** 2) + ((restaurant.longitude + 71.0589) ** 2);
  return filtered.sort((left, right) => {
    if (state.sort === "name") return left.name.localeCompare(right.name);
    if (state.sort === "distance") return distance(left) - distance(right);
    const leftScore = scoreFor(left.name);
    const rightScore = scoreFor(right.name);
    return Number(rightScore.count > 0) - Number(leftScore.count > 0) || (rightScore.score ?? -1) - (leftScore.score ?? -1) || rightScore.count - leftScore.count || left.name.localeCompare(right.name);
  });
}

function renderCuisineRail() {
  const counts = Object.fromEntries(FEATURED_COUNTRIES.map(country => [country, state.restaurants.filter(item => item.country === country).length]));
  byId("cuisineRail").innerHTML = FEATURED_COUNTRIES.map(country => {
    const cuisine = cuisineFor(country);
    return `<button class="cuisine-card${state.selectedCuisine === country ? " active" : ""}" type="button" data-country="${escapeHtml(country)}" style="--image:url('${imageFor(country)}')" aria-label="Explore ${escapeHtml(cuisine.label)} restaurants">
      <strong>${escapeHtml(cuisine.flag)} ${escapeHtml(cuisine.label)}</strong><span>${counts[country].toLocaleString()} places</span>
    </button>`;
  }).join("");
}

function scoreMarkup(restaurant) {
  const summary = scoreFor(restaurant.name);
  if (summary.score === null) return `<span class="awaiting">Awaiting a HomeTaste check</span>`;
  return `<span class="score-number">${summary.score} HomeTaste</span><span class="score-count">${summary.count} lived-experience check${summary.count === 1 ? "" : "s"}</span>`;
}

function restaurantCard(restaurant) {
  const cuisine = cuisineFor(restaurant.country);
  return `<article class="restaurant-card" data-restaurant="${escapeHtml(restaurant.name)}">
    <div class="restaurant-image" role="button" tabindex="0" data-action="detail" aria-label="View ${escapeHtml(restaurant.name)} details">
      <img src="${imageFor(restaurant.country)}" alt="${escapeHtml(imageAltFor(restaurant.country))}" loading="lazy" onerror="this.style.display='none'" />
      <span class="cuisine-pill">${escapeHtml(cuisine.flag)} ${escapeHtml(cuisine.label)}</span>
    </div>
    <div class="restaurant-body">
      <h4>${escapeHtml(restaurant.name)}</h4>
      <p class="restaurant-meta">${escapeHtml(restaurant.area)} · ${escapeHtml(subtypeFor(restaurant))}</p>
      <div class="score-row">${scoreMarkup(restaurant)}</div>
      <div class="card-actions"><button type="button" data-action="detail">Details</button><button type="button" data-action="check">Add a Check</button></div>
    </div>
  </article>`;
}

function renderResults({ fitMap = false } = {}) {
  const list = filteredRestaurants();
  const cuisine = state.selectedCuisine === "all" ? null : cuisineFor(state.selectedCuisine);
  byId("resultsHeading").textContent = cuisine ? `${cuisine.label} restaurants` : "All restaurants";
  byId("resultsCount").textContent = `${list.length.toLocaleString()} place${list.length === 1 ? "" : "s"} in the current view`;
  const visible = list.slice(0, state.visibleCount);
  byId("restaurantGrid").innerHTML = visible.length ? visible.map(restaurantCard).join("") : `<div class="empty-state"><h4>No matching restaurants</h4><p>Try a broader cuisine, area, or search term. Nothing has been removed from the complete dataset.</p></div>`;
  byId("loadMore").hidden = visible.length >= list.length;
  if (!byId("loadMore").hidden) byId("loadMore").textContent = `Show more restaurants (${(list.length - visible.length).toLocaleString()} remaining)`;
  renderCuisineRail();
  renderMap(list, fitMap);
}

function initMap() {
  state.map = L.map("map", { zoomControl: true, preferCanvas: true }).setView([42.3601, -71.0789], 11);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' }).addTo(state.map);
  state.clusters = L.markerClusterGroup({ showCoverageOnHover: false, maxClusterRadius: 48, spiderfyOnMaxZoom: true });
  state.map.addLayer(state.clusters);
}

function renderMap(list, fitMap = false) {
  if (!state.map) initMap();
  state.clusters.clearLayers();
  const markers = list.map(restaurant => {
    const cuisine = cuisineFor(restaurant.country);
    const summary = scoreFor(restaurant.name);
    const marker = L.marker([restaurant.latitude, restaurant.longitude], { title: restaurant.name });
    const score = summary.score === null ? "Awaiting a HomeTaste check" : `${summary.score} HomeTaste · ${summary.count} check${summary.count === 1 ? "" : "s"}`;
    marker.bindPopup(`<div class="map-popup"><strong>${escapeHtml(restaurant.name)}</strong><p>${escapeHtml(cuisine.flag)} ${escapeHtml(cuisine.label)} · ${escapeHtml(restaurant.area)}</p><p>${escapeHtml(score)}</p><button type="button" onclick="window.openRestaurant(decodeURIComponent('${encodeURIComponent(restaurant.name)}'))">View details</button></div>`);
    return marker;
  });
  state.clusters.addLayers(markers);
  if ((fitMap || !state.map._hometasteFitted) && markers.length) {
    const bounds = L.latLngBounds(list.map(item => [item.latitude, item.longitude]));
    state.map.fitBounds(bounds, { padding: [28, 28], maxZoom: 13 });
    state.map._hometasteFitted = true;
  }
}

function renderVoices() {
  const grouped = new Map();
  state.checks.forEach(check => {
    const key = normalizeName(check.restaurant);
    if (!grouped.has(key)) grouped.set(key, { name: check.restaurant, checks: [] });
    grouped.get(key).checks.push(check);
  });
  const entries = [...grouped.values()].map(group => {
    const restaurant = state.restaurants.find(item => normalizeName(item.name) === normalizeName(group.name)) || { name: group.name, country: group.checks[0]?.country || "Japan", area: "Boston area", cuisine: cuisineFor(group.checks[0]?.country || "Japan").label };
    return { restaurant, summary: scoreFor(group.name) };
  }).sort((left, right) => (right.summary.score ?? -1) - (left.summary.score ?? -1) || right.summary.count - left.summary.count || left.restaurant.name.localeCompare(right.restaurant.name));

  byId("voicesGrid").innerHTML = entries.slice(0, 6).map((entry, index) => {
    const { restaurant, summary } = entry;
    const note = summary.checks.find(check => check.note)?.note || "A lived-experience check has been recorded; a written detail has not been added yet.";
    return `<article class="voice-card" style="--image:url('${imageFor(restaurant.country)}')">
      <div class="voice-content"><div class="voice-rank">#${index + 1} · ${escapeHtml(cuisineFor(restaurant.country).label)}</div><h3>${escapeHtml(restaurant.name)}</h3><div class="voice-score">${summary.score ?? "New"} HomeTaste · ${summary.count} check${summary.count === 1 ? "" : "s"}</div><p class="voice-note">“${escapeHtml(note)}”</p><button type="button" data-voice-name="${escapeHtml(restaurant.name)}">See all voices</button></div>
    </article>`;
  }).join("") || `<div class="empty-state"><h4>No voices yet</h4><p>Be the first to share a lived-experience check.</p></div>`;
}

function openRestaurant(name) {
  const restaurant = state.restaurants.find(item => normalizeName(item.name) === normalizeName(name));
  const checks = checksFor(name);
  const fallback = checks.length ? { name, country: checks[0].country || "Japan", area: "Boston area", cuisine: cuisineFor(checks[0].country || "Japan").label, source: "HomeTaste check" } : null;
  const item = restaurant || fallback;
  if (!item) return;
  const cuisine = cuisineFor(item.country);
  const summary = scoreFor(name);
  const voiceMarkup = checks.length ? checks.map(check => `<div class="detail-voice"><p>${check.note ? `“${escapeHtml(check.note)}”` : "This check did not include a written note."}</p><span>${escapeHtml(check.relationship)} · ${escapeHtml(check.rating)} / 5</span></div>`).join("") : `<div class="detail-voice"><p>No HomeTaste voice yet. Be the first person with lived experience to add context.</p></div>`;
  byId("restaurantDetail").innerHTML = `<div class="detail-hero" role="img" aria-label="${escapeHtml(imageAltFor(item.country))}" style="--image:url('${imageFor(item.country)}')"></div><div class="detail-body"><p class="eyebrow">${escapeHtml(cuisine.flag)} ${escapeHtml(cuisine.label)}</p><h2>${escapeHtml(item.name)}</h2><div class="detail-meta">${escapeHtml(item.area)} · ${escapeHtml(subtypeFor(item))}</div><div class="detail-score"><strong>${summary.score === null ? "New" : `${summary.score}/100`}</strong><div><b>${summary.score === null ? "Awaiting a HomeTaste check" : "HomeTaste Score"}</b><p>${summary.count} lived-experience check${summary.count === 1 ? "" : "s"}. This is cultural context, not general popularity.</p></div></div><h3>Voices</h3><div class="detail-voices">${voiceMarkup}</div><div class="detail-actions"><button class="button primary" type="button" data-detail-check="${escapeHtml(item.name)}">Add a HomeTaste Check</button><button class="button quiet" type="button" data-detail-report="${escapeHtml(item.name)}">Report issue</button></div></div>`;
  byId("restaurantDialog").showModal();
}
window.openRestaurant = openRestaurant;

function populateCuisineSelects() {
  const options = state.cuisines.map(cuisine => `<option value="${escapeHtml(cuisine.country)}">${escapeHtml(cuisine.flag)} ${escapeHtml(cuisine.label)}</option>`).join("");
  byId("cuisineFilter").innerHTML = `<option value="all">All 52 cuisines</option>${options}`;
  byId("checkCuisine").innerHTML = `<option value="" selected disabled>Choose a cuisine</option>${options}`;
}

function populateCheckRestaurants(country, selectedName = "") {
  const list = state.restaurants.filter(item => !country || item.country === country).sort((left, right) => left.name.localeCompare(right.name));
  byId("checkRestaurant").innerHTML = `<option value="" disabled${selectedName ? "" : " selected"}>Choose a restaurant</option>${list.map(item => `<option${normalizeName(item.name) === normalizeName(selectedName) ? " selected" : ""}>${escapeHtml(item.name)}</option>`).join("")}`;
}

function openCheck(name = "") {
  const restaurant = state.restaurants.find(item => normalizeName(item.name) === normalizeName(name));
  const preferredCountry = restaurant?.country || (state.selectedCuisine !== "all" ? state.selectedCuisine : "");
  byId("checkCuisine").value = preferredCountry;
  populateCheckRestaurants(preferredCountry, restaurant?.name || "");
  byId("checkMessage").textContent = "";
  byId("checkMessage").className = "form-message";
  byId("checkDialog").showModal();
}

function openReport(name = "") {
  byId("issueRestaurant").value = name;
  byId("reportMessage").textContent = "";
  byId("reportMessage").className = "form-message";
  byId("reportDialog").showModal();
}

function applyFilters({ fitMap = true } = {}) {
  state.visibleCount = 24;
  state.selectedCuisine = byId("cuisineFilter").value;
  state.selectedArea = byId("areaFilter").value;
  state.query = byId("restaurantSearch").value;
  state.sort = byId("sortFilter").value;
  renderResults({ fitMap });
}

function selectCuisine(country) {
  state.selectedCuisine = country;
  byId("cuisineFilter").value = country;
  byId("restaurantSearch").value = "";
  byId("siteSearch").value = "";
  state.query = "";
  state.visibleCount = 24;
  renderResults({ fitMap: true });
  byId("explore").scrollIntoView({ behavior: "smooth", block: "start" });
}

function submitHidden(action, data) {
  const form = document.createElement("form");
  form.action = action;
  form.method = "POST";
  form.target = "hiddenSubmitFrame";
  form.hidden = true;
  Object.entries(data).forEach(([name, value]) => {
    const input = document.createElement("input");
    input.name = name;
    input.value = value;
    form.appendChild(input);
  });
  document.body.appendChild(form);
  form.submit();
  window.setTimeout(() => form.remove(), 1500);
}

function bindInteractions() {
  document.querySelectorAll("[data-scroll]").forEach(button => button.addEventListener("click", () => {
    const target = button.dataset.scroll === "top" ? byId("top") : byId(button.dataset.scroll);
    target?.scrollIntoView({ behavior: "smooth", block: "start" });
    byId("mobileNav").classList.remove("open");
    byId("mobileMenu").setAttribute("aria-expanded", "false");
  }));
  document.querySelectorAll("[data-open]").forEach(button => button.addEventListener("click", () => {
    if (button.dataset.open === "checkDialog") openCheck();
    if (button.dataset.open === "reportDialog") openReport();
    byId("mobileNav").classList.remove("open");
  }));
  document.querySelectorAll("[data-close]").forEach(button => button.addEventListener("click", () => byId(button.dataset.close).close()));
  document.querySelectorAll("dialog").forEach(dialog => dialog.addEventListener("click", event => {
    if (event.target === dialog) dialog.close();
  }));
  byId("mobileMenu").addEventListener("click", () => {
    const open = byId("mobileNav").classList.toggle("open");
    byId("mobileMenu").setAttribute("aria-expanded", String(open));
  });
  byId("cuisineRail").addEventListener("click", event => {
    const button = event.target.closest("[data-country]");
    if (button) selectCuisine(button.dataset.country);
  });
  ["cuisineFilter", "areaFilter", "sortFilter"].forEach(id => byId(id).addEventListener("change", () => applyFilters()));
  let searchTimer;
  ["restaurantSearch", "siteSearch"].forEach(id => byId(id).addEventListener("input", event => {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(() => {
      const other = id === "siteSearch" ? byId("restaurantSearch") : byId("siteSearch");
      other.value = event.target.value;
      applyFilters();
      if (id === "siteSearch" && event.target.value) byId("explore").scrollIntoView({ behavior: "smooth", block: "start" });
    }, 180);
  }));
  byId("clearFilters").addEventListener("click", () => {
    byId("cuisineFilter").value = "all";
    byId("areaFilter").value = "all";
    byId("sortFilter").value = "hometaste";
    byId("restaurantSearch").value = "";
    byId("siteSearch").value = "";
    applyFilters();
  });
  byId("showAllCuisines").addEventListener("click", () => {
    byId("explore").scrollIntoView({ behavior: "smooth", block: "start" });
    window.setTimeout(() => byId("cuisineFilter").focus(), 450);
  });
  byId("loadMore").addEventListener("click", () => { state.visibleCount += 24; renderResults(); });
  byId("restaurantGrid").addEventListener("click", event => {
    const card = event.target.closest("[data-restaurant]");
    if (!card) return;
    if (event.target.closest('[data-action="check"]')) openCheck(card.dataset.restaurant);
    else if (event.target.closest('[data-action="detail"]')) openRestaurant(card.dataset.restaurant);
  });
  byId("restaurantGrid").addEventListener("keydown", event => {
    if ((event.key === "Enter" || event.key === " ") && event.target.matches('[data-action="detail"]')) openRestaurant(event.target.closest("[data-restaurant]").dataset.restaurant);
  });
  byId("voicesGrid").addEventListener("click", event => {
    const button = event.target.closest("[data-voice-name]");
    if (button) openRestaurant(button.dataset.voiceName);
  });
  byId("restaurantDetail").addEventListener("click", event => {
    const check = event.target.closest("[data-detail-check]");
    const report = event.target.closest("[data-detail-report]");
    if (check) { byId("restaurantDialog").close(); openCheck(check.dataset.detailCheck); }
    if (report) { byId("restaurantDialog").close(); openReport(report.dataset.detailReport); }
  });
  document.querySelectorAll("[data-mobile-view]").forEach(button => button.addEventListener("click", () => {
    document.querySelectorAll("[data-mobile-view]").forEach(item => item.classList.toggle("active", item === button));
    byId("results").classList.toggle("map-view", button.dataset.mobileView === "map");
    if (button.dataset.mobileView === "map") window.setTimeout(() => state.map.invalidateSize(), 60);
  }));
  byId("score").addEventListener("input", event => { byId("scoreOutput").textContent = `${Number(event.target.value).toFixed(1)} / 5`; });
  byId("checkCuisine").addEventListener("change", event => populateCheckRestaurants(event.target.value));

  byId("checkForm").addEventListener("submit", event => {
    event.preventDefault();
    const explanation = byId("explanation").value.trim();
    const wordCount = explanation.split(/\s+/).filter(Boolean).length;
    if (wordCount < 6 || /^(good|authentic|nice|great)[.!]?$/i.test(explanation)) {
      byId("checkMessage").textContent = "Please add one concrete detail: ingredient, language, clientele, regional style, portion, or service.";
      byId("checkMessage").className = "form-message";
      return;
    }
    const timestamp = new Date().toISOString();
    const relationship = byId("relationship").value;
    const nativeNote = byId("nativeNote").value.trim();
    const rating = Number(byId("score").value);
    const country = byId("checkCuisine").value;
    const restaurant = byId("checkRestaurant").value;
    const structuredNote = `${explanation}\n\nRelationship to cuisine: ${relationship}\nNative language voice: ${nativeNote}\nIngredients ${byId("ingredients").value}, Regional specificity ${byId("regional").value}, People / language ${byId("language").value}, Reminds me of home ${byId("home").value}`;
    const newCheck = { timestamp, country, restaurant, rating, note: explanation, nativeNote, relationship };
    const saved = localChecks();
    saved.push(newCheck);
    localStorage.setItem("hometasteChecks", JSON.stringify(saved));
    state.checks = dedupeChecks([...state.checks, newCheck]);
    submitHidden(REVIEW_FORM_ACTION_URL, { [REVIEW_FIELDS.timestamp]: timestamp, [REVIEW_FIELDS.country]: country, [REVIEW_FIELDS.restaurant]: restaurant, [REVIEW_FIELDS.rating]: rating, [REVIEW_FIELDS.note]: structuredNote });
    byId("checkMessage").textContent = "Thank you — your HomeTaste check was submitted.";
    byId("checkMessage").className = "form-message success";
    renderResults();
    renderVoices();
    window.setTimeout(() => { byId("checkDialog").close(); event.target.reset(); byId("scoreOutput").textContent = "5.0 / 5"; }, 900);
  });

  byId("reportForm").addEventListener("submit", event => {
    event.preventDefault();
    submitHidden(FEEDBACK_FORM_ACTION_URL, { [FEEDBACK_FIELDS.timestamp]: new Date().toISOString(), [FEEDBACK_FIELDS.topic]: byId("issueType").value, [FEEDBACK_FIELDS.restaurant]: byId("issueRestaurant").value, [FEEDBACK_FIELDS.message]: byId("issueMessage").value, [FEEDBACK_FIELDS.contact]: byId("issueContact").value });
    byId("reportMessage").textContent = "Thank you — your report was sent to the HomeTaste team.";
    byId("reportMessage").className = "form-message success";
    window.setTimeout(() => { byId("reportDialog").close(); event.target.reset(); }, 900);
  });
}

async function bootstrap() {
  bindInteractions();
  byId("restaurantGrid").innerHTML = `<div class="skeleton"></div><div class="skeleton"></div>`;
  try {
    const [restaurantResponse, cuisineResponse, checkResponse] = await Promise.all([
      fetch(`/data/restaurants.json?v=${DATA_VERSION}`),
      fetch(`/data/cuisines.json?v=${DATA_VERSION}`),
      fetch("/api/checks").then(response => response.ok ? response : fetch(`/data/checks.json?v=${DATA_VERSION}`)).catch(() => fetch(`/data/checks.json?v=${DATA_VERSION}`)),
    ]);
    if (!restaurantResponse.ok || !cuisineResponse.ok || !checkResponse.ok) throw new Error("A data source did not respond.");
    const [restaurantData, cuisines, checkData] = await Promise.all([restaurantResponse.json(), cuisineResponse.json(), checkResponse.json()]);
    state.restaurants = restaurantData.restaurants;
    state.cuisines = cuisines;
    state.checks = dedupeChecks([...(checkData.checks || []), ...localChecks()]);
    populateCuisineSelects();
    populateCheckRestaurants("");
    byId("dataStatus").textContent = `${state.restaurants.length.toLocaleString()} restaurants · ${state.cuisines.length} cuisines · ${state.checks.length} HomeTaste checks. No source listings are hidden.`;
    renderResults({ fitMap: true });
    renderVoices();
  } catch (error) {
    byId("dataStatus").textContent = "The restaurant atlas could not load. Please refresh in a moment.";
    byId("restaurantGrid").innerHTML = `<div class="empty-state"><h4>We couldn't load the atlas</h4><p>${escapeHtml(error.message)} Nothing has been replaced with a partial sample.</p></div>`;
    byId("loadMore").hidden = true;
  }
}

bootstrap();
