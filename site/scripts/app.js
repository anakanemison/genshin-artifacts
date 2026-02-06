/**
 * Genshin Artifact Evaluator
 * Main application logic
 */

// Global data variable (loaded from artifact_data.json)
let DATA = null;

// Application state
const state = {
    tab: 'browse',
    set: '',
    slot: '',
    mainStat: '',
    preferredOnly: false,
    substatThreshold: 3,
    focusedSubstat: null,
    focusedCharRole: null
};

// DOM element references - will be initialized in init()
let elements = null;

// ============================================================================
// Data Loading
// ============================================================================

async function loadData() {
    try {
        showLoading(true);
        const response = await fetch('artifact_data.json');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        DATA = await response.json();
        showLoading(false);
    } catch (error) {
        console.error('Failed to load artifact data:', error);
        showFatalError(error.message);
        throw error;
    }
}

function showLoading(isLoading) {
    elements.loading.style.display = isLoading ? 'flex' : 'none';
    // Let CSS classes control workflow visibility via updateTabs()
}

function showFatalError(message) {
    elements.fatalError.style.display = 'flex';
    elements.loading.style.display = 'none';
    elements.workflowBrowse.style.display = 'none';
    elements.workflowEvaluate.style.display = 'none';
}

// ============================================================================
// Initialization
// ============================================================================

function initElements() {
    elements = {
        loading: document.getElementById('loading'),
        fatalError: document.getElementById('fatal-error'),
        tabs: document.querySelectorAll('.tab'),
        setFilter: document.getElementById('set-filter'),
        slotFilter: document.getElementById('slot-filter'),
        mainstatFilter: document.getElementById('mainstat-filter'),
        preferredToggle: document.getElementById('preferred-toggle'),
        toggleText: document.querySelector('.toggle-text'),
        thresholdBtns: document.querySelectorAll('.threshold-btn'),
        workflowBrowse: document.getElementById('workflow-browse'),
        workflowEvaluate: document.getElementById('workflow-evaluate'),
        browseEmpty: document.getElementById('browse-empty'),
        browseContent: document.getElementById('browse-content'),
        browseTitle: document.getElementById('browse-title'),
        browseCount: document.getElementById('browse-count'),
        browseCharsTable: document.getElementById('browse-chars-table').querySelector('tbody'),
        slotBreakdown: document.getElementById('slot-breakdown'),
        evaluateEmpty: document.getElementById('evaluate-empty'),
        evaluateContent: document.getElementById('evaluate-content'),
        verdictCount: document.getElementById('verdict-count'),
        verdictText: document.getElementById('verdict-text'),
        evaluateCharsTable: document.getElementById('evaluate-chars-table').querySelector('tbody'),
        substatsTable: document.getElementById('substats-table').querySelector('tbody'),
        evaluateFilters: document.querySelectorAll('.workflow-evaluate-only')
    };
}

async function init() {
    try {
        initElements();
        await loadData();
        populateSetDropdown();
        populateSlotDropdown();
        updateTabs();
        bindEvents();
        render();
    } catch (error) {
        console.error('Initialization error:', error);
    }
}

function populateSetDropdown() {
    DATA.meta.sets.forEach(set => {
        const option = document.createElement('option');
        option.value = set;
        option.textContent = set;
        elements.setFilter.appendChild(option);
    });
}

function populateSlotDropdown() {
    DATA.meta.slots.forEach(slot => {
        const option = document.createElement('option');
        option.value = slot;
        option.textContent = slot;
        elements.slotFilter.appendChild(option);
    });
}

function populateMainStatDropdown() {
    elements.mainstatFilter.innerHTML = '<option value="">Select a main stat...</option>';
    if (!state.slot) return;

    const mainStats = DATA.meta.mainStatsBySlot[state.slot] || [];
    mainStats.forEach(stat => {
        const option = document.createElement('option');
        option.value = stat;
        option.textContent = stat;
        elements.mainstatFilter.appendChild(option);
    });
}

// ============================================================================
// Event Handlers
// ============================================================================

function bindEvents() {
    bindTabEvents();
    bindFilterEvents();
    bindFocusEvents();
}

function bindTabEvents() {
    elements.tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            state.tab = tab.dataset.tab;
            clearFocusStates();
            updateTabs();
            render();
        });
    });
}

