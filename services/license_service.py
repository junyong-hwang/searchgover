# -*- coding: utf-8 -*-
"""
지방행정 인허가데이터(LOCALDATA) 조회 서비스 계층.

[중요] localdata.go.kr 은 2026-04-16 폐쇄되어 데이터가 공공데이터포털/신 포털
(localdata.kr)로 이전되었습니다. 엔드포인트(Config.LICENSE_API_URL)와
인증키(Config.LOCALDATA_KEY)는 신 포털에서 활용신청 후 받은 값으로
환경변수로 주입하세요. (구버전 키/주소는 동작하지 않습니다.)

REST openDataApi 규격(기존 LOCALDATA 기준, 신 포털도 동일 구조로 추정):
  GET {LICENSE_API_URL}
    authKey   (필수) 인증키
    opnSvcId  (업종) 개방서비스ID  예) 일반음식점 07_24_04_P
    bgnYmd    인허가일자 시작(YYYYMMDD)
    endYmd    인허가일자 종료
    pageIndex / pageSize(최대 500)
    resultType = json | xml
  응답(JSON): result.body.rows[0].row = [ {필드...}, ... ]
"""
import json
import xml.etree.ElementTree as ET

import requests
import urllib3

from config import Config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REQUEST_TIMEOUT = 30
MAX_RETRIES = 2
PAGE_SIZE = 500

# UI 업종 옵션: (표시명, opnSvcId). 신 포털에서 코드가 바뀌면 여기만 수정.
INDUSTRIES = [
    ("일반음식점", "07_24_04_P"),
    ("휴게음식점", "07_24_05_P"),
    ("제과점영업", "07_24_06_P"),
    ("단란주점영업", "07_24_02_P"),
    ("유흥주점영업", "07_24_03_P"),
]

# 지역(시도) — 주소(siteWhlAddr) 기준 로컬 필터용
SIDO = ["전체", "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
        "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]

# LOCALDATA 응답 필드 → 표시 컬럼
FIELD_MAP = [
    ("bplcNm", "사업장명"), ("opnSvcNm", "업종"), ("trdStateNm", "영업상태"),
    ("dtlStateNm", "상세상태"), ("apvPermYmd", "인허가일자"),
    ("rdnWhlAddr", "도로명주소"), ("siteWhlAddr", "지번주소"),
    ("siteTel", "전화번호"), ("uptaeNm", "업태"), ("lastModTs", "최종수정"),
]
COLUMNS = [c for _, c in FIELD_MAP]


class LicenseApiError(Exception):
    pass


def _request(params):
    last = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            r = requests.get(Config.LICENSE_API_URL, params=params,
                             timeout=REQUEST_TIMEOUT, verify=Config.SSL_VERIFY)
            r.encoding = "utf-8"
            return r.status_code, r.text
        except Exception as e:
            last = e
    raise LicenseApiError(f"인허가 API 연결 실패: {last} "
                          f"(엔드포인트/네트워크 확인: {Config.LICENSE_API_URL})")


def _parse_json(text):
    """LOCALDATA JSON: result.body.rows[0].row = [...]. (구조 변형도 방어적으로 처리)"""
    data = json.loads(text)
    res = data.get("result", data)
    # 에러 메시지
    proc = (res.get("header", {}) or {}).get("process", {}) or {}
    code = proc.get("code")
    if code and code not in ("00", "0"):
        raise LicenseApiError(f"[{code}] {proc.get('message', '오류')}")
    paging = (res.get("header", {}) or {}).get("paging", {}) or {}
    total = int(paging.get("totalCount") or 0)
    body = res.get("body", {}) or {}
    rows = body.get("rows")
    items = []
    if isinstance(rows, list) and rows:
        first = rows[0]
        row = first.get("row") if isinstance(first, dict) else first
    elif isinstance(rows, dict):
        row = rows.get("row")
    else:
        row = None
    if isinstance(row, dict):
        row = [row]
    for r in (row or []):
        items.append({col: str(r.get(api_f, "") or "").strip() for api_f, col in FIELD_MAP})
    return items, total


def _parse_xml(text):
    root = ET.fromstring(text)
    msg = root.findtext(".//process/message") or root.findtext(".//message")
    code = root.findtext(".//process/code") or root.findtext(".//code")
    if code and code not in ("00", "0"):
        raise LicenseApiError(f"[{code}] {msg or '오류'}")
    total = int((root.findtext(".//totalCount") or "0") or 0)
    items = []
    for r in root.findall(".//row"):
        items.append({col: (r.findtext(api_f) or "").strip() for api_f, col in FIELD_MAP})
    return items, total


def search(opn_svc_id, bgn_ymd, end_ymd, sido="전체", keyword="", max_records=3000):
    """인허가 검색. 반환: {"columns","items","total","capped"}"""
    if not Config.LOCALDATA_KEY:
        raise LicenseApiError("인허가 인증키(LOCALDATA_KEY)가 설정되지 않았습니다. "
                              "신 포털(localdata.kr/data.go.kr)에서 발급한 키를 환경변수로 넣으세요.")
    collected, page, total = [], 1, None
    capped = False
    while True:
        params = {
            "authKey": Config.LOCALDATA_KEY,
            "opnSvcId": opn_svc_id,
            "pageIndex": str(page), "pageSize": str(PAGE_SIZE),
            "resultType": "json",
        }
        if bgn_ymd:
            params["bgnYmd"] = bgn_ymd
        if end_ymd:
            params["endYmd"] = end_ymd
        status, text = _request(params)
        if status in (401, 403):
            raise LicenseApiError(f"인증 오류({status}). 새 포털에서 발급한 키인지 확인하세요.")
        try:
            items, tc = (_parse_json(text) if text.lstrip().startswith("{")
                         else _parse_xml(text))
        except LicenseApiError:
            raise
        except Exception as e:
            raise LicenseApiError(f"응답 파싱 실패: {type(e).__name__}: {e}")
        if total is None:
            total = tc
        collected.extend(items)
        if not items or (total and len(collected) >= total):
            break
        if len(collected) >= max_records:
            capped = True
            break
        page += 1

    # 지역(시도) 로컬 필터 + 키워드(사업장명) 필터
    kw = (keyword or "").strip().lower()

    def keep(r):
        if sido and sido != "전체":
            addr = r.get("도로명주소", "") + r.get("지번주소", "")
            if sido not in addr:
                return False
        if kw and kw not in r.get("사업장명", "").lower():
            return False
        return True

    view = [r for r in collected if keep(r)]
    return {"columns": COLUMNS, "items": view, "total": len(view), "capped": capped}
