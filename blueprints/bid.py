# -*- coding: utf-8 -*-
"""입찰공고 조회 페이지 모듈 (페이지 + 스트리밍 API)."""
import json
from datetime import datetime

from flask import (Blueprint, render_template, request, jsonify,
                   Response, stream_with_context)

from services import bid_service

bp = Blueprint("bid", __name__, url_prefix="/bid")


@bp.route("/")
def page():
    return render_template("bid.html", active="bid", regions=bid_service.REGIONS,
                           categories=bid_service.CATEGORIES)


@bp.route("/api/search")
def api_search():
    """결과를 NDJSON으로 스트리밍 — 페이지가 들어오는 대로 즉시 전송."""
    try:
        category = request.args.get("category", "물품")
        date_type = request.args.get("dateType", "공고일")
        start = datetime.strptime(request.args.get("start", ""), "%Y-%m-%d")
        end = datetime.strptime(request.args.get("end", ""), "%Y-%m-%d")
        keyword = request.args.get("keyword", "")
        regions = [r for r in request.args.get("regions", "").split(",") if r]
    except ValueError:
        return jsonify({"ok": False, "error": "날짜 형식(YYYY-MM-DD)이 올바르지 않습니다."}), 400
    if end < start:
        return jsonify({"ok": False, "error": "종료일이 시작일보다 빠릅니다."}), 400

    def generate():
        try:
            for ev in bid_service.iter_search(category, date_type, start, end, keyword, regions):
                yield json.dumps(ev, ensure_ascii=False) + "\n"
        except Exception as e:  # noqa
            yield json.dumps({"type": "error", "error": f"{type(e).__name__}: {e}"}) + "\n"

    return Response(stream_with_context(generate()),
                    mimetype="application/x-ndjson",
                    headers={"X-Accel-Buffering": "no",          # 프록시 버퍼링 방지
                             "Cache-Control": "no-cache"})