function bindFilterEvents() {
    elements.setFilter.addEventListener('change', (e) => {
        state.set = e.target.value;
        clearFocusStates();
        render();
    });

    elements.slotFilter.addEventListener('change', (e) => {
        state.slot = e.target.value;
        state.mainStat = '';
        state.focusedCharRole = null;
        populateMainStatDropdown();
        render();
    });

    elements.mainstatFilter.addEventListener('change', (e) => {
        state.mainStat = e.target.value;
        state.focusedCharRole = null;
        render();
    });

    elements.preferredToggle.addEventListener('click', () => {
        state.preferredOnly = !state.preferredOnly;
        elements.preferredToggle.classList.toggle('active', state.preferredOnly);
        elements.toggleText.textContent = state.preferredOnly ? 'Preferred only' : 'Show all roles';
        render();
    });

    elements.thresholdBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            state.substatThreshold = parseInt(btn.dataset.threshold);
            elements.thresholdBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            render();
        });
    });
}

function bindFocusEvents() {
    // Clear focus when clicking outside substat tags in Browse view
    elements.slotBreakdown.addEventListener('click', (e) => {
        if (!e.target.closest('.substat-tag') && state.focusedSubstat) {
            state.focusedSubstat = null;
            render();
        }
    });

    // Clear focus when clicking outside character chips in Evaluate view
    elements.evaluateContent.addEventListener('click', (e) => {
        if (!e.target.closest('.char-chip') && state.focusedCharRole) {
            state.focusedCharRole = null;
            render();
        }
    });
}

function clearFocusStates() {
    state.focusedSubstat = null;
    state.focusedCharRole = null;
}

// ============================================================================
// UI Updates
// ============================================================================

function updateTabs() {
    elements.tabs.forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === state.tab);
    });
    elements.workflowBrowse.classList.toggle('active', state.tab === 'browse');
    elements.workflowEvaluate.classList.toggle('active', state.tab === 'evaluate');

    // Show/hide evaluate-specific filters
    elements.evaluateFilters.forEach(el => {
        el.style.display = state.tab === 'evaluate' ? 'block' : 'none';
    });
}

function render() {
    if (state.tab === 'browse') {
        renderBrowse();
    } else {
        renderEvaluate();
    }
}

// ============================================================================
// Filtering Utilities
// ============================================================================

function filterCharacters(chars) {
    if (!state.preferredOnly) return chars;
    return chars.filter(c => c.preferred);
}

function filterSubstats(substats) {
    return substats.filter(s => s.rank <= state.substatThreshold);
}

// ============================================================================
// Browse Tab Rendering
// ============================================================================

function renderBrowse() {
    if (!state.set) {
        elements.browseEmpty.style.display = 'flex';
        elements.browseContent.style.display = 'none';
        return;
    }

    elements.browseEmpty.style.display = 'none';
    elements.browseContent.style.display = 'block';

    const setData = DATA.bySet[state.set];
    if (!setData) return;

    const chars = filterCharacters(setData.characters);
    const focusedCharRoleKeys = computeFocusedCharRoleKeys(setData);

    // Update header
    elements.browseTitle.textContent = state.set;
    elements.browseCount.textContent = `${chars.length} character${chars.length !== 1 ? 's' : ''}`;

    // Render characters table
    renderCharactersTable(chars, focusedCharRoleKeys);

    // Render slot breakdown
    renderSlotBreakdown(setData.slots, focusedCharRoleKeys);
}

/**
 * Computes the set of character+role keys that match the focused substat
 */
function computeFocusedCharRoleKeys(setData) {
    const keys = new Set();
    if (!state.focusedSubstat) return keys;

    const { slot, mainStat, substat, rank } = state.focusedSubstat;
    const slotData = setData.slots[slot];
    if (!slotData || !slotData[mainStat]) return keys;

    const sub = slotData[mainStat].substats.find(s =>
        s.substat === substat && s.rank === rank
    );

    if (sub && sub.characterRoles) {
        sub.characterRoles.forEach(cr => {
            keys.add(`${cr.character}|${cr.role}`);
        });
    }

    return keys;
}

