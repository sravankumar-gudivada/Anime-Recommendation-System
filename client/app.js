const API_BASE = window.location.origin.includes("127.0.0.1") || window.location.origin.includes("localhost")
  ? "http://127.0.0.1:5000/api"
  : "/api";
const ITEMS_PER_PAGE = 25;

let currentMode = "title";
let animeDataCache = [];
let currentPage = 1;

document.addEventListener("DOMContentLoaded", () => {
  loadFilterOptions();
  // Perform initial default search
  triggerTitleSearch("Naruto");
});

// Mode Switcher
function switchMode(mode) {
  currentMode = mode;
  document
    .getElementById("tab-title")
    .classList.toggle("active", mode === "title");
  document
    .getElementById("tab-filter")
    .classList.toggle("active", mode === "filter");

  document.getElementById("panel-title-search").style.display =
    mode === "title" ? "block" : "none";
  document.getElementById("panel-filter-search").style.display =
    mode === "filter" ? "block" : "none";
}

// Fetch Filter Options from Backend (app3.ipynb)
async function loadFilterOptions() {
  try {
    const res = await fetch(`${API_BASE}/options`);
    const data = await res.json();
    if (data.status === "success") {
      populateSelect("filter-genre", data.data.genres, "count-genre");
      populateSelect("filter-type", data.data.types, "count-type");
      populateSelect("filter-studio", data.data.studios, "count-studio");
      populateSelect("filter-rating", data.data.ratings, "count-rating");
    }
  } catch (err) {
    console.error("Failed to load filter options:", err);
  }
}

function populateSelect(elementId, items, countId) {
  const select = document.getElementById(elementId);
  const countSpan = document.getElementById(countId);
  if (countSpan) countSpan.textContent = items.length;

  items.forEach((item) => {
    const opt = document.createElement("option");
    opt.value = item;
    opt.textContent = item;
    select.appendChild(opt);
  });
}

// Update Active Filter Mode Indicator
function updateFilterState() {
  const genre = document.getElementById("filter-genre").value;
  const type = document.getElementById("filter-type").value;
  const studio = document.getElementById("filter-studio").value;
  const rating = document.getElementById("filter-rating").value;

  const activeCount = [genre, type, studio, rating].filter(Boolean).length;
  const modeBadge = document.getElementById("mode-badge");

  if (activeCount > 1) {
    modeBadge.textContent = "Hybrid Function";
    modeBadge.className = "mode-tag hybrid";
  } else {
    modeBadge.textContent = "Individual Function";
    modeBadge.className = "mode-tag individual";
  }
}

function resetFilters() {
  document.getElementById("filter-genre").value = "";
  document.getElementById("filter-type").value = "";
  document.getElementById("filter-studio").value = "";
  document.getElementById("filter-rating").value = "";
  updateFilterState();
}

// Autocomplete Search Title
let autocompleteTimeout = null;
function handleAutocomplete(event) {
  const query = event.target.value.trim();
  const listContainer = document.getElementById("autocomplete-list");

  if (event.key === "Enter") {
    listContainer.style.display = "none";
    triggerTitleSearch();
    return;
  }

  if (query.length < 2) {
    listContainer.style.display = "none";
    return;
  }

  clearTimeout(autocompleteTimeout);
  autocompleteTimeout = setTimeout(async () => {
    try {
      const res = await fetch(
        `${API_BASE}/autocomplete?q=${encodeURIComponent(query)}`,
      );
      const data = await res.json();
      if (data.status === "success" && data.results.length > 0) {
        renderAutocompleteList(data.results);
      } else {
        listContainer.style.display = "none";
      }
    } catch (err) {
      console.error("Autocomplete error:", err);
    }
  }, 250);
}

function renderAutocompleteList(items) {
  const listContainer = document.getElementById("autocomplete-list");
  listContainer.innerHTML = "";

  items.forEach((item) => {
    const div = document.createElement("div");
    div.className = "autocomplete-item";
    div.innerHTML = `
      <span class="item-title">${item.name}</span>
      <span class="item-score">${item.score ? "★ " + item.score : ""}</span>
    `;
    div.onclick = () => {
      document.getElementById("title-input").value = item.name;
      listContainer.style.display = "none";
      triggerTitleSearch(item.name);
    };
    listContainer.appendChild(div);
  });

  listContainer.style.display = "block";
}

