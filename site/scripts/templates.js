/**
 * HTML Template Functions
 * All HTML string generation is centralized here for better maintainability
 */

// HTML escaping utility
const ESC_MAP = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
function esc(value) {
    return String(value ?? '').replace(/[&<>"']/g, ch => ESC_MAP[ch]);
}

/**
 * Generates a preferred role indicator star
 */
function preferredStar() {
    return '<span class="preferred" title="Preferred role">★</span>';
}

/**
 * Generates a rank badge span
 */
function rankBadge(rank) {
    const displayRank = Math.min(rank, 5);
    return `<span class="rank rank-${displayRank}">${rank}</span>`;
}

/**
 * Generates a character table row
 * @param {Object} char - Character object with character, role, setRank, preferred
 * @param {string} rowClass - Optional CSS class for the row
 */
function characterRow(char, rowClass = '') {
    return `
        <tr class="${rowClass}">
            <td>${esc(char.character)}${char.preferred ? preferredStar() : ''}</td>
            <td>${esc(char.role)}</td>
            <td>${rankBadge(char.setRank)}</td>
        </tr>
    `;
}

/**
 * Generates an empty table row with a message
 */
function emptyRow(message, colspan = 3) {
    return `<tr><td colspan="${colspan}" style="text-align: center; color: var(--text-muted);">${esc(message)}</td></tr>`;
}

/**
 * Generates a substat tag (used in Browse tab slot breakdown)
 * @param {Object} params - { slotName, mainStat, substat, rank, cssClass }
 */
function substatTag({ slotName, mainStat, substat, rank, cssClass = 'substat-tag' }) {
    const displayRank = Math.min(rank, 5);
    return `
        <span class="${cssClass}"
              data-slot="${esc(slotName)}"
              data-mainstat="${esc(mainStat)}"
              data-substat="${esc(substat)}"
              data-rank="${rank}">
            <span class="substat-rank rank-${displayRank}">${rank}</span>
            ${esc(substat)}
        </span>
    `;
}

/**
 * Generates a main stat item within a slot card
 * @param {Object} params - { slotName, mainStat, count, maxCount, subsHtml }
 */
function mainStatItem({ slotName, mainStat, count, maxCount, subsHtml }) {
    const widthPercent = (count / maxCount * 100).toFixed(1);
    const charLabel = count === 1 ? 'char' : 'chars';

    return `
        <div class="main-stat-item">
            <div class="main-stat-name">
                <span class="main-stat-link"
                      data-slot="${esc(slotName)}"
                      data-mainstat="${esc(mainStat)}">${esc(mainStat)}</span>
                <span class="main-stat-count">${count} ${charLabel}</span>
            </div>
            <div class="main-stat-bar">
                <div class="main-stat-bar-fill" style="width: ${widthPercent}%"></div>
            </div>
            <div class="substat-tags">
                ${subsHtml}
            </div>
        </div>
    `;
}

/**
 * Generates a complete slot card with all main stats
 */
function slotCard(slotName, contentHtml) {
    return `
        <div class="slot-card">
            <div class="slot-header">${esc(slotName)}</div>
            <div class="slot-content">
                ${contentHtml}
            </div>
        </div>
    `;
}

/**
 * Generates a character chip (used in Evaluate tab substats table)
 * @param {Object} params - { character, role, cssClass }
 */
function characterChip({ character, role, cssClass = 'char-chip' }) {
    return `<span class="${cssClass}"
                  title="${esc(role)}"
                  data-character="${esc(character)}"
                  data-role="${esc(role)}">${esc(character)}</span>`;
}

/**
 * Generates an overflow chip showing "+N more"
 */
function overflowChip(count) {
    return `<span class="char-chip" style="cursor: default;">+${count} more</span>`;
}

/**
 * Generates a substat table row for the Evaluate tab
 * @param {Object} substat - { substat, rank, characterRoles }
 * @param {Array} filteredCharRoles - Filtered character roles to display
 * @param {Object|null} focusedCharRole - Currently focused character+role
 * @param {string} rowClass - CSS class for the row
 */
function substatRow({ substat, rank }, filteredCharRoles, focusedCharRole, rowClass = '') {
    const MAX_VISIBLE = 10;
    const visible = filteredCharRoles.slice(0, MAX_VISIBLE);
    const remaining = filteredCharRoles.length - MAX_VISIBLE;

    const chipsHtml = visible.map(cr => {
        let chipClass = 'char-chip';
        if (focusedCharRole &&
            cr.character === focusedCharRole.character &&
            cr.role === focusedCharRole.role) {
            chipClass += ' focused';
        }
        return characterChip({ character: cr.character, role: cr.role, cssClass: chipClass });
    }).join('');

    const overflowHtml = remaining > 0 ? overflowChip(remaining) : '';

    return `
        <tr class="${rowClass}">
            <td>${esc(substat)}</td>
            <td>${rankBadge(rank)}</td>
            <td>
                <div class="char-chips">
                    ${chipsHtml}
                    ${overflowHtml}
                </div>
            </td>
        </tr>
    `;
}