function renderCharactersTable(chars, focusedCharRoleKeys) {
    elements.browseCharsTable.innerHTML = chars.map(c => {
        let rowClass = '';
        if (state.focusedSubstat) {
            const key = `${c.character}|${c.role}`;
            rowClass = focusedCharRoleKeys.has(key) ? 'highlighted' : 'dimmed';
        }
        return characterRow(c, rowClass);
    }).join('');
}

function renderSlotBreakdown(slots, focusedCharRoleKeys) {
    const slotOrder = ['Sands', 'Goblet', 'Circlet'];

    elements.slotBreakdown.innerHTML = slotOrder.map(slotName => {
        const slotData = slots[slotName];
        if (!slotData) return '';

        const maxCount = calculateMaxCount(slotData);
        const mainStatsHtml = renderMainStats(slotName, slotData, maxCount, focusedCharRoleKeys);

        return slotCard(slotName, mainStatsHtml);
    }).join('');

    bindSlotBreakdownEvents();
}

function calculateMaxCount(slotData) {
    let maxCount = 0;
    Object.entries(slotData).forEach(([_, data]) => {
        const filtered = filterCharacters(data.characters);
        if (filtered.length > maxCount) {
            maxCount = filtered.length;
        }
    });
    return maxCount;
}

function renderMainStats(slotName, slotData, maxCount, focusedCharRoleKeys) {
    const mainStats = Object.entries(slotData)
        .map(([mainStat, data]) => {
            const chars = filterCharacters(data.characters);
            const subs = filterSubstats(data.substats);
            return { mainStat, chars, subs, count: chars.length };
        })
        .filter(ms => ms.count > 0)
        .sort((a, b) => b.count - a.count);

    return mainStats.map(ms => {
        const subsHtml = renderSubstatTags(slotName, ms.mainStat, ms.subs, focusedCharRoleKeys);
        return mainStatItem({
            slotName,
            mainStat: ms.mainStat,
            count: ms.count,
            maxCount,
            subsHtml
        });
    }).join('');
}

function renderSubstatTags(slotName, mainStat, subs, focusedCharRoleKeys) {
    return subs.map(s => {
        const cssClass = determineSubstatCssClass(slotName, mainStat, s, focusedCharRoleKeys);
        return substatTag({
            slotName,
            mainStat,
            substat: s.substat,
            rank: s.rank,
            cssClass
        });
    }).join('');
}

function determineSubstatCssClass(slotName, mainStat, substat, focusedCharRoleKeys) {
    let cssClass = 'substat-tag';

    if (!state.focusedSubstat) return cssClass;

    const isFocused = state.focusedSubstat.slot === slotName &&
                      state.focusedSubstat.mainStat === mainStat &&
                      state.focusedSubstat.substat === substat.substat &&
                      state.focusedSubstat.rank === substat.rank;

    if (isFocused) {
        return cssClass + ' focused';
    }

    // Check if this substat shares any character+role with focused
    const subCharRoles = substat.characterRoles || [];
    const sharesCharRole = subCharRoles.some(cr =>
        focusedCharRoleKeys.has(`${cr.character}|${cr.role}`)
    );

    return cssClass + (sharesCharRole ? ' highlighted' : ' dimmed');
}

function bindSlotBreakdownEvents() {
    // Bind click handlers for main stat links
    document.querySelectorAll('.main-stat-link').forEach(el => {
        el.addEventListener('click', (e) => {
            const slot = e.target.dataset.slot;
            const mainStat = e.target.dataset.mainstat;
            navigateToEvaluate(slot, mainStat);
        });
    });

    // Bind click handlers for substat tags
    document.querySelectorAll('#slot-breakdown .substat-tag').forEach(el => {
        el.addEventListener('click', (e) => {
            e.stopPropagation();
            const slot = el.dataset.slot;
            const mainStat = el.dataset.mainstat;
            const substat = el.dataset.substat;
            const rank = parseInt(el.dataset.rank);
            toggleSubstatFocus(slot, mainStat, substat, rank);
        });
    });
}

function navigateToEvaluate(slot, mainStat) {
    state.tab = 'evaluate';
    state.slot = slot;
    state.mainStat = mainStat;
    state.focusedSubstat = null;

    // Update UI
    elements.slotFilter.value = slot;
    populateMainStatDropdown();
    elements.mainstatFilter.value = mainStat;
    updateTabs();
    render();
}

