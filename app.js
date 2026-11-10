const SEGMENT_COLORS = {
  "Champions": "#c1d94e",
  "Regular Customers": "#62cbb8",
  "Occasional Buyers": "#8198e8",
  "At-Risk Customers": "#f28a69"
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[char]));
}

function number(value) {
  return new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 }).format(Number(value || 0));
}

function money(value, digits = 0) {
  return new Intl.NumberFormat("en-GB", {
    style: "currency", currency: "GBP", maximumFractionDigits: digits,
    minimumFractionDigits: digits
  }).format(Number(value || 0));
}

async function request(url, options = {}) {
  const response = await fetch(url, options);
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) throw new Error(data?.error || `Request failed (${response.status})`);
  return data;
}

function segmentCard(segment, index, large = false) {
  const color = SEGMENT_COLORS[segment.name] || "#c1d94e";
  return `
    <article class="segment-card" style="--segment-color:${color}">
      <div class="segment-top"><span class="segment-number">SEGMENT / 0${index + 1}</span><span class="segment-count">${number(segment.customers)} customers</span></div>
      <h3>${escapeHtml(segment.name)}</h3>
      <p>${escapeHtml(segment.summary)}</p>
      <div class="segment-metric"><span>Avg. customer value</span><strong>${money(segment.avgMonetary)}</strong></div>
      ${large ? `<span class="segment-advice">${escapeHtml(segment.action)}</span>` : ""}
    </article>`;
}

function renderSegments(segments) {
  const ordered = ["Champions", "Regular Customers", "Occasional Buyers", "At-Risk Customers"];
  const sorted = [...segments].sort((a, b) => ordered.indexOf(a.name) - ordered.indexOf(b.name));
  $("#overview-segments").innerHTML = sorted.map((segment, index) => segmentCard(segment, index)).join("") || "<div class='loading-state'>No customer segments found.</div>";
  $("#all-segments").innerHTML = sorted.map((segment, index) => segmentCard(segment, index, true)).join("") || "<div class='loading-state'>No segment profile found.</div>";
}

function segmentChip(name) {
  const color = SEGMENT_COLORS[name] || "#c1d94e";
  return `<span class="segment-chip" style="--chip-color:${color}">${escapeHtml(name)}</span>`;
}

function renderCustomerTable(customers) {
  const body = $("#customer-table");
  if (!customers.length) {
    body.innerHTML = `<tr><td colspan="6" class="empty-cell">No customers match this search.</td></tr>`;
  } else {
    body.innerHTML = customers.map((customer) => `
      <tr>
        <td>${escapeHtml(customer.customerId)}</td>
        <td>${segmentChip(customer.segment)}</td>
        <td>${number(customer.recency)} days</td>
        <td>${number(customer.frequency)}</td>
        <td>${money(customer.monetary, 2)}</td>
        <td>${escapeHtml(customer.country)}</td>
      </tr>`).join("");
  }
  $("#customer-count").textContent = `${number(customers.length)} profiles shown`;
}

async function loadCustomerDirectory(search = "") {
  const url = `/api/customers?limit=350${search ? `&search=${encodeURIComponent(search)}` : ""}`;
  const result = await request(url);
  renderCustomerTable(result.customers || []);
}

async function loadRecommendationOptions() {
  const result = await request("/api/customers?limit=1000");
  const select = $("#recommend-customer");
  const customers = result.customers || [];
  select.innerHTML = customers.map((customer) =>
    `<option value="${escapeHtml(customer.customerId)}">${escapeHtml(customer.customerId)} · ${escapeHtml(customer.segment)}</option>`
  ).join("");
  if (!customers.length) select.innerHTML = "<option value=''>No customers found</option>";
}

