# -*- coding: utf-8 -*-
"""
공정거래위원회 가맹사업 - 브랜드별 가맹점수/매출 통계 서비스 계층.
- data.go.kr OpenAPI: FftcBrandFrcsStatsService / getBrandFrcsStats
- 연도 전체 데이터는 변하지 않는 통계이므로 메모리에 캐시한다.
- 데스크톱 프로그램(franchise_stats.py)의 검증된 로직을 재사용.
"""
import time
import threading
import xml.etree.ElementTree as ET

import requests
import urllib3

from config import Config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_URL = "https://apis.data.go.kr/1130000/FftcBrandFrcsStatsService/getBrandFrcsStats"
ROWS_PER_PAGE = 999
MAX_PAGES = 100
REQUEST_TIMEOUT = 40
MAX_RETRIES = 2

FIELDS = [
    ("yr", "연도"), ("indutyLclasNm", "업종대분류"), ("indutyMlsfcNm", "업종중분류"),
    ("corpNm", "가맹본부"), ("brandNm", "브랜드"),
    ("frcsCnt", "가맹점수"), ("newFrcsRgsCnt", "신규개점"),
    ("ctrtEndCnt", "계약종료"), ("ctrtCncltnCnt", "계약해지"), ("nmChgCnt", "명의변경"),
    ("avrgSlsAmt", "평균매출액"), ("arUnitAvrgSlsAmt", "면적당매출액"),
]
COLUMNS = [c for _, c in FIELDS]
NUMERIC = {"가맹점수", "신규개점", "계약종료", "계약해지", "명의변경", "평균매출액", "면적당매출액"}

_cache = {}            # {yr: [rows]}
_cache_lock = threading.Lock()


class FranchiseApiError(Exception):
    pass


def _to_num(s):
    try:
        return float(str(s).replace(",", ""))
    except (ValueError, TypeError):
        return 0.0


def _get(params):
    last = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            r = requests.get(API_URL, params=params, timeout=REQUEST_TIMEOUT,
                             verify=Config.SSL_VERIFY)
            r.encoding = "utf-8"
            return r.status_code, r.text
        except Exception as e:
            last = e
            time.sleep(1.0 * (attempt + 1))
    raise FranchiseApiError(f"네트워크 오류: {last}")


def _check_error(status, text):
    if status in (401, 403):
        return (f"인증 오류({status}). 이 serviceKey가 'FftcBrandFrcsStatsService'에 "
                "활용신청/승인되었는지 확인하세요.")
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        if "Forbidden" in (text or "") or "Unauthorized" in (text or ""):
            return "인증 오류(403/401). 활용신청 여부를 확인하세요."
        return "응답 파싱 실패"
    code = root.findtext(".//resultCode")
    if code and code != "00":
        msg = root.findtext(".//resultMsg") or "오류"
        if msg == "ESSENTIAL_PARAMETER_ERROR":
            msg = "필수 파라미터 누락(연도)"
        return f"[{code}] {msg}"
    return None


def _parse(text):
    rows, total = [], 0
    root = ET.fromstring(text)
    tc = root.findtext(".//totalCount")
    if tc and tc.isdigit():
        total = int(tc)
    for it in root.findall(".//item"):
        rows.append({col: (it.findtext(api_f) or "").strip() for api_f, col in FIELDS})
    return rows, total


def get_year(yr):
    """연도 전체 통계 수집(캐시). 반환: list[dict]"""
    yr = str(yr)
    with _cache_lock:
        if yr in _cache:
            return _cache[yr]
    rows, total, page = [], None, 1
    while page <= MAX_PAGES:
        status, text = _get({"serviceKey": Config.DATA_GO_KR_KEY, "yr": yr,
                             "pageNo": str(page), "numOfRows": str(ROWS_PER_PAGE)})
        err = _check_error(status, text)
        if err:
            raise FranchiseApiError(err)
        items, tc = _parse(text)
        if total is None:
            total = tc
        rows.extend(items)
        if not items or (total and len(rows) >= total):
            break
        page += 1
        time.sleep(0.15)
    with _cache_lock:
        _cache[yr] = rows
    return rows


def filter_rows(rows, lclas="전체", mlsfc="", keyword=""):
    mlsfc = (mlsfc or "").strip().lower()
    keyword = (keyword or "").strip().lower()
    out = []
    for r in rows:
        if lclas and lclas != "전체" and r.get("업종대분류", "") != lclas:
            continue
        if mlsfc and mlsfc not in r.get("업종중분류", "").lower():
            continue
        if keyword and keyword not in (r.get("브랜드", "") + r.get("가맹본부", "")).lower():
            continue
        out.append(r)
    return out


def aggregate(rows):
    """업종중분류 기준 집계: 브랜드수/총가맹점수/평균매출액."""
    buckets = {}
    for r in rows:
        key = (r.get("업종대분류", ""), r.get("업종중분류", ""))
        b = buckets.setdefault(key, {"브랜드수": 0, "총가맹점수": 0, "_sum": 0.0, "_cnt": 0})
        b["브랜드수"] += 1
        b["총가맹점수"] += int(_to_num(r.get("가맹점수", 0)))
        sls = _to_num(r.get("평균매출액", 0))
        if sls > 0:
            b["_sum"] += sls
            b["_cnt"] += 1
    out = []
    for (lc, mc), b in buckets.items():
        out.append({
            "업종대분류": lc, "업종중분류": mc, "브랜드수": b["브랜드수"],
            "총가맹점수": b["총가맹점수"],
            "평균매출액": round(b["_sum"] / b["_cnt"]) if b["_cnt"] else 0,
        })
    out.sort(key=lambda x: (-x["총가맹점수"], -x["브랜드수"]))
    return out
