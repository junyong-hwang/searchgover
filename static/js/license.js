// 인허가 조회 페이지 로직
(function () {
  const form = document.getElementById('searchForm');
  const statusEl = document.getElementById('status');
  const countEl = document.getElementById('count');
  const table = document.getElementById('resultTable');
  let COLUMNS = [], lastRows = [];

  // 업종 '직접입력' 토글
  const opnSel = document.getElementById('opnSel');
  const customWrap = document.getElementById('customWrap');
  opnSel.addEventListener('change', () => {
    customWrap.style.display = opnSel.value === '__custom__' ? '' : 'none';
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    let opn = opnSel.value;
    if (opn === '__custom__') opn = form.opnCustom.value.trim();
    if (!opn) { App.setStatus(statusEl, '업종(opnSvcId)을 지정하세요.'); return; }

    const params = new URLSearchParams({
      opnSvcId: opn, sido: form.sido.value,
      bgn: form.bgn.value, end: form.end.value, keyword: form.keyword.value,
    });
    App.setStatus(statusEl, '조회 중...', true);
    try {
      const res = await fetch('/license/api/search?' + params.toString());
      const data = await res.json();
      if (!data.ok) { App.setStatus(statusEl, '오류: ' + data.error); return; }
      COLUMNS = data.columns; lastRows = data.items;
      App.renderTable(table, COLUMNS, lastRows);
      countEl.textContent = data.total.toLocaleString() + '건'
        + (data.capped ? ' (상한 도달 — 기간/조건을 좁혀주세요)' : '');
      App.setStatus(statusEl, '완료');
    } catch (err) {
      App.setStatus(statusEl, '요청 실패: ' + err.message);
    }
  });

  document.getElementById('csvBtn').addEventListener('click', () =>
    App.downloadCSV('인허가_' + Date.now() + '.csv', COLUMNS, lastRows));
})();
