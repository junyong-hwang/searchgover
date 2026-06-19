# -*- coding: utf-8 -*-
"""
조달청 나라장터 입찰공고 조회 서비스 계층.
- data.go.kr OpenAPI(BidPublicInfoService)를 호출하여 입찰공고를 수집한다.
- 데스크톱 프로그램(bid_search.py)의 검증된 파싱 로직을 웹 백엔드용으로 재구성.
"""
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import requests
import urllib3

from config import Config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BID_BASE_URL = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService"
ENDPOINTS = {
    "물품": "/getBidPblancListInfoThng",
    "공사": "/getBidPblancListInfoCnstwk",
    "용역": "/getBidPblancListInfoServc",
    "외자": "/getBidPblancListInfoFrgcpt",
    "기타": "/getBidPblancListInfoEtc",
}
# UI 표시용 품목 옵션(전체 = 모든 종류 합산)
CATEGORIES = ["전체"] + list(ENDPOINTS.keys())
DATE_TYPE_DIV = {"공고일": "1", "입찰마감일": "2", "개찰일": "3"}
REGIONS = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
           "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]

ROWS_PER_PAGE = 500
REQUEST_TIMEOUT = 30
MAX_RETRIES = 2


class BidApiError(Exception):
    pass


def _request(url, params):
    last = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT,
                             verify=Config.SSL_VERIFY)
            r.raise_for_status()
            return r.text
        except Exception as e:
            last = e
            time.sleep(1.0 * (attempt + 1))
    raise BidApiError(f"네트워크 오류: {last}")


def _text(item, tag, default=""):
    el = item.find(tag)
    return el.text.strip() if el is not None and el.text else default


def _fmt_price(v):
    try:
        return f"{int(float(v)):,}"
    except (ValueError, TypeError):
        return v or ""


def _fmt_date(s):
    if not s:
        return ""
    s = s.strip()
    if "-" in s:
        return s[:10]
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s) >= 8 else s


def _fmt_dt(s):
    if not s:
        return ""
    s = s.strip()
    if "-" in s and ":" in s:
        return s[:16]
    if "-" in s:
        return s[:10]
    if len(s) >= 12:
        return f"{s[:4]}-{s[4:6]}-{s[6:8]} {s[8:10]}:{s[10:12]}"
    return _fmt_date(s)


def _check_api_error(xml_text):
    if not xml_text:
        return "빈 응답"
    if "<OpenAPI_ServiceResponse" in xml_text or "ResponseError" in xml_text:
        try:
            root = ET.fromstring(xml_text)
            code = root.findtext(".//returnReasonCode") or root.findtext(".//resultCode") or ""
            msg = root.findtext(".//returnAuthMsg") or root.findtext(".//resultMsg") or "오류"
            return f"[{code}] {msg}"
        except ET.ParseError:
            return "응답 파싱 실패"
    try:
        root = ET.fromstring(xml_text)
        code = root.findtext(".//resultCode")
        if code and code != "00":
            return f"[{code}] {root.findtext('.//resultMsg') or '오류'}"
    except ET.ParseError:
        return "응답 파싱 실패"
    return None


def _parse(xml_text):
    items, total = [], 0
    root = ET.fromstring(xml_text)
    tc = root.findtext(".//totalCount")
    if tc and tc.isdigit():
        total = int(tc)
    for it in root.findall(".//item"):
        atts = []
        for i in range(1, 11):
            url = _text(it, f"ntceSpecDocUrl{i}")
            if url:
                atts.append({"name": _text(it, f"ntceSpecFileNm{i}") or f"첨부{i}", "url": url})
        items.append({
            "공고번호": _text(it, "bidNtceNo"),
            "차수": _text(it, "bidNtceOrd") or "000",
            "공고명": _text(it, "bidNtceNm"),
            "공고기관": _text(it, "ntceInsttNm"),
            "수요기관": _text(it, "dminsttNm"),
            "예정가격": _fmt_price(_text(it, "presmptPrce")),
            "공고일": _fmt_date(_text(it, "bidNtceDt")),
            "입찰마감일": _fmt_date(_text(it, "bidClseDt")),
            "개찰일시": _fmt_dt(_text(it, "opengDt")),
            "입찰방식": _text(it, "bidMethdNm"),
            "상태": _text(it, "ntceKindNm"),
            "상세URL": _text(it, "bidNtceDtlUrl"),
            "첨부수": len(atts),
            "첨부문서": atts,
        })
    return items, total


