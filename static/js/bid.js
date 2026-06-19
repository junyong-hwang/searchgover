// 입찰공고 페이지 로직
(function () {
  const form = document.getElementById('searchForm');
  const statusEl = document.getElementById('status');
  const countEl = document.getElementById('count');
  const table = document.getElementById('resultTable');
  const COLUMNS = ["번호", "구분", "공고번호", "공고명", "공고기관", "수요기관", "예정가격",
    "공고일", "입찰마감일", "개찰일시", "입찰방식", "상태", "첨부수"];
  let lastRows = [];

  // 기본 날짜: 최근 7일
  const today = new Date();
  const weekAgo = new Date(Date.now() - 7 * 864e5);
  form.start.value = weekAgo.toISOString().slice(0, 10);
  form.end.value = today.toISOString().slice(0, 10);

  // 지역 전체 체크박스
  const all = document.getElementById('regionAll');
  const regionBoxes = () => Array.from(document.querySelectorAll('.region'));
  all.addEventListener('change', () => regionBoxes().forEach(b => b.checked = all.checked));
  regionBoxes().forEach(b => b.addEventListener('change', () =>
    all.checked = regionBoxes().every(x => x.checked)));

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const regions = regionBoxes().filter(b => b.checked).map(b => b.value);
    const params = new URLSearchParams({
      category: form.category.value, dateType: form.dateType.value,
      start: form.start.value, end: form.end.value,
      keyword: form.keyword.value,
      regions: regions.length === regionBoxes().length ? '' : regions.join(','),
    });
    App.setStatus(statusEl, '조회 중...', true);
    try {
      const res = await fetch('/bid/api/search?' + params.toString());
      const data = await res.json();
      if (!data.ok) { App.setStatus(statusEl, '오류: ' + data.error); return; }
      lastRows = data.items;
      App.renderTable(table, COLUMNS, lastRows);
      countEl.textContent = data.total.toLocaleString() + '건'
        + (data.capped ? ' (상한 도달 — 기간을 좁혀주세요)' : '');
      App.setStatus(statusEl, '완료');
    } catch (err) {
      App.setStatus(statusEl, '요청 실패: ' + err.message);
    }
  });

  document.getElementById('csvBtn').addEventListener('click', () =>
    App.downloadCSV('입찰공고_' + Date.now() + '.csv', COLUMNS, lastRows));
})();
