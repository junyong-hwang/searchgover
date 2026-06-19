# 공공데이터 조회 웹앱 (입찰공고 · 가맹점 통계)

조달청 나라장터 입찰공고와 공정거래위원회 가맹점 통계를 검색·집계·CSV 저장하는 Flask 웹앱.

## 구조 (페이지별 모듈)
```
web/
  app.py                      # Flask 진입점 (blueprint 등록)
  config.py                   # serviceKey/설정 (환경변수 주입)
  requirements.txt
  services/                   # API 호출·파싱 (비즈니스 로직)
    bid_service.py            #   조달청 입찰공고
    franchise_service.py      #   공정위 가맹점 통계 (+연도 캐시)
  blueprints/                 # 페이지별 라우트 모듈
    main.py                   #   /            홈
    bid.py                    #   /bid         입찰공고 페이지 + /bid/api/search
    franchise.py              #   /franchise   가맹점 페이지 + /franchise/api/stats,aggregate
  templates/                  # base + 페이지별 HTML
  static/css, static/js       # 스타일 + 페이지별 JS
```

## 로컬 실행
```bash
cd web
pip install -r requirements.txt
# (권장) 키를 환경변수로 주입. 미설정 시 config.py 기본키 사용
set DATA_GO_KR_KEY=발급키          # Windows
# export DATA_GO_KR_KEY=발급키     # macOS/Linux
python app.py                       # http://localhost:5000
```

## 운영 실행
```bash
gunicorn -w 2 -b 0.0.0.0:8000 "app:create_app()"
```

## API 엔드포인트
| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/bid/api/search?category=물품&dateType=공고일&start=YYYY-MM-DD&end=YYYY-MM-DD&keyword=&regions=` | 입찰공고 검색(JSON) |
| GET | `/franchise/api/stats?yr=2023&lclas=외식&mlsfc=&keyword=` | 가맹점 통계(JSON) |
| GET | `/franchise/api/aggregate?yr=2023&...` | 업종별 집계(JSON) |

## 보안/운영 메모
- **serviceKey는 서버(백엔드)에만** 둡니다. 브라우저로 노출되지 않습니다(프록시 구조).
- 운영 배포 시 `DATA_GO_KR_KEY`, `SECRET_KEY`를 환경변수로 주입하세요.
- 가맹점 통계는 연도 데이터를 메모리에 캐시합니다. 다중 워커/재시작 시 DB·Redis 캐시로 확장 권장(추후).
- 입찰 조회는 1회 요청당 최대 `MAX_RECORDS`(기본 5000)까지 수집 후 필터링합니다.

## 무료 배포: Render.com (카드 불필요)

이 앱은 서버에서 data.go.kr을 호출하므로 **외부 호출이 가능한 무료 호스팅**이 필요합니다.
Render 무료 플랜이 적합합니다(Firebase Spark·PythonAnywhere 무료는 외부 호출 제한으로 부적합).

### 가장 쉬운 업로드 (명령어 없이, GitHub 웹 + Render 웹)
1. **GitHub 가입** → 새 저장소(Repository) 생성 — *Private 권장*.
2. 저장소 화면에서 **Add file ▸ Upload files** → 이 `web/` 폴더 안의 **파일 전체를 드래그**해서 업로드 → Commit.
   (app.py, config.py, requirements.txt, Procfile, render.yaml, runtime.txt, services/, blueprints/, templates/, static/ 모두)
3. **Render 가입**(render.com, GitHub 계정으로 로그인) → **New + ▸ Blueprint** → 방금 저장소 선택
   → `render.yaml`을 자동 인식하여 서비스가 만들어집니다.
   (Blueprint이 안 보이면 **New + ▸ Web Service** 선택 후: Build `pip install -r requirements.txt`,
    Start `gunicorn app:app --bind 0.0.0.0:$PORT`)
4. **Environment** 탭에서 `DATA_GO_KR_KEY` 값에 발급키 입력 → **Deploy**.
5. 몇 분 뒤 `https://gov-data-app.onrender.com` 같은 주소가 생성됩니다.

### 참고
- 무료 플랜은 15분 미사용 시 잠들고 첫 요청에 ~50초 깨어납니다(개인용 무방).
  깨워두려면 외부 무료 모니터(UptimeRobot)로 5분마다 핑.
- **공개(Public) 저장소면 `config.py`의 기본 키를 지우고** 반드시 환경변수로만 주입하세요(키 노출 방지).
- 이후 코드 수정 → GitHub에 다시 업로드(commit)하면 Render가 자동 재배포합니다.

## 그 외 배포 후보
- Koyeb 무료(외부호출 가능), Fly.io(카드 필요), Cloud Run(종량제·무료한도 큼)
- DB가 필요해지면(검색 캐시·즐겨찾기·이력) Render PostgreSQL 무료 인스턴스 권장
```