function toggleSubstatFocus(slot, mainStat, substat, rank) {
    // Toggle: if clicking same substat+rank, clear focus
    if (state.focusedSubstat &&
        state.focusedSubstat.slot === slot &&
        state.focusedSubstat.mainStat === mainStat &&
        state.focusedSubstat.substat === substat &&
        state.focusedSubstat.rank === rank) {
        state.focusedSubstat = null;
    } else {
        state.focusedSubstat = { slot, mainStat, substat, rank };
    }
    render();
}

// ============================================================================
// Evaluate Tab Rendering
// ============================================================================

function renderEvaluate() {
    if (!state.set || !state.slot || !state.mainStat) {
        elements.evaluateEmpty.style.display = 'flex';
        elements.evaluateContent.style.display = 'none';
        return;
    }

    elements.evaluateEmpty.style.display = 'none';
    elements.evaluateContent.style.display = 'block';

    const key = `${state.set}|${state.slot}|${state.mainStat}`;
    const artifactData = DATA.byArtifact[key];

    if (!artifactData) {
        renderEmptyEvaluate();
        return;
    }

    const chars = filterCharacters(artifactData.characters);
    const subs = filterSubstats(artifactData.substats);

    renderEvaluateVerdict(chars);
    renderEvaluateCharacters(chars);
    renderEvaluateSubstats(subs, chars);
}

function renderEmptyEvaluate() {
    elements.verdictCount.textContent = '0';
    elements.verdictText.textContent = 'characters';
    elements.evaluateCharsTable.innerHTML = emptyRow('No characters want this combination');
    elements.substatsTable.innerHTML = '';
}

function renderEvaluateVerdict(chars) {
    elements.verdictCount.textContent = chars.length;
    elements.verdictText.textContent = chars.length === 1 ? 'character' : 'characters';
}

function renderEvaluateCharacters(chars) {
    if (chars.length === 0) {
        elements.evaluateCharsTable.innerHTML = emptyRow('No characters match filters');
        return;
    }

    elements.evaluateCharsTable.innerHTML = chars.map(c => {
        let rowClass = '';
        if (state.focusedCharRole) {
            const isMatch = c.character === state.focusedCharRole.character &&
                           c.role === state.focusedCharRole.role;
            rowClass = isMatch ? 'highlighted' : 'dimmed';
        }
        return characterRow(c, rowClass);
    }).join('');
}

function renderEvaluateSubstats(subs, chars) {
    if (subs.length === 0) {
        elements.substatsTable.innerHTML = emptyRow('No substats match threshold');
        return;
    }

    const rows = subs.map(s => {
        const charRoles = s.characterRoles || [];
        let filteredCharRoles = charRoles;

        // Filter by preferred if needed
        if (state.preferredOnly) {
            filteredCharRoles = charRoles.filter(cr =>
                chars.some(c => c.character === cr.character)
            );
        }

        if (filteredCharRoles.length === 0) return '';

        // Determine row CSS class
        const rowClass = determineSubstatRowClass(s);

        return substatRow(s, filteredCharRoles, state.focusedCharRole, rowClass);
    }).filter(Boolean);

    elements.substatsTable.innerHTML = rows.join('');
    bindEvaluateSubstatsEvents();
}

function determineSubstatRowClass(substat) {
    if (!state.focusedCharRole) return '';

    const wantsThisSubstat = (substat.characterRoles || []).some(cr =>
        cr.character === state.focusedCharRole.character &&
        cr.role === state.focusedCharRole.role
    );

    return wantsThisSubstat ? 'highlighted-row' : 'dimmed-row';
}

function bindEvaluateSubstatsEvents() {
    // Bind click handlers for character chips
    document.querySelectorAll('#substats-table .char-chip[data-character]').forEach(el => {
        el.addEventListener('click', (e) => {
            e.stopPropagation();
            const character = el.dataset.character;
            const role = el.dataset.role;
            toggleCharRoleFocus(character, role);
        });
    });
}

function toggleCharRoleFocus(character, role) {
    // Toggle: if clicking same character+role, clear focus
    if (state.focusedCharRole &&
        state.focusedCharRole.character === character &&
        state.focusedCharRole.role === role) {
        state.focusedCharRole = null;
    } else {
        state.focusedCharRole = { character, role };
    }
    render();
}

// ============================================================================
// Start Application
// ============================================================================

init();