def _split_months(start, end):
    """조회기간을 달 경계(최대 1개월) 단위로 분할 — [07] 입력범위값 초과 방지."""
    out, cur = [], start
    while cur <= end:
        if cur.month == 12:
            nxt = datetime(cur.year + 1, 1, cur.day if cur.day <= 28 else 28)
        else:
            # 다음 달 말일 보정
            import calendar
            last = calendar.monthrange(cur.year, cur.month + 1)[1]
            nxt = datetime(cur.year, cur.month + 1, min(cur.day, last))
        ce = min(nxt - timedelta(days=1), end)
        out.append((cur, ce))
        cur = ce + timedelta(days=1)
    return out


def _match_kw(text, keywords):
    if not keywords:
        return True
    t = text.lower()
    return any(k in t for k in keywords)


def _match_region(org, regions):
    if not regions or len(regions) == len(REGIONS):
        return True
    return any(r in org for r in regions)


def _fetch_category(category, div, start_date, end_date, collected, seen):
    """단일 품목 엔드포인트를 달 경계로 분할·페이지 반복 수집. 상한 도달 시 True."""
    url = BID_BASE_URL + ENDPOINTS[category]
    for cs, ce in _split_months(start_date, end_date):
        page = 1
        while True:
            params = {
                "serviceKey": Config.DATA_GO_KR_KEY,
                "pageNo": str(page), "numOfRows": str(ROWS_PER_PAGE),
                "inqryDiv": div,
                "inqryBgnDt": cs.strftime("%Y%m%d") + "0000",
                "inqryEndDt": ce.strftime("%Y%m%d") + "2359",
                "type": "xml",
            }
            xml_text = _request(url, params)
            err = _check_api_error(xml_text)
            if err:
                raise BidApiError(err)
            items, total = _parse(xml_text)
            for r in items:
                bid_id = r["공고번호"]
                if bid_id and bid_id not in seen:
                    seen.add(bid_id)
                    r["구분"] = category
                    collected.append(r)
            if len(collected) >= Config.MAX_RECORDS:
                return True
            if len(items) < ROWS_PER_PAGE or len(collected) >= total:
                break
            page += 1
            time.sleep(0.15)
    return False


def search(category, date_type, start_date, end_date, keyword="", regions=None):
    """입찰공고 검색. category가 '전체'면 모든 종류를 합산한다.
    반환: {"items":[...], "total":n, "capped":bool}"""
    if category == "전체":
        targets = list(ENDPOINTS.keys())
    elif category in ENDPOINTS:
        targets = [category]
    else:
        raise BidApiError("품목은 전체/물품/공사/용역/외자/기타 중 하나여야 합니다.")

    div = DATE_TYPE_DIV.get(date_type, "1")
    keywords = [k.strip().lower() for k in keyword.split(",") if k.strip()]
    regions = regions or []

    collected, seen = [], set()
    capped = False
    for cat in targets:
        if _fetch_category(cat, div, start_date, end_date, collected, seen):
            capped = True
            break

    filtered = [r for r in collected
                if _match_kw(r["공고명"], keywords)
                and _match_region(r["공고기관"] + r["수요기관"], regions)]
    for i, r in enumerate(filtered, 1):
        r["번호"] = i
    return {"items": filtered, "total": len(filtered), "capped": capped}
