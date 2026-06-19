// 공통 유틸: 테이블 렌더링, 정렬, CSV 내보내기, 상태 표시
window.App = (function () {
  function setStatus(el, msg, loading) {
    el.innerHTML = (loading ? '<span class="spinner"></span>' : '') + (msg || '');
  }

  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // 테이블 렌더 + 컬럼 클릭 정렬 지원
  function renderTable(table, columns, rows, opts) {
    opts = opts || {};
    const numeric = new Set(opts.numeric || []);
    const thead = table.querySelector('thead');
    const tbody = table.querySelector('tbody');
    let sortCol = null, sortAsc = true;

    function draw() {
      let data = rows.slice();
      if (sortCol !== null) {
        const isNum = numeric.has(sortCol);
        data.sort((a, b) => {
          let x = a[sortCol], y = b[sortCol];
          if (isNum) { x = parseFloat(String(x).replace(/,/g, '')) || 0;
                       y = parseFloat(String(y).replace(/,/g, '')) || 0; }
          else { x = String(x || ''); y = String(y || ''); }
          return (x < y ? -1 : x > y ? 1 : 0) * (sortAsc ? 1 : -1);
        });
      }
      thead.innerHTML = '<tr>' + columns.map(c => {
        const cls = numeric.has(c) ? ' class="num"' : '';
        const arr = sortCol === c ? ' <span class="arrow">' + (sortAsc ? '▲' : '▼') + '</span>' : '';
        return `<th${cls} data-c="${escapeHtml(c)}">${escapeHtml(c)}${arr}</th>`;
      }).join('') + '</tr>';
      tbody.innerHTML = data.map(r => '<tr>' + columns.map(c => {
        const cls = numeric.has(c) ? ' class="num"' : '';
        let v = r[c];
        if (numeric.has(c) && v !== '' && v != null && !isNaN(v))
          v = Number(v).toLocaleString();
        return `<td${cls}>${escapeHtml(v)}</td>`;
      }).join('') + '</tr>').join('');
      thead.querySelectorAll('th').forEach(th => th.addEventListener('click', () => {
        const c = th.getAttribute('data-c');
        if (sortCol === c) sortAsc = !sortAsc; else { sortCol = c; sortAsc = true; }
        draw();
      }));
    }
    draw();
  }

  function toCSV(columns, rows) {
    const esc = v => '"' + String(v == null ? '' : v).replace(/"/g, '""') + '"';
    const lines = [columns.map(esc).join(',')];
    rows.forEach(r => lines.push(columns.map(c => esc(r[c])).join(',')));
    return '﻿' + lines.join('\r\n'); // BOM for Excel(Korean)
  }

  function downloadCSV(filename, columns, rows) {
    if (!rows || !rows.length) { alert('저장할 데이터가 없습니다.'); return; }
    const blob = new Blob([toCSV(columns, rows)], { type: 'text/csv;charset=utf-8;' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  return { setStatus, renderTable, downloadCSV, escapeHtml };
})();
