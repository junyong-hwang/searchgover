# -*- coding: utf-8 -*-
"""인허가(지방행정 인허가데이터) 조회 페이지 모듈 (페이지 + JSON API)."""
from flask import Blueprint, render_template, request, jsonify

from services import license_service as ls

bp = Blueprint("license", __name__, url_prefix="/license")


@bp.route("/")
def page():
    return render_template("license.html", active="license",
                           industries=ls.INDUSTRIES, sido=ls.SIDO)


@bp.route("/api/search")
def api_search():
    opn = request.args.get("opnSvcId", "")
    if not opn:
        return jsonify({"ok": False, "error": "업종을 선택하세요."}), 400
    bgn = request.args.get("bgn", "").replace("-", "")
    end = request.args.get("end", "").replace("-", "")
    sido = request.args.get("sido", "전체")
    keyword = request.args.get("keyword", "")
    try:
        result = ls.search(opn, bgn, end, sido, keyword)
        return jsonify({"ok": True, **result})
    except ls.LicenseApiError as e:
        return jsonify({"ok": False, "error": str(e)}), 502
    except Exception as e:
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), 500