async function loadTransactions() {
  const result = await request("/api/transactions?limit=25");
  const transactions = result.transactions || [];
  $("#transaction-table").innerHTML = transactions.map((item) => `
    <tr>
      <td>${escapeHtml(item.invoice)}</td><td>${escapeHtml(item.date)}</td>
      <td>${escapeHtml(item.customerId)}</td><td>${escapeHtml(item.product)}</td>
      <td>${number(item.quantity)}</td><td>${money(item.unitPrice, 2)}</td>
      <td>${money(item.total, 2)}</td><td>${escapeHtml(item.country)}</td>
    </tr>`).join("") || `<tr><td colspan="8" class="empty-cell">No transactions found.</td></tr>`;
}

function updateChartImages() {
  const stamp = Date.now();
  [".visual-grid .chart-image", ".chart-short", ".diagnostic-grid img"].forEach((selector) => {
    $$(selector).forEach((img) => {
      const base = img.getAttribute("src").split("?")[0];
      img.setAttribute("src", `${base}?v=${stamp}`);
    });
  });
}

async function refreshDashboard() {
  const data = await request("/api/dashboard");
  const summary = data.summary;
  $("#kpi-customers").textContent = number(summary.customers);
  $("#kpi-revenue").textContent = money(summary.revenue);
  $("#kpi-orders").textContent = number(summary.orders);
  $("#kpi-aov").textContent = money(summary.averageOrderValue, 2);
  $("#date-range").textContent = `${summary.dateRange.from} — ${summary.dateRange.to}`;
  $("#source-label").textContent = summary.dataSource.toUpperCase();
  $("#silhouette-note").textContent = summary.silhouette === null
    ? `K-Means grouped customers into ${summary.clusterCount} clusters. Silhouette score was not available for this dataset.`
    : `K-Means grouped customers into ${summary.clusterCount} clusters. Sample silhouette score: ${summary.silhouette.toFixed(3)}.`;
  $("#data-facts").innerHTML = `
    <div class="fact-box"><span>TRANSACTION LINES</span><strong>${number(summary.transactionLines)}</strong></div>
    <div class="fact-box"><span>PRODUCTS</span><strong>${number(summary.products)}</strong></div>
    <div class="fact-box"><span>COUNTRIES</span><strong>${number(summary.countries)}</strong></div>`;
  renderSegments(data.segments || []);
  updateChartImages();
  await Promise.all([loadCustomerDirectory(), loadRecommendationOptions(), loadTransactions()]);
}

