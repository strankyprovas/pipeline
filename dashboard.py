"""
Jednoduchý web dashboard pro sledování leadů.
Spuštění: venv/bin/python3 dashboard.py
Otevře se na: http://localhost:5000
"""
from flask import Flask, jsonify, render_template_string
from sheets import get_or_create_sheet

app = Flask(__name__)

HTML = """<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>StránkyProVás – Dashboard</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f1117; color: #e2e8f0; min-height: 100vh; }

  header { background: #1a1d27; border-bottom: 1px solid #2d3148; padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; }
  header h1 { font-size: 1.2rem; font-weight: 600; color: #fff; }
  header span { font-size: 0.8rem; color: #64748b; }

  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; padding: 20px 24px; }
  .stat { background: #1a1d27; border: 1px solid #2d3148; border-radius: 10px; padding: 16px; text-align: center; }
  .stat .num { font-size: 2rem; font-weight: 700; }
  .stat .lbl { font-size: 0.75rem; color: #94a3b8; margin-top: 4px; }
  .stat.blue .num   { color: #60a5fa; }
  .stat.yellow .num { color: #fbbf24; }
  .stat.orange .num { color: #fb923c; }
  .stat.green .num  { color: #4ade80; }
  .stat.purple .num { color: #a78bfa; }

  .controls { padding: 0 24px 12px; display: flex; gap: 10px; flex-wrap: wrap; }
  select, input { background: #1a1d27; border: 1px solid #2d3148; color: #e2e8f0; padding: 7px 12px; border-radius: 7px; font-size: 0.85rem; outline: none; }
  select:focus, input:focus { border-color: #4f6ef7; }

  .table-wrap { padding: 0 24px 24px; overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  thead th { background: #1a1d27; color: #94a3b8; font-weight: 500; padding: 10px 12px; text-align: left; border-bottom: 1px solid #2d3148; position: sticky; top: 0; cursor: pointer; user-select: none; }
  thead th:hover { color: #e2e8f0; }
  tbody tr { border-bottom: 1px solid #1e2133; transition: background 0.15s; }
  tbody tr:hover { background: #1a1d27; }
  td { padding: 9px 12px; vertical-align: middle; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .badge { display: inline-block; padding: 2px 8px; border-radius: 99px; font-size: 0.72rem; font-weight: 600; }
  .badge-novy          { background: #1e3a5f; color: #60a5fa; }
  .badge-osloveno      { background: #3d2e00; color: #fbbf24; }
  .badge-follow_up_odesl { background: #3d1f00; color: #fb923c; }
  .badge-odpovdl       { background: #0d3320; color: #4ade80; }
  .badge-odpověděl     { background: #0d3320; color: #4ade80; }
  .badge-zakaznik      { background: #2d1457; color: #a78bfa; }
  .badge-nezajem       { background: #2d1111; color: #f87171; }
  .badge-manual        { background: #0f2840; color: #38bdf8; }
  .badge-default       { background: #1e2133; color: #94a3b8; }

  .demo-link { color: #4f6ef7; text-decoration: none; }
  .demo-link:hover { text-decoration: underline; }

  .eye { color: #4ade80; font-size: 0.9rem; }

  .refresh-btn { background: #4f6ef7; color: #fff; border: none; padding: 7px 16px; border-radius: 7px; cursor: pointer; font-size: 0.85rem; }
  .refresh-btn:hover { background: #3b55e6; }

  .loading { text-align: center; padding: 60px; color: #64748b; }
  .count-info { color: #64748b; font-size: 0.8rem; padding: 0 24px 8px; }
</style>
</head>
<body>
<header>
  <h1>StránkyProVás – Leads</h1>
  <div style="display:flex;gap:12px;align-items:center">
    <span id="last-refresh">Načítám...</span>
    <button class="refresh-btn" onclick="loadData()">Obnovit</button>
  </div>
</header>

<div class="stats" id="stats">
  <div class="loading">Načítám data...</div>
</div>

<div class="controls">
  <select id="filter-stav" onchange="renderTable()">
    <option value="">Všechny stavy</option>
    <option value="nový">Nový</option>
    <option value="osloveno">Osloveno</option>
    <option value="follow_up_odesl">Follow-up odeslán</option>
    <option value="odpověděl">Odpověděl</option>
    <option value="zákazník">Zákazník</option>
    <option value="nezájem">Nezájem</option>
    <option value="manual">Manual (FB)</option>
  </select>
  <select id="filter-odvetvi" onchange="renderTable()">
    <option value="">Všechna odvětví</option>
  </select>
  <select id="filter-mesto" onchange="renderTable()">
    <option value="">Všechna města</option>
  </select>
  <input type="text" id="search" placeholder="Hledat název / email..." oninput="renderTable()" style="min-width:220px">
</div>
<div class="count-info" id="count-info"></div>

<div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th onclick="sortBy('Název')">Název ↕</th>
        <th onclick="sortBy('Odvětví')">Odvětví ↕</th>
        <th onclick="sortBy('Město')">Město ↕</th>
        <th onclick="sortBy('Stav')">Stav ↕</th>
        <th>Email</th>
        <th onclick="sortBy('Datum emailu')">Datum ↕</th>
        <th>Demo</th>
        <th>Otevřel</th>
      </tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>
</div>

<script>
let allData = [];
let sortCol = 'Datum emailu';
let sortAsc = false;

async function loadData() {
  try {
    const res = await fetch('/api/data');
    allData = await res.json();
    populateFilters();
    renderTable();
    renderStats();
    document.getElementById('last-refresh').textContent = 'Obnoveno: ' + new Date().toLocaleTimeString('cs-CZ');
  } catch(e) {
    document.getElementById('stats').innerHTML = '<div class="loading">Chyba načítání: ' + e + '</div>';
  }
}

function renderStats() {
  const total = allData.length;
  const osloveno = allData.filter(r => ['osloveno','follow_up_odesl'].includes(r['Stav'])).length;
  const followup = allData.filter(r => r['Stav'] === 'follow_up_odesl').length;
  const odpovdl = allData.filter(r => r['Stav'] === 'odpověděl').length;
  const zakaznik = allData.filter(r => r['Stav'] === 'zákazník').length;
  const otevreli = allData.filter(r => r['Otevřel email']).length;

  document.getElementById('stats').innerHTML = `
    <div class="stat blue"><div class="num">${total}</div><div class="lbl">Celkem leadů</div></div>
    <div class="stat yellow"><div class="num">${osloveno}</div><div class="lbl">Osloveno</div></div>
    <div class="stat orange"><div class="num">${followup}</div><div class="lbl">Follow-up odeslán</div></div>
    <div class="stat"><div class="num" style="color:#10b981">${otevreli}</div><div class="lbl">Otevřelo email</div></div>
    <div class="stat green"><div class="num">${odpovdl}</div><div class="lbl">Odpověděli</div></div>
    <div class="stat purple"><div class="num">${zakaznik}</div><div class="lbl">Zákazníci</div></div>
  `;
}

function populateFilters() {
  const odvetvi = [...new Set(allData.map(r => r['Odvětví']).filter(Boolean))].sort();
  const mesta = [...new Set(allData.map(r => r['Město']).filter(Boolean))].sort();

  const sel1 = document.getElementById('filter-odvetvi');
  const cur1 = sel1.value;
  sel1.innerHTML = '<option value="">Všechna odvětví</option>' + odvetvi.map(v => `<option value="${v}">${v}</option>`).join('');
  sel1.value = cur1;

  const sel2 = document.getElementById('filter-mesto');
  const cur2 = sel2.value;
  sel2.innerHTML = '<option value="">Všechna města</option>' + mesta.map(v => `<option value="${v}">${v}</option>`).join('');
  sel2.value = cur2;
}

function sortBy(col) {
  if (sortCol === col) sortAsc = !sortAsc;
  else { sortCol = col; sortAsc = true; }
  renderTable();
}

function renderTable() {
  const stavF = document.getElementById('filter-stav').value;
  const odvF = document.getElementById('filter-odvetvi').value;
  const mestoF = document.getElementById('filter-mesto').value;
  const search = document.getElementById('search').value.toLowerCase();

  let rows = allData.filter(r => {
    if (stavF && r['Stav'] !== stavF) return false;
    if (odvF && r['Odvětví'] !== odvF) return false;
    if (mestoF && r['Město'] !== mestoF) return false;
    if (search && !r['Název'].toLowerCase().includes(search) && !r['Email'].toLowerCase().includes(search)) return false;
    return true;
  });

  rows.sort((a, b) => {
    let va = a[sortCol] || '', vb = b[sortCol] || '';
    return sortAsc ? va.localeCompare(vb, 'cs') : vb.localeCompare(va, 'cs');
  });

  document.getElementById('count-info').textContent = `Zobrazeno ${rows.length} z ${allData.length} leadů`;

  const tbody = document.getElementById('tbody');
  tbody.innerHTML = rows.map(r => {
    const stav = r['Stav'] || 'nový';
    const stavKey = stav.replace(/[^a-z_]/gi, '').toLowerCase();
    const badgeClass = 'badge-' + stavKey;
    const demoUrl = r['Demo URL'];
    const demoCell = demoUrl ? `<a class="demo-link" href="${demoUrl}" target="_blank">🔗 demo</a>` : '–';
    const otevrCel = r['Otevřel email'] ? `<span class="eye" title="${r['Otevřel email']}">👁️</span>` : '–';
    const datum = r['Datum emailu'] || r['Datum přidání'] || '';
    return `<tr>
      <td title="${r['Název']}">${r['Název']}</td>
      <td>${r['Odvětví'] || '–'}</td>
      <td>${r['Město'] || '–'}</td>
      <td><span class="badge ${badgeClass} badge-default">${stav}</span></td>
      <td title="${r['Email']}">${r['Email']}</td>
      <td>${datum}</td>
      <td>${demoCell}</td>
      <td style="text-align:center">${otevrCel}</td>
    </tr>`;
  }).join('');
}

// Auto-refresh každých 60 sekund
loadData();
setInterval(loadData, 60000);
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/data")
def api_data():
    try:
        sheet = get_or_create_sheet()
        all_values = sheet.get_all_values()
        if not all_values:
            return jsonify([])
        headers = all_values[0]
        records = []
        for row in all_values[1:]:
            # Doplň prázdné buňky pokud řádek kratší než hlavička
            padded = row + [""] * (len(headers) - len(row))
            record = {headers[i]: padded[i] for i in range(len(headers)) if headers[i]}
            records.append(record)
        return jsonify(records)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    import webbrowser, threading, time

    def open_browser():
        time.sleep(1.2)
        webbrowser.open("http://localhost:5000")

    threading.Thread(target=open_browser, daemon=True).start()
    print("🚀 Dashboard běží na http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