// Close autocomplete on click outside
document.addEventListener("click", (e) => {
  if (
    !e.target.closest("#title-input") &&
    !e.target.closest("#autocomplete-list")
  ) {
    const listContainer = document.getElementById("autocomplete-list");
    if (listContainer) listContainer.style.display = "none";
  }
});

function getSelectedLimit() {
  const select = document.getElementById("limit-select");
  return select ? parseInt(select.value) || 100 : 100;
}

function handleLimitChange() {
  if (currentMode === "title") {
    triggerTitleSearch();
  } else {
    triggerFilterSearch();
  }
}

// Trigger Search by Title
async function triggerTitleSearch(customTitle = null) {
  const title =
    customTitle || document.getElementById("title-input").value.trim();
  if (!title) return;

  renderSkeletons();
  document.getElementById("results-title").textContent =
    `Recommendations for "${title}"`;

  const limit = getSelectedLimit();
  try {
    const res = await fetch(
      `${API_BASE}/search?title=${encodeURIComponent(title)}&top_n=${limit}`,
    );
    const data = await res.json();

    if (data.status === "success" && data.results.length > 0) {
      animeDataCache = data.results;
      renderPage(1);
    } else {
      animeDataCache = [];
      renderEmptyState(
        data.message || "No anime found matching your title query.",
      );
    }
  } catch (err) {
    console.error("Search API error:", err);
    renderEmptyState(
      "Failed to connect to backend engine. Ensure server.py is running.",
    );
  }
}

// Trigger Filter Search
async function triggerFilterSearch() {
  const genre = document.getElementById("filter-genre").value;
  const type = document.getElementById("filter-type").value;
  const studio = document.getElementById("filter-studio").value;
  const rating = document.getElementById("filter-rating").value;

  if (!genre && !type && !studio && !rating) {
    alert("Please select at least one filter option!");
    return;
  }

  renderSkeletons();
  const limit = getSelectedLimit();

  const payload = {
    genres: genre ? [genre] : [],
    types: type ? [type] : [],
    studios: studio ? [studio] : [],
    ratings: rating ? [rating] : [],
    top_n: limit,
  };

  const activeCount = [genre, type, studio, rating].filter(Boolean).length;
  const titleText =
    activeCount > 1
      ? "Hybrid Filter Recommendations"
      : "Individual Filter Recommendations";
  document.getElementById("results-title").textContent = titleText;

  try {
    const res = await fetch(`${API_BASE}/filter`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (data.status === "success" && data.results.length > 0) {
      animeDataCache = data.results;
      renderPage(1);
    } else {
      animeDataCache = [];
      renderEmptyState(
        data.message || "No anime matched the selected filters.",
      );
    }
  } catch (err) {
    console.error("Filter API error:", err);
    renderEmptyState("Failed to connect to backend server.");
  }
}

// Skeleton Loaders
function renderSkeletons() {
  const grid = document.getElementById("anime-grid");
  const paginationContainer = document.getElementById("pagination-container");
  if (paginationContainer) paginationContainer.style.display = "none";
  grid.innerHTML = "";
  for (let i = 0; i < 12; i++) {
    const skeleton = document.createElement("div");
    skeleton.className = "skeleton-card";
    grid.appendChild(skeleton);
  }
}

// Render Page Function
function renderPage(pageNumber) {
  currentPage = pageNumber;
  const totalItems = animeDataCache.length;
  const totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE);

  if (totalItems === 0) {
    renderEmptyState("No recommendations found.");
    return;
  }

  const startIndex = (pageNumber - 1) * ITEMS_PER_PAGE;
  const endIndex = Math.min(startIndex + ITEMS_PER_PAGE, totalItems);
  const pageItems = animeDataCache.slice(startIndex, endIndex);

  // Update counter
  document.getElementById("results-count").textContent =
    `Showing ${startIndex + 1}–${endIndex} of ${totalItems} results (Page ${pageNumber} of ${totalPages})`;

  renderGridCards(pageItems, startIndex);
  renderPaginationControls(totalPages);

  // Smooth scroll to top of grid
  document
    .getElementById("results-title")
    .scrollIntoView({ behavior: "smooth", block: "start" });
}

