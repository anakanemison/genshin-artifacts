const ESC_MAP = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
function esc(v) {
  return String(v ?? "").replace(/[&<>"']/g, (ch) => ESC_MAP[ch]);
}

function preferredStarTpl() {
  return '<span class="preferred" title="Preferred role">★</span>';
}

function rankBadgeTpl(rank) {
  const r = Number(rank);
  const capped = Math.min(r, 5);
  return `<span class="rank rank-${capped}">${esc(r)}</span>`;
}

function emptyRowTpl(message, colspan = 3) {
  return `<tr><td colspan="${colspan}" style="text-align: center; color: var(--text-muted);">${esc(message)}</td></tr>`;
}

// --- Character rows (Browse + Evaluate) ---
function characterRowTpl(c, rowClass = "") {
  return `
    <tr class="${rowClass}">
      <td>${esc(c.character)}${c.preferred ? preferredStarTpl() : ""}</td>
      <td>${esc(c.role)}</td>
      <td>${rankBadgeTpl(c.setRank)}</td>
    </tr>
  `;
}

// --- Browse: slot breakdown ---
function slotCardTpl(slotName, innerHtml) {
  return `
    <div class="slot-card">
      <div class="slot-header">${esc(slotName)}</div>
      <div class="slot-content">${innerHtml}</div>
    </div>
  `;
}

function mainStatItemTpl({ slotName, mainStat, count, maxCount, substatTagsHtml }) {
  const pct = maxCount ? (count / maxCount) * 100 : 0;
  return `
    <div class="main-stat-item">
      <div class="main-stat-name">
        <span class="main-stat-link" data-slot="${esc(slotName)}" data-mainstat="${esc(mainStat)}">${esc(mainStat)}</span>
        <span class="main-stat-count">${esc(count)} char${count !== 1 ? "s" : ""}</span>
      </div>
      <div class="main-stat-bar">
        <div class="main-stat-bar-fill" style="width: ${pct}%"></div>
      </div>
      <div class="substat-tags">${substatTagsHtml}</div>
    </div>
  `;
}

function substatTagTpl({ cssClass, slotName, mainStat, substat, rank }) {
  return `
    <span class="${cssClass}"
          data-slot="${esc(slotName)}"
          data-mainstat="${esc(mainStat)}"
          data-substat="${esc(substat)}"
          data-rank="${esc(rank)}">
      <span class="substat-rank rank-${Math.min(Number(rank), 5)}">${esc(rank)}</span>
      ${esc(substat)}
    </span>
  `;
}

function substatRowTpl({ substat, rank }, chipsHtml, rowClass = "") {
  return `
    <tr class="${rowClass}">
      <td>${esc(substat)}</td>
      <td>${rankBadgeTpl(rank)}</td>
      <td><div class="char-chips">${chipsHtml}</div></td>
    </tr>
  `;
}