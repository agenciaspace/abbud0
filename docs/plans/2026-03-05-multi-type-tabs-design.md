# Design: Seleção Multi-tipo com Abas

## Objetivo
Permitir ao usuário selecionar um ou mais tipos de vegetação (árvores, arbustos, forrações) e gerar os mapas correspondentes em paralelo, exibidos em abas navegáveis.

## UI

### Seletor de tipo
- Checkboxes ao invés de radio buttons
- Todos podem ser marcados simultaneamente
- Visual: chips clicáveis com borda colorida quando selecionados

### Processamento
- Botão "Processar" dispara chamadas paralelas à API para cada tipo selecionado
- Barra de progresso global com status por tipo ("Processando árvores... arbustos...")

### Resultado em abas
- Uma aba por tipo processado (ex: "Árvores", "Arbustos", "Forrações")
- Cada aba contém: mapa canvas+SVG, legenda, botões PNG e PDF
- Aba ativa destacada com cor do acento

### Download
- Botões PNG/PDF dentro de cada aba (exportam apenas aquele tipo)
- Botão "Processar outro PDF" para reiniciar

## Dados
- `results = { arvore: {...}, arbusto: {...}, forracao: {...} }` — preenchido conforme API responde
- `activeTab` — tipo atualmente visível
- Processamento paralelo via `Promise.all`
