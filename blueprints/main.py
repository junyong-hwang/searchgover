# -*- coding: utf-8 -*-
"""메인(홈) 페이지 모듈."""
from flask import Blueprint, render_template

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    return render_template("index.html", active="home")
