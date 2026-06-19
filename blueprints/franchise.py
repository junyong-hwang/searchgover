# -*- coding: utf-8 -*-
"""가맹점 통계 조회 페이지 모듈 (페이지 + JSON API)."""
from flask import Blueprint, render_template, request, jsonify

from services import franchise_service as fs

bp = Blueprint("franchise", __name__, url_prefix="/franchise")


@bp.route("/")
def page():
    return render_template("franchise.html", active="franchise",
                           columns=fs.COLUMNS, lclas=["전체", "외식", "서비스", "도소매"])


@bp.route("/api/stats")
def api_stats():
    yr = request.args.get("yr", "")
    if not yr.isdigit():
        return jsonify({"ok": False, "error": "연도(yr)를 숫자로 지정하세요."}), 400
    lclas = request.args.get("lclas", "전체")
    mlsfc = request.args.get("mlsfc", "")
    keyword = request.args.get("keyword", "")
    try:
        rows = fs.get_year(yr)
        view = fs.filter_rows(rows, lclas, mlsfc, keyword)
        return jsonify({"ok": True, "columns": fs.COLUMNS, "numeric": list(fs.NUMERIC),
                        "items": view, "total": len(view), "yearTotal": len(rows)})
    except fs.FranchiseApiError as e:
        return jsonify({"ok": False, "error": str(e)}), 502
    except Exception as e:
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), 500


@bp.route("/api/aggregate")
def api_aggregate():
    yr = request.args.get("yr", "")
    if not yr.isdigit():
        return jsonify({"ok": False, "error": "연도(yr)를 숫자로 지정하세요."}), 400
    lclas = request.args.get("lclas", "전체")
    mlsfc = request.args.get("mlsfc", "")
    keyword = request.args.get("keyword", "")
    try:
        rows = fs.get_year(yr)
        view = fs.filter_rows(rows, lclas, mlsfc, keyword)
        return jsonify({"ok": True, "items": fs.aggregate(view)})
    except fs.FranchiseApiError as e:
        return jsonify({"ok": False, "error": str(e)}), 502
    except Exception as e:
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), 500
