# -*- coding: utf-8 -*-
"""
인허가(지방행정 인허가데이터) 조회 서비스 계층.
- 행정안전부 재난안전데이터 공유플랫폼(safetydata.go.kr) OpenAPI 사용.
  요청: https://www.safetydata.go.kr/V2/api/{인터페이스ID}
        ?serviceKey=&returnType=json&pageNo=&numOfRows=(최대 1000)
  응답(JSON): {"header":{"resultCode","resultMsg"}, "totalCount", "body":[{...}]}
- 서버측 필터가 없어 지역(시도)/사업장명/인허가일은 로컬 필터로 처리.

[env] LOCALDATA_KEY = safetydata.go.kr 발급 serviceKey
      (인터페이스별 활용신청 필요. 키는 신청한 인터페이스에서만 동작)
"""
from collections import OrderedDict

import requests
import urllib3

from config import Config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_BASE = "https://www.safetydata.go.kr/V2/api/"
PAGE_SIZE = 1000
REQUEST_TIMEOUT = 30
MAX_RETRIES = 2

# 업종 표시명 → 인터페이스 ID (활용신청된 것만 동작)
INDUSTRIES = [
    ("일반음식점", "DSSP-IF-20103"),
]
SIDO = ["전체", "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
        "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]

RENAME = OrderedDict([
    ("BUES_NM", "사업장명"), ("TPBIZ_NM", "업종"), ("PRMSN_YMD", "인허가일자"),
    ("RPRSV_NM", "대표자"), ("TELNO", "전화번호"), ("ADDR", "주소"),
    ("SALS_UNQ_SE_NO_LCPMT_NO", "인허가번호"),
])


class LicenseApiError(Exception):
    pass


def _request(iface, page):
    params = {"serviceKey": Config.LOCALDATA_KEY, "returnType": "json",
              "pageNo": str(page), "numOfRows": str(PAGE_SIZE)}
    last = None
    for _ in range(MAX_RETRIES + 1):
        try:
            r = requests.get(API_BASE + iface, params=params,
                             timeout=REQUEST_TIMEOUT, verify=Config.SSL_VERIFY)
            r.encoding = "utf-8"
            return r.text
        except Exception as e:
            last = e
    raise LicenseApiError(f"safetydata.go.kr 연결 실패: {last}")


def _parse(text):
    import json
    d = json.loads(text)
    header = d.get("header", {}) or {}
    code = header.get("resultCode")
    if code and str(code) != "00":
        raise LicenseApiError(f"[{code}] {header.get('resultMsg') or header.get('errorMsg') or '오류'}")
    total = int(d.get("totalCount") or 0)
    rows = d.get("body") or []
    return [{k: ("" if v is None else str(v)).strip() for k, v in r.items()} for r in rows], total


def columns_for(rows):
    present = OrderedDict()
    for r in rows:
        for k in r:
            present[k] = True
    keys = [k for k in RENAME if k in present] + [k for k in present if k not in RENAME]
    return keys, [RENAME.get(k, k) for k in keys]


def search(iface, sido="전체", keyword="", bgn="", end="", max_records=20000):
    if not Config.LOCALDATA_KEY:
        raise LicenseApiError("인허가 인증키(LOCALDATA_KEY)가 설정되지 않았습니다. "
                              "safetydata.go.kr 발급 serviceKey를 환경변수로 넣으세요.")
    if not iface:
        raise LicenseApiError("업종(인터페이스 ID)을 지정하세요.")
    collected, page, total = [], 1, None
    capped = False
    while True:
        rows, tc = _parse(_request(iface, page))
        if total is None:
            total = tc
        collected.extend(rows)
        if not rows or (total and len(collected) >= total):
            break
        if len(collected) >= max_records:
            capped = True
            break
        page += 1

    kw = (keyword or "").strip().lower()

    def keep(r):
        if sido and sido != "전체" and sido not in r.get("ADDR", ""):
            return False
        if kw and kw not in r.get("BUES_NM", "").lower():
            return False
        ymd = r.get("PRMSN_YMD", "")
        if bgn and ymd and ymd < bgn:
            return False
        if end and ymd and ymd > end:
            return False
        return True

    view = [r for r in collected if keep(r)]
    keys, labels = columns_for(view or collected)
    items = [{lbl: r.get(k, "") for k, lbl in zip(keys, labels)} for r in view]
    return {"columns": labels, "items": items, "total": len(view),
            "fetched": len(collected), "grandTotal": total or 0, "capped": capped}
