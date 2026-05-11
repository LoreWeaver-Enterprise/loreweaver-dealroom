/**
 * ScenarioData — shared financial model data loader for LoreWeaver Deal Room.
 *
 * Usage:
 *   <script src="js/scenario-data.js"></script>
 *   <div id="scenario-selector"></div>
 *   <span data-model="summary.y5_arr" data-fmt="eur"></span>
 *
 * API:
 *   ScenarioData.load(scenario, variant, gamingOnly) → Promise
 *   ScenarioData.get(path)        — dot-notation lookup
 *   ScenarioData.fmt(value, type) — format a value
 *   ScenarioData.onChange(cb)     — register change callback
 *   ScenarioData.data             — raw loaded data
 */

(function () {
    'use strict';

    // ── Constants ────────────────────────────────────────────────────────

    var SCENARIO_MAP = {
        'Bootstrap':  'bootstrap',
        'Pre-Seed':   'preseed',
        'Seed':       'seed',
        'Series A':   'seriesa',
        'Series B':   'seriesb'
    };

    var SCENARIO_LABELS = Object.keys(SCENARIO_MAP);
    var VARIANTS = ['low', 'medium', 'high'];
    var VARIANT_LABELS = { low: 'Low', medium: 'Medium', high: 'High' };
    var STORAGE_KEY = 'lw_dealroom_scenario';
    var DATA_PATH = 'data/scenarios/';

    // ── State ────────────────────────────────────────────────────────────

    var _data = null;
    var _callbacks = [];
    var _current = { scenario: 'seed', variant: 'medium', gamingOnly: false };

    // ── Helpers ──────────────────────────────────────────────────────────

    function buildFilename(scenario, variant, gamingOnly) {
        var base = scenario + '_' + variant;
        if (scenario === 'preseed' && gamingOnly) base += '_go';
        return base + '.json';
    }

    function resolvePath(obj, path) {
        if (!obj || !path) return undefined;
        var parts = path.split('.');
        var cur = obj;
        for (var i = 0; i < parts.length; i++) {
            if (cur == null) return undefined;
            cur = cur[parts[i]];
        }
        return cur;
    }

    // ── Formatting ───────────────────────────────────────────────────────

    function fmtEur(value) {
        if (value == null || isNaN(value)) return '—';
        var abs = Math.abs(value);
        var sign = value < 0 ? '-' : '';

        if (abs >= 1e9) {
            return sign + '€' + (abs / 1e9).toFixed(1).replace('.', ',') + 'B';
        }
        if (abs >= 1e6) {
            var m = abs / 1e6;
            return sign + '€' + (m >= 100 ? Math.round(m).toLocaleString('de-DE') : m.toFixed(1).replace('.', ',')) + 'M';
        }
        if (abs >= 1e3) {
            var k = abs / 1e3;
            return sign + '€' + (k >= 100 ? Math.round(k).toLocaleString('de-DE') : k.toFixed(1).replace('.', ',')) + 'K';
        }
        return sign + '€' + Math.round(abs).toLocaleString('de-DE');
    }

    function fmtEurExact(value) {
        if (value == null || isNaN(value)) return '—';
        return (value < 0 ? '-€' : '€') + Math.round(Math.abs(value)).toLocaleString('de-DE');
    }

    function fmtPct(value) {
        if (value == null || isNaN(value)) return '—';
        // Values < 1 are decimals (e.g. 0.01 = 1%), values >= 1 are already percentages (e.g. 76.4)
        var pct = value < 1 ? value * 100 : value;
        // Drop decimals if result is a whole number (e.g. 1%, 5%)
        var decimals = (pct % 1 === 0) ? 0 : 1;
        return pct.toLocaleString('de-DE', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }) + '%';
    }

    function fmtInt(value) {
        if (value == null || isNaN(value)) return '—';
        return Math.round(value).toLocaleString('de-DE');
    }

    function fmtMonths(value) {
        if (value == null || isNaN(value)) return '—';
        return value.toLocaleString('de-DE', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + ' months';
    }

    function fmt(value, type) {
        switch (type) {
            case 'eur':       return fmtEur(value);
            case 'eur_exact': return fmtEurExact(value);
            case 'pct':       return fmtPct(value);
            case 'int':       return fmtInt(value);
            case 'months':    return fmtMonths(value);
            default:          return String(value != null ? value : '—');
        }
    }

    // ── Auto-binding ─────────────────────────────────────────────────────

    function bindAll() {
        if (!_data) return;
        var els = document.querySelectorAll('[data-model]');
        for (var i = 0; i < els.length; i++) {
            var el = els[i];
            var path = el.getAttribute('data-model');
            var type = el.getAttribute('data-fmt');
            var val = resolvePath(_data, path);
            el.textContent = fmt(val, type);
        }
    }

    // ── Persistence ──────────────────────────────────────────────────────

    function saveState() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(_current));
        } catch (e) { /* ignore */ }
    }

    function loadState() {
        try {
            var raw = localStorage.getItem(STORAGE_KEY);
            if (raw) {
                var s = JSON.parse(raw);
                if (s.scenario) _current.scenario = s.scenario;
                if (s.variant)  _current.variant  = s.variant;
                if (s.gamingOnly != null) _current.gamingOnly = !!s.gamingOnly;
            }
        } catch (e) { /* ignore */ }
    }

    // ── Data loading ─────────────────────────────────────────────────────

    function load(scenario, variant, gamingOnly) {
        scenario  = scenario  || _current.scenario;
        variant   = variant   || _current.variant;
        gamingOnly = gamingOnly != null ? gamingOnly : _current.gamingOnly;

        _current.scenario   = scenario;
        _current.variant    = variant;
        _current.gamingOnly = gamingOnly;
        saveState();

        var url = DATA_PATH + buildFilename(scenario, variant, gamingOnly);

        return fetch(url)
            .then(function (res) {
                if (!res.ok) throw new Error('Failed to load ' + url + ' (' + res.status + ')');
                return res.json();
            })
            .then(function (json) {
                _data = json;
                bindAll();
                for (var i = 0; i < _callbacks.length; i++) {
                    try { _callbacks[i](_data); } catch (e) { console.error('ScenarioData callback error:', e); }
                }
                return _data;
            });
    }

    // ── Selector Widget ──────────────────────────────────────────────────

    function injectStyles() {
        if (document.getElementById('scenario-data-styles')) return;
        var style = document.createElement('style');
        style.id = 'scenario-data-styles';
        style.textContent = [
            '#scenario-selector-widget {',
            '  background: var(--bg-light);',
            '  border: 1px solid var(--border-color);',
            '  border-radius: 8px;',
            '  padding: 16px 20px;',
            '  margin-bottom: 24px;',
            '  display: flex;',
            '  flex-wrap: wrap;',
            '  align-items: center;',
            '  gap: 16px;',
            '  font-family: "Open Sans", sans-serif;',
            '  color: var(--text-color);',
            '}',
            '#scenario-selector-widget label {',
            '  font-size: 13px;',
            '  font-weight: 600;',
            '  color: var(--text-light);',
            '  margin-right: 6px;',
            '}',
            '#scenario-selector-widget select {',
            '  background: var(--bg-white);',
            '  color: var(--text-color);',
            '  border: 1px solid var(--border-color);',
            '  border-radius: 4px;',
            '  padding: 5px 10px;',
            '  font-size: 13px;',
            '  font-family: inherit;',
            '  cursor: pointer;',
            '}',
            '#scenario-selector-widget select:focus {',
            '  outline: none;',
            '  border-color: var(--primary-color);',
            '}',
            '.scenario-radio-group {',
            '  display: flex;',
            '  gap: 2px;',
            '  background: var(--bg-white);',
            '  border: 1px solid var(--border-color);',
            '  border-radius: 4px;',
            '  overflow: hidden;',
            '}',
            '.scenario-radio-group input[type="radio"] {',
            '  display: none;',
            '}',
            '.scenario-radio-group label {',
            '  padding: 5px 12px;',
            '  font-size: 13px;',
            '  font-weight: 500;',
            '  color: var(--text-light);',
            '  cursor: pointer;',
            '  margin: 0;',
            '  transition: background 0.15s, color 0.15s;',
            '}',
            '.scenario-radio-group input[type="radio"]:checked + label {',
            '  background: var(--primary-color);',
            '  color: #1F201F;',
            '  font-weight: 600;',
            '}',
            '.scenario-gaming-only {',
            '  display: flex;',
            '  align-items: center;',
            '  gap: 6px;',
            '}',
            '.scenario-gaming-only input[type="checkbox"] {',
            '  accent-color: var(--primary-color);',
            '  cursor: pointer;',
            '}',
            '.scenario-gaming-only label {',
            '  font-weight: 500 !important;',
            '  cursor: pointer;',
            '}',
            '.scenario-note {',
            '  font-size: 12px;',
            '  color: var(--text-light);',
            '  font-style: italic;',
            '  margin-left: auto;',
            '}',
            '@media (max-width: 640px) {',
            '  #scenario-selector-widget {',
            '    flex-direction: column;',
            '    align-items: flex-start;',
            '  }',
            '  .scenario-note { margin-left: 0; }',
            '}'
        ].join('\n');
        document.head.appendChild(style);
    }

    function renderWidget() {
        var container = document.getElementById('scenario-selector');
        if (!container) return;

        injectStyles();

        var widget = document.createElement('div');
        widget.id = 'scenario-selector-widget';

        // Scenario dropdown
        var scenarioGroup = document.createElement('div');
        var scenarioLabel = document.createElement('label');
        scenarioLabel.textContent = 'Scenario';
        scenarioLabel.setAttribute('for', 'scenario-select');
        var select = document.createElement('select');
        select.id = 'scenario-select';
        for (var i = 0; i < SCENARIO_LABELS.length; i++) {
            var opt = document.createElement('option');
            opt.value = SCENARIO_MAP[SCENARIO_LABELS[i]];
            opt.textContent = SCENARIO_LABELS[i];
            if (opt.value === _current.scenario) opt.selected = true;
            select.appendChild(opt);
        }
        scenarioGroup.appendChild(scenarioLabel);
        scenarioGroup.appendChild(select);
        widget.appendChild(scenarioGroup);

        // Variant radio group
        var variantWrap = document.createElement('div');
        var variantLabel = document.createElement('label');
        variantLabel.textContent = 'Variant';
        variantWrap.appendChild(variantLabel);
        var radioGroup = document.createElement('div');
        radioGroup.className = 'scenario-radio-group';
        for (var v = 0; v < VARIANTS.length; v++) {
            var id = 'variant-' + VARIANTS[v];
            var radio = document.createElement('input');
            radio.type = 'radio';
            radio.name = 'scenario-variant';
            radio.id = id;
            radio.value = VARIANTS[v];
            if (VARIANTS[v] === _current.variant) radio.checked = true;
            var rLabel = document.createElement('label');
            rLabel.setAttribute('for', id);
            rLabel.textContent = VARIANT_LABELS[VARIANTS[v]];
            radioGroup.appendChild(radio);
            radioGroup.appendChild(rLabel);
        }
        variantWrap.appendChild(radioGroup);
        widget.appendChild(variantWrap);

        // Gaming-only checkbox (initially hidden unless preseed)
        var gamingWrap = document.createElement('div');
        gamingWrap.className = 'scenario-gaming-only';
        gamingWrap.id = 'gaming-only-wrap';
        gamingWrap.style.display = _current.scenario === 'preseed' ? 'flex' : 'none';
        var cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.id = 'gaming-only-cb';
        cb.checked = _current.gamingOnly;
        var cbLabel = document.createElement('label');
        cbLabel.setAttribute('for', 'gaming-only-cb');
        cbLabel.textContent = 'Gaming only';
        gamingWrap.appendChild(cb);
        gamingWrap.appendChild(cbLabel);
        widget.appendChild(gamingWrap);

        // Note
        var note = document.createElement('span');
        note.className = 'scenario-note';
        note.textContent = 'Projections below update with selected scenario';
        widget.appendChild(note);

        container.appendChild(widget);

        // ── Event handlers ──────────────────────────────────────────────

        function onSelectionChange() {
            var scenario = select.value;
            var variant = document.querySelector('input[name="scenario-variant"]:checked').value;
            var gaming = cb.checked;

            gamingWrap.style.display = scenario === 'preseed' ? 'flex' : 'none';
            if (scenario !== 'preseed') gaming = false;

            load(scenario, variant, gaming);
        }

        select.addEventListener('change', onSelectionChange);
        cb.addEventListener('change', onSelectionChange);

        var radios = radioGroup.querySelectorAll('input[type="radio"]');
        for (var r = 0; r < radios.length; r++) {
            radios[r].addEventListener('change', onSelectionChange);
        }
    }

    // ── Initialisation ───────────────────────────────────────────────────

    loadState();

    function init() {
        renderWidget();
        load(_current.scenario, _current.variant, _current.gamingOnly);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // ── Public API ───────────────────────────────────────────────────────

    window.ScenarioData = {
        load: load,
        get: function (path) { return resolvePath(_data, path); },
        fmt: fmt,
        onChange: function (cb) { if (typeof cb === 'function') _callbacks.push(cb); },
        get data() { return _data; }
    };

})();
