// 입찰공고 페이지 로직 (스트리밍: 결과가 들어오는 대로 실시간 추가)
(function () {
  const form = document.getElementById('searchForm');
  const statusEl = document.getElementById('status');
  const countEl = document.getElementById('count');
  const table = document.getElementById('resultTable');
  const searchBtn = form.querySelector('button[type=submit]');
  const COLUMNS = ["번호", "구분", "공고번호", "공고명", "공고기관", "수요기관", "예정가격",
    "공고일", "입찰마감일", "개찰일시", "입찰방식", "상태", "첨부수"];
  let lastRows = [];
  let aborter = null;

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

  // 표 헤더 1회 설정 + 빠른 행 추가(append) 함수
  function setHeader() {
    table.querySelector('thead').innerHTML = '<tr>' +
      COLUMNS.map(c => `<th>${c}</th>`).join('') + '</tr>';
  }
  function appendRows(rows) {
    const tbody = table.querySelector('tbody');
    const frag = document.createDocumentFragment();
    rows.forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML = COLUMNS.map(c => `<td>${App.escapeHtml(r[c])}</td>`).join('');
      frag.appendChild(tr);
    });
    tbody.appendChild(frag);
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (aborter) aborter.abort();           // 이전 검색 중단
    aborter = new AbortController();

    const regions = regionBoxes().filter(b => b.checked).map(b => b.value);
    const params = new URLSearchParams({
      category: form.category.value, dateType: form.dateType.value,
      start: form.start.value, end: form.end.value,
      keyword: form.keyword.value,
      regions: regions.length === regionBoxes().length ? '' : regions.join(','),
    });

    // 초기화
    lastRows = [];
    setHeader();
    table.querySelector('tbody').innerHTML = '';
    countEl.textContent = '0건';
    searchBtn.disabled = true;
    App.setStatus(statusEl, '검색 시작...', true);

    try {
      const res = await fetch('/bid/api/search?' + params.toString(), { signal: aborter.signal });
      if (!res.ok) {
        const d = await res.json().catch(() => ({ error: 'HTTP ' + res.status }));
        App.setStatus(statusEl, '오류: ' + (d.error || res.status)); searchBtn.disabled = false; return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        let nl;
        while ((nl = buf.indexOf('\n')) >= 0) {
          const line = buf.slice(0, nl).trim(); buf = buf.slice(nl + 1);
          if (!line) continue;
          const ev = JSON.parse(line);
          if (ev.type === 'items') {
            lastRows.push(...ev.rows);
            appendRows(ev.rows);                       // ← 실시간 추가
            countEl.textContent = lastRows.length.toLocaleString() + '건';
          } else if (ev.type === 'progress') {
            App.setStatus(statusEl,
              `수집 중... (${ev.cat} ${ev.period}) 표시 ${ev.matched.toLocaleString()}건`, true);
          } else if (ev.type === 'done') {
            App.setStatus(statusEl, '완료' + (ev.capped ? ' (상한 도달 — 기간/조건을 좁히면 더 정확)' : ''));
            App.renderTable(table, COLUMNS, lastRows);   // 완료 후 정렬 가능하도록 재구성
          } else if (ev.type === 'error') {
            App.setStatus(statusEl, '오류: ' + ev.error);
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') App.setStatus(statusEl, '요청 실패: ' + err.message);
    } finally {
      searchBtn.disabled = false;
    }
  });

  document.getElementById('csvBtn').addEventListener('click', () =>
    App.downloadCSV('입찰공고_' + Date.now() + '.csv', COLUMNS, lastRows));
})();
