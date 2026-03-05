# Multi-type Tabs Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Permitir selecao de multiplos tipos de vegetacao com resultados em abas navegaveis.

**Architecture:** Modificacao unica em `index.html` — checkboxes substituem radio buttons, chamadas paralelas via `Promise.all`, resultado em objeto `results` por tipo, abas dinamicas renderizadas por tipo.

**Tech Stack:** HTML/CSS/JS vanilla, PDF.js 3.11, jsPDF 2.5, API `/api/extract`

---

### Task 1: Checkboxes multi-select no seletor de tipo

**Files:**
- Modify: `index.html`

**Step 1:** Substituir `type="radio"` por `type="checkbox"` nos 3 labels do `#typeSelector`.

**Step 2:** Substituir o event listener do seletor:
```js
document.querySelectorAll('.type-option').forEach(opt => {
    opt.addEventListener('click', () => {
        const cb = opt.querySelector('input[type="checkbox"]');
        opt.classList.toggle('selected', cb.checked);
    });
});
```

**Step 3:** Substituir variavel `currentType` por funcao:
```js
function getSelectedTypes() {
    return Array.from(document.querySelectorAll('.type-option input:checked'))
        .map(cb => cb.value);
}
```

**Step 4: Commit**
```bash
git add index.html
git commit -m "feat: checkboxes multi-select para tipos de vegetacao"
```

---

### Task 2: Processamento paralelo

**Files:**
- Modify: `index.html` — funcao `processPDF()`

**Step 1:** No inicio de `processPDF()`, substituir `if (!pdfFile) return` por:
```js
const selectedTypes = getSelectedTypes();
if (!pdfFile || selectedTypes.length === 0) {
    statusText.textContent = 'Selecione ao menos um tipo e um arquivo PDF.';
    return;
}
```

**Step 2:** Substituir o bloco de chamada unica `fetch('/api/extract')` por chamadas paralelas:
```js
const promises = selectedTypes.map(type => {
    const formData = new FormData();
    formData.append('file', pdfFile);
    formData.append('type', type);
    return fetch('/api/extract', { method: 'POST', body: formData })
        .then(r => r.ok ? r.json() : r.json().then(e => { throw new Error(e.error); }))
        .then(data => ({ type, data }));
});
const apiResults = await Promise.all(promises);
```

**Step 3:** Renderizar background PDF uma unica vez e armazenar em `results`:
```js
let results = {};
// ... render bgCanvas ...
for (const { type, data } of apiResults) {
    results[type] = { data, bgCanvas };
}
```

**Step 4:** Substituir chamada de `renderMapOverlay / renderTabs` no lugar das chamadas antigas de SVG/legend.

**Step 5: Commit**
```bash
git add index.html
git commit -m "feat: processamento paralelo de multiplos tipos via Promise.all"
```

---

### Task 3: Abas e renderizacao por tipo

**Files:**
- Modify: `index.html`

**Step 1:** Adicionar CSS das abas antes do `@media (max-width: 768px)`:
```css
.tabs-bar {
    display: flex; border-bottom: 1px solid var(--border);
    background: var(--surface2);
}
.tab-btn {
    padding: 12px 24px; font-size: 13px; font-weight: 600;
    cursor: pointer; border: none; background: transparent;
    color: var(--text2); letter-spacing: 1px; text-transform: uppercase;
    border-bottom: 2px solid transparent; transition: all 0.15s;
}
.tab-btn:hover { color: var(--text); }
.tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); background: var(--surface); }
.tab-panel { display: none; }
.tab-panel.active { display: block; }
```

**Step 2:** Substituir conteudo de `<div class="preview-card">` por:
```html
<div class="preview-card">
    <div class="tabs-bar" id="tabsBar"></div>
    <div id="tabPanels"></div>
</div>
```

**Step 3:** Implementar `renderTabs(types)` — para cada tipo, cria botao de aba + painel com header/stats, canvas, svg, legend-bar e botoes de download usando metodos DOM (sem innerHTML).

**Step 4:** Implementar `showTab(type)`:
```js
function showTab(type) {
    activeTab = type;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.type === type));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === 'panel-' + type));
}
```

**Step 5:** Implementar `renderMapOverlay(type, canvas, svg)` — copia bgCanvas e desenha SVG overlay (mesmo codigo atual do processPDF, parametrizado por tipo).

**Step 6:** Implementar `renderLegend(type, legendEl)` — mesmo codigo atual, parametrizado.

**Step 7: Commit**
```bash
git add index.html
git commit -m "feat: abas por tipo com mapa e legenda independentes"
```

---

### Task 4: Export e reset

**Files:**
- Modify: `index.html`

**Step 1:** Adaptar `renderComposite(type, scale)` para receber tipo explicitamente (em vez de usar `currentType`).

**Step 2:** Adaptar `exportPNG(type)` e `exportPDF(type)` para receber tipo como parametro.

**Step 3:** Atualizar `resetApp()`:
```js
function resetApp() {
    pdfFile = null; results = {}; activeTab = null;
    fileInput.value = ''; fileNameEl.textContent = '';
    processBtn.disabled = true;
    const tabsBar = $('tabsBar'), tabPanels = $('tabPanels');
    if (tabsBar) while (tabsBar.firstChild) tabsBar.removeChild(tabsBar.firstChild);
    if (tabPanels) while (tabPanels.firstChild) tabPanels.removeChild(tabPanels.firstChild);
    uploadSection.style.display = '';
    previewSection.classList.remove('active');
    downloadSection.classList.remove('active');
    statusText.textContent = '';
}
```

**Step 4:** Remover seção `#downloadSection` do HTML fixo (botoes de download ficam dentro de cada aba).

**Step 5: Commit final + push**
```bash
git add index.html docs/plans/
git commit -m "feat: multi-type tabs com export por aba"
git push
```
