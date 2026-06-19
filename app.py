# -*- coding: utf-8 -*-
"""
Flask 앱 진입점. 페이지별 모듈(blueprint)을 등록한다.

실행:
    pip install -r requirements.txt
    python app.py            # http://localhost:5000
운영:
    gunicorn -w 2 -b 0.0.0.0:8000 "app:create_app()"
"""
from flask import Flask

from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    from blueprints.main import bp as main_bp
    from blueprints.bid import bp as bid_bp
    from blueprints.franchise import bp as franchise_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(bid_bp)
    app.register_blueprint(franchise_bp)
    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
