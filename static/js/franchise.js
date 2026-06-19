// 가맹점 통계 페이지 로직
(function () {
  const form = document.getElementById('searchForm');
  const statusEl = document.getElementById('status');
  const countEl = document.getElementById('count');
  const table = document.getElementById('resultTable');
  let COLUMNS = [], NUMERIC = [], lastRows = [];

  // 연도 옵션 (올해-1 ~ 2017)
  const yrSel = document.getElementById('yr');
  const baseYear = new Date().getFullYear() - 1;
  for (let y = baseYear; y >= 2017; y--) {
    const o = document.createElement('option'); o.value = y; o.textContent = y;
    yrSel.appendChild(o);
  }
  yrSel.value = String(Math.min(baseYear, 2023));

  function buildParams() {
    return new URLSearchParams({
      yr: form.yr.value, lclas: form.lclas.value,
      mlsfc: form.mlsfc.value, keyword: form.keyword.value,
    });
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    App.setStatus(statusEl, '조회 중... (연도 전체 수집)', true);
    try {
      const res = await fetch('/franchise/api/stats?' + buildParams().toString());
      const data = await res.json();
      if (!data.ok) { App.setStatus(statusEl, '오류: ' + data.error); return; }
      COLUMNS = data.columns; NUMERIC = data.numeric; lastRows = data.items;
      App.renderTable(table, COLUMNS, lastRows, { numeric: NUMERIC });
      countEl.textContent = data.total.toLocaleString() + '건 (연도 전체 '
        + data.yearTotal.toLocaleString() + '건)';
      App.setStatus(statusEl, '완료');
    } catch (err) {
      App.setStatus(statusEl, '요청 실패: ' + err.message);
    }
  });

  // 업종별 집계 모달
  const modal = document.getElementById('aggModal');
  document.getElementById('aggBtn').addEventListener('click', async () => {
    App.setStatus(statusEl, '집계 중...', true);
    try {
      const res = await fetch('/franchise/api/aggregate?' + buildParams().toString());
      const data = await res.json();
      if (!data.ok) { App.setStatus(statusEl, '오류: ' + data.error); return; }
      const tb = document.querySelector('#aggTable tbody');
      tb.innerHTML = data.items.map(a =>
        `<tr><td>${App.escapeHtml(a.업종대분류)}</td><td>${App.escapeHtml(a.업종중분류)}</td>`
        + `<td class="num">${a.브랜드수.toLocaleString()}</td>`
        + `<td class="num">${a.총가맹점수.toLocaleString()}</td>`
        + `<td class="num">${a.평균매출액.toLocaleString()}</td></tr>`).join('');
      modal.classList.remove('hidden');
      App.setStatus(statusEl, '완료');
    } catch (err) {
      App.setStatus(statusEl, '요청 실패: ' + err.message);
    }
  });
  document.getElementById('aggClose').addEventListener('click', () => modal.classList.add('hidden'));
  modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.add('hidden'); });

  document.getElementById('csvBtn').addEventListener('click', () =>
    App.downloadCSV('가맹점통계_' + Date.now() + '.csv', COLUMNS, lastRows));
})();