function showPage(pageName) {
  $$(".page").forEach((page) => page.classList.toggle("active", page.id === `page-${pageName}`));
  $$(".nav-link").forEach((link) => link.classList.toggle("active", link.dataset.page === pageName));
  const labels = { overview: "OVERVIEW", segments: "CUSTOMER SEGMENTS", recommendations: "PRODUCT STUDIO", transactions: "TRANSACTIONS" };
  $("#breadcrumb-current").textContent = labels[pageName] || "OVERVIEW";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function generateRecommendations() {
  const customerId = $("#recommend-customer").value;
  const target = $("#recommendation-results");
  if (!customerId) {
    target.innerHTML = `<div class="empty-recommendation"><h3>Select a customer first.</h3></div>`;
    return;
  }
  target.innerHTML = `<div class="loading-state">Comparing customer purchase profiles…</div>`;
  $("#recommend-button").disabled = true;
  try {
    const data = await request(`/api/recommend?customer=${encodeURIComponent(customerId)}`);
    const customer = data.customer;
    const products = data.recommendations || [];
    const purchased = data.purchasedProducts || [];
    const similar = data.similarCustomers || [];
    target.innerHTML = `
      <div class="result-summary">
        <div><span class="panel-kicker">RECOMMENDATION PROFILE</span><h3>Customer ${escapeHtml(customer.customerId)}</h3><p>${escapeHtml(data.method)}</p></div>
        <span class="result-segment">${escapeHtml(customer.segment)}</span>
      </div>
      <div class="result-metrics">
        <div class="result-metric"><span>RECENCY</span><strong>${number(customer.recency)} days</strong></div>
        <div class="result-metric"><span>ORDERS</span><strong>${number(customer.frequency)}</strong></div>
        <div class="result-metric"><span>SPEND</span><strong>${money(customer.monetary)}</strong></div>
      </div>
      <section class="result-section">
        <div class="result-section-head"><h3>Products worth exploring</h3><span>SIMILAR BASKETS</span></div>
        <div class="product-grid">${products.map((item, index) => `
          <article class="product-item"><span class="product-icon">${["✳", "◈", "⌑", "◇", "✧", "▧"][index % 6]}</span><strong>${escapeHtml(item.product)}</strong><small>Similarity signal · ${Number(item.score).toFixed(2)}</small></article>`).join("") || "<p>No new products could be suggested from this purchase history yet.</p>"}</div>
      </section>
      <section class="result-section">
        <div class="result-section-head"><h3>Already in their basket</h3><span>PAST PURCHASES</span></div>
        <div class="product-pills">${purchased.map((item) => `<span class="product-pill">${escapeHtml(item)}</span>`).join("") || "<span class='product-pill'>No product history</span>"}</div>
      </section>
      <section class="result-section">
        <div class="result-section-head"><h3>Customers with similar tastes</h3><span>TOP MATCHES</span></div>
        <div class="similar-list">${similar.map((item) => `<div class="similar-chip"><strong>${escapeHtml(item.customerId)}</strong><span>${Math.round(Number(item.similarity) * 100)}% match</span></div>`).join("") || "<span class='product-pill'>No close match available</span>"}</div>
      </section>
      <div class="action-note"><strong>Segment action:</strong> ${escapeHtml(data.segmentAction)}</div>`;
  } catch (error) {
    target.innerHTML = `<div class="empty-recommendation"><h3>Could not generate recommendations.</h3><p>${escapeHtml(error.message)}</p></div>`;
  } finally {
    $("#recommend-button").disabled = false;
  }
}

// Navigation
$$(".nav-link").forEach((button) => button.addEventListener("click", () => showPage(button.dataset.page)));
$$("[data-goto]").forEach((button) => button.addEventListener("click", () => showPage(button.dataset.goto)));
$("#recommend-button").addEventListener("click", generateRecommendations);
$("#customer-search").addEventListener("input", (event) => {
  loadCustomerDirectory(event.target.value.trim()).catch((error) => console.error(error));
});

// CSV import dialog
const uploadDialog = $("#upload-dialog");
$("#upload-trigger").addEventListener("click", () => {
  $("#upload-message").textContent = "";
  uploadDialog.showModal();
});
$("#close-upload").addEventListener("click", () => uploadDialog.close());
$("#cancel-upload").addEventListener("click", () => uploadDialog.close());
$("#csv-file").addEventListener("change", (event) => {
  const file = event.target.files[0];
  $("#selected-file").textContent = file ? `${file.name} · ${(file.size / (1024 * 1024)).toFixed(2)} MB` : "No file selected";
  $("#start-upload").disabled = !file || !file.name.toLowerCase().endsWith(".csv");
});
$("#start-upload").addEventListener("click", async () => {
  const file = $("#csv-file").files[0];
  if (!file) return;
  const message = $("#upload-message");
  const button = $("#start-upload");
  button.disabled = true;
  message.classList.remove("error");
  message.textContent = "Uploading and rebuilding RFM segments… keep this tab open.";
  try {
    const csvText = await file.text();
    const response = await request("/api/upload", {
      method: "POST",
      headers: { "Content-Type": "text/csv; charset=utf-8" },
      body: csvText
    });
    message.textContent = response.message;
    await refreshDashboard();
    setTimeout(() => uploadDialog.close(), 900);
  } catch (error) {
    message.classList.add("error");
    message.textContent = error.message;
    button.disabled = false;
  }
});

// Initial data load
refreshDashboard().catch((error) => {
  console.error(error);
  $("#overview-segments").innerHTML = `<div class="loading-state">Dashboard error: ${escapeHtml(error.message)}</div>`;
});
