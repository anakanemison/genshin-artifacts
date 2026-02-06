// Data will be embedded here
let DATA = null;

// State
const state = {
    tab: 'browse',
    set: '',
    slot: '',
    mainStat: '',
    preferredOnly: false,
    substatThreshold: 3,
    // Focus state for substat highlighting in Browse tab
    focusedSubstat: null,  // { slot, mainStat, substat } or null
    // Focus state for character highlighting in Evaluate tab
    focusedCharRole: null  // { character, role } or null
};

// DOM elements
const elements = {
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

// Data loading
async function loadData() {
    const url = 'artifact_data.json';
    const res = await fetch(url, { cache: 'no-cache' });
    if (!res.ok) throw new Error(`Failed to fetch ${url}: ${res.status} ${res.statusText}`);
    return await res.json();
}

function setLoading(isLoading) {
    const loadingEl = document.getElementById('loading');
    const fatalEl = document.getElementById('fatal-error');
    if (loadingEl) loadingEl.style.display = isLoading ? 'flex' : 'none';
    if (fatalEl) fatalEl.style.display = 'none';
}

function showFatalError(err) {
    setLoading(false);
    const fatalEl = document.getElementById('fatal-error');
    const fatalText = document.getElementById('fatal-error-text');
    if (fatalText) fatalText.textContent = `Failed to load artifact data: ${err?.message || err}`;
    if (fatalEl) fatalEl.style.display = 'flex';
}

// Initialize
async function init() {
    setLoading(true);
    try {
        DATA = await loadData();
        populateSetDropdown();
        populateSlotDropdown();
        bindEvents();
        updateTabs();
        setLoading(false);
        render();
    } catch (err) {
        console.error(err);
        showFatalError(err);
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

function bindEvents() {
    // Tabs
    elements.tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            state.tab = tab.dataset.tab;
            // Clear focus states when switching tabs
            state.focusedSubstat = null;
            state.focusedCharRole = null;
            updateTabs();
            render();
        });
    });

    // Filters
    elements.setFilter.addEventListener('change', (e) => {
        state.set = e.target.value;
        // Clear focus states when changing set
        state.focusedSubstat = null;
        state.focusedCharRole = null;
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

    // Clear focus when clicking outside substat tags in Browse view
    elements.slotBreakdown.addEventListener('click', (e) => {
        if (!e.target.closest('.substat-tag') && state.focusedSubstat) {
            state.focusedSubstat = null;
            render();
        }
    });

    // Clear focus when clicking outside character chips in Evaluate view
    document.getElementById('evaluate-content').addEventListener('click', (e) => {
        if (!e.target.closest('.char-chip') && state.focusedCharRole) {
            state.focusedCharRole = null;
            render();
        }
    });
}

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

function filterCharacters(chars) {
    if (!state.preferredOnly) return chars;
    return chars.filter(c => c.preferred);
}

function filterSubstats(substats) {
    return substats.filter(s => s.rank <= state.substatThreshold);
}

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

    // Compute highlighted character+role keys if there's a focused substat
    let focusedCharRoleKeys = new Set();
    if (state.focusedSubstat) {
        const { slot, mainStat, substat, rank } = state.focusedSubstat;
        const slotData = setData.slots[slot];
        if (slotData && slotData[mainStat]) {
            const sub = slotData[mainStat].substats.find(s =>
                s.substat === substat && s.rank === rank
            );
            if (sub && sub.characterRoles) {
                sub.characterRoles.forEach(cr => {
                    focusedCharRoleKeys.add(`${cr.character}|${cr.role}`);
                });
            }
        }
    }

    elements.browseTitle.textContent = state.set;
    elements.browseCount.textContent = `${chars.length} character${chars.length !== 1 ? 's' : ''}`;

    // Render characters table with highlighting
    elements.browseCharsTable.innerHTML = chars.map(c => {
        let rowClass = '';
        if (state.focusedSubstat) {
            const key = `${c.character}|${c.role}`;
            rowClass = focusedCharRoleKeys.has(key) ? 'highlighted' : 'dimmed';
        }
        return characterRowTpl(c, rowClass);
    }).join('');

    // Render slot breakdown (pass focusedCharRoleKeys to avoid recomputing)
    renderSlotBreakdown(setData.slots, focusedCharRoleKeys);
}

