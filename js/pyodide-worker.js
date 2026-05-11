// Pyodide Web Worker — runs Python engine in background thread
importScripts('https://cdn.jsdelivr.net/pyodide/v0.27.4/full/pyodide.js');

let pyodide = null;
let engineReady = false;

async function init() {
    try {
        pyodide = await loadPyodide();

        // Fetch the engine bundle
        const response = await fetch('../python/engine_bundle.py');
        const code = await response.text();

        // Run it to define all functions
        pyodide.runPython(code);

        engineReady = true;
        postMessage({ type: 'ready' });
    } catch (err) {
        postMessage({ type: 'error', message: err.toString() });
    }
}

self.onmessage = async function(e) {
    if (e.data.type === 'run') {
        if (!engineReady) {
            postMessage({ type: 'error', message: 'Engine not ready' });
            return;
        }
        try {
            const paramsJson = JSON.stringify(e.data.params);
            // Escape single quotes in JSON for Python string literal
            const escaped = paramsJson.replace(/'/g, "\\'");
            const resultJson = pyodide.runPython(`run_custom('${escaped}')`);
            const result = JSON.parse(resultJson);
            postMessage({ type: 'result', data: result });
        } catch (err) {
            postMessage({ type: 'error', message: err.toString() });
        }
    }
};

init();
