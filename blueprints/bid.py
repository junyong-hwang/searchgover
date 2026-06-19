# -*- coding: utf-8 -*-
"""입찰공고 조회 페이지 모듈 (페이지 + JSON API)."""
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify

from services import bid_service

bp = Blueprint("bid", __name__, url_prefix="/bid")


@bp.route("/")
def page():
    return render_template("bid.html", active="bid", regions=bid_service.REGIONS,
                           categories=bid_service.CATEGORIES)


@bp.route("/api/search")
def api_search():
    try:
        category = request.args.get("category", "물품")
        date_type = request.args.get("dateType", "공고일")
        start = datetime.strptime(request.args.get("start", ""), "%Y-%m-%d")
        end = datetime.strptime(request.args.get("end", ""), "%Y-%m-%d")
        keyword = request.args.get("keyword", "")
        regions = [r for r in request.args.get("regions", "").split(",") if r]
    except ValueError:
        return jsonify({"ok": False, "error": "날짜 형식(YYYY-MM-DD)이 올바르지 않습니다."}), 400

    if (end - start).days > 366:
        return jsonify({"ok": False, "error": "조회 기간은 1년 이내로 지정하세요."}), 400

    try:
        result = bid_service.search(category, date_type, start, end, keyword, regions)
        return jsonify({"ok": True, **result})
    except bid_service.BidApiError as e:
        return jsonify({"ok": False, "error": str(e)}), 502
    except Exception as e:
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), 500