function renderSlotBreakdown(slots, focusedCharRoleKeys) {
  const slotOrder = ["Sands", "Goblet", "Circlet"];

  // 1) Build HTML first
  const html = slotOrder
    .map((slotName) => {
      const slotData = slots[slotName];
      if (!slotData) return "";

      // Calculate maxCount for bar scaling
      let maxCount = 0;
      Object.values(slotData).forEach((data) => {
        const filtered = filterCharacters(data.characters);
        if (filtered.length > maxCount) maxCount = filtered.length;
      });

      const mainStats = Object.entries(slotData)
        .map(([mainStat, data]) => {
          const chars = filterCharacters(data.characters);
          const subs = filterSubstats(data.substats);
          return { mainStat, chars, subs, count: chars.length };
        })
        .filter((ms) => ms.count > 0)
        .sort((a, b) => b.count - a.count);

      const mainStatsHtml = mainStats
        .map((ms) => {
          const subTagsHtml = ms.subs
            .map((s) => {
              let cssClass = "substat-tag";

              if (state.focusedSubstat) {
                const isFocused =
                  state.focusedSubstat.slot === slotName &&
                  state.focusedSubstat.mainStat === ms.mainStat &&
                  state.focusedSubstat.substat === s.substat &&
                  state.focusedSubstat.rank === s.rank;

                if (isFocused) {
                  cssClass += " focused";
                } else {
                  const subCharRoles = s.characterRoles || [];
                  const sharesCharRole = subCharRoles.some((cr) =>
                    focusedCharRoleKeys.has(`${cr.character}|${cr.role}`)
                  );
                  cssClass += sharesCharRole ? " highlighted" : " dimmed";
                }
              }

              return substatTagTpl({
                cssClass,
                slotName,
                mainStat: ms.mainStat,
                substat: s.substat,
                rank: s.rank,
              });
            })
            .join("");

          return mainStatItemTpl({
            slotName,
            mainStat: ms.mainStat,
            count: ms.count,
            maxCount,
            substatTagsHtml: subTagsHtml,
          });
        })
        .join("");

      return slotCardTpl(slotName, mainStatsHtml);
    })
    .join("");

  // 2) Set DOM once
  elements.slotBreakdown.innerHTML = html;

  // 3) Bind events once (scoped to slotBreakdown)
  elements.slotBreakdown.querySelectorAll(".main-stat-link").forEach((el) => {
    el.addEventListener("click", (e) => {
      const { slot, mainstat } = e.currentTarget.dataset; // use currentTarget, not target
      navigateToEvaluate(slot, mainstat);
    });
  });

  elements.slotBreakdown.querySelectorAll(".substat-tag").forEach((el) => {
    el.addEventListener("click", (e) => {
      e.stopPropagation();
      const { slot, mainstat, substat, rank } = e.currentTarget.dataset;
      toggleSubstatFocus(slot, mainstat, substat, Number(rank));
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
        elements.verdictCount.textContent = '0';
        elements.verdictText.textContent = 'characters';
        elements.evaluateCharsTable.innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--text-muted);">No characters want this combination</td></tr>';
        elements.substatsTable.innerHTML = '';
        return;
    }

    const chars = filterCharacters(artifactData.characters);
    const subs = filterSubstats(artifactData.substats);

    // Verdict
    elements.verdictCount.textContent = chars.length;
    elements.verdictText.textContent = chars.length === 1 ? 'character' : 'characters';

    // Characters table with highlighting when a character chip is focused
    elements.evaluateCharsTable.innerHTML = chars.length > 0 ? chars.map(c => {
        let rowClass = '';
        if (state.focusedCharRole) {
            const isMatch = c.character === state.focusedCharRole.character &&
                            c.role === state.focusedCharRole.role;
            rowClass = isMatch ? 'highlighted' : 'dimmed';
        }
        return characterRowTpl(c, rowClass);
    }).join('') : emptyRowTpl("No characters match filters", 3);

    // Substats table with character chips that have tooltips and click handlers
    elements.substatsTable.innerHTML = subs.length > 0 ? subs.map(s => {
        // Get character+role pairs for this substat
        const charRoles = s.characterRoles || [];
        // Filter by preferred if needed
        let filteredCharRoles = charRoles;
        if (state.preferredOnly) {
            filteredCharRoles = charRoles.filter(cr =>
                chars.some(c => c.character === cr.character)
            );
        }
        if (filteredCharRoles.length === 0) return '';

        // Determine row CSS class based on focus state
        // Check if the focused character+role wants this specific substat+rank
        let rowClass = '';
        if (state.focusedCharRole) {
            const wantsThisSubstat = (s.characterRoles || []).some(cr =>
                cr.character === state.focusedCharRole.character &&
                cr.role === state.focusedCharRole.role
            );
            rowClass = wantsThisSubstat ? 'highlighted-row' : 'dimmed-row';
        }

        return substatRowTpl(
            { substat: s.substat, rank: s.rank },
            chipsHtml,
            rowClass
          );
        })
        .filter(Boolean)
        .join("")
    : emptyRowTpl("No substats match threshold", 3);

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

// Start
init();