// Render Anime Cards Grid Output
function renderGridCards(animeList, baseIndex = 0) {
  const grid = document.getElementById("anime-grid");
  grid.innerHTML = "";

  animeList.forEach((anime, index) => {
    const globalIndex = baseIndex + index;
    const card = document.createElement("div");
    card.className = "anime-card";

    const genresList = (anime.genres || "")
      .split(",")
      .slice(0, 3)
      .map((g) => `<span class="genre-chip">${g.trim()}</span>`)
      .join("");

    const fallbackImg =
      "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=500&auto=format&fit=crop&q=60";

    card.innerHTML = `
      <div class="card-poster">
        <img src="${anime.image_url}" alt="${anime.name}" onerror="this.onerror=null; this.src='${fallbackImg}';">
        <span class="badge-score">★ ${anime.score || "N/A"}</span>
        <span class="badge-type">${anime.type || "ANIME"}</span>
      </div>
      <div class="card-body">
        <div>
          <h3 class="card-title" title="${anime.name}">${anime.name}</h3>
          ${anime.english_name ? `<div class="card-english-title">${anime.english_name}</div>` : ""}
        </div>
        <div class="card-genres">${genresList}</div>
      </div>
    `;

    card.onclick = () => openModal(globalIndex);
    grid.appendChild(card);
  });
}

// Render Pagination Controls (← 1 2 3 4 →)
function renderPaginationControls(totalPages) {
  const container = document.getElementById("pagination-container");
  if (!container) return;

  if (totalPages <= 1) {
    container.style.display = "none";
    return;
  }

  container.innerHTML = "";
  container.style.display = "flex";

  // Previous Arrow Button (←)
  const prevBtn = document.createElement("button");
  prevBtn.className = "pagination-btn pagination-arrow";
  prevBtn.innerHTML = "←";
  prevBtn.disabled = currentPage === 1;
  prevBtn.onclick = () => goToPage(currentPage - 1);
  container.appendChild(prevBtn);

  // Page Numbers Buttons (1, 2, 3, 4...)
  for (let i = 1; i <= totalPages; i++) {
    const pageBtn = document.createElement("button");
    pageBtn.className = `pagination-btn ${i === currentPage ? "active" : ""}`;
    pageBtn.textContent = i;
    pageBtn.onclick = () => goToPage(i);
    container.appendChild(pageBtn);
  }

  // Next Arrow Button (→)
  const nextBtn = document.createElement("button");
  nextBtn.className = "pagination-btn pagination-arrow";
  nextBtn.innerHTML = "→";
  nextBtn.disabled = currentPage === totalPages;
  nextBtn.onclick = () => goToPage(currentPage + 1);
  container.appendChild(nextBtn);
}

function goToPage(page) {
  const totalPages = Math.ceil(animeDataCache.length / ITEMS_PER_PAGE);
  if (page < 1 || page > totalPages) return;
  renderPage(page);
}

function renderEmptyState(message) {
  const grid = document.getElementById("anime-grid");
  const paginationContainer = document.getElementById("pagination-container");
  if (paginationContainer) paginationContainer.style.display = "none";

  document.getElementById("results-count").textContent = "0 results";
  grid.innerHTML = `
    <div class="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
      <h3>No Anime Found</h3>
      <p>${message}</p>
    </div>
  `;
}

// Modal View
function openModal(globalIndex) {
  const anime = animeDataCache[globalIndex];
  if (!anime) return;

  document.getElementById("modal-img").src = anime.image_url;
  document.getElementById("modal-title").textContent = anime.name;
  document.getElementById("modal-eng-title").textContent =
    anime.english_name || "";
  document.getElementById("modal-score").textContent =
    `★ ${anime.score || "N/A"}`;
  document.getElementById("modal-type").textContent = anime.type || "N/A";
  document.getElementById("modal-episodes").textContent =
    `${anime.episodes || "N/A"} Episodes`;
  document.getElementById("modal-genres").textContent =
    `Genres: ${anime.genres || "N/A"}`;
  document.getElementById("modal-studios").textContent =
    `Studios: ${anime.studios || "N/A"} | Rating: ${anime.rating || "N/A"}`;
  document.getElementById("modal-synopsis").textContent =
    anime.synopsis && anime.synopsis !== "UNKNOWN"
      ? anime.synopsis
      : "No detailed synopsis available for this anime.";

  document.getElementById("modal-overlay").classList.add("active");
}

function closeModal(event) {
  if (
    !event ||
    event.target.id === "modal-overlay" ||
    event.target.classList.contains("modal-close")
  ) {
    document.getElementById("modal-overlay").classList.remove("active");
  }
}
