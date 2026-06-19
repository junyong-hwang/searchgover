# -*- coding: utf-8 -*-
"""앱 설정. serviceKey 등 민감정보는 환경변수로 주입하고, 없으면 기본값 사용."""
import os


class Config:
    # data.go.kr 공통 인증키 (조달청·공정위 서비스 활용신청 완료된 키).
    # 보안을 위해 코드에 넣지 않고 환경변수로만 주입합니다.
    #  - 로컬 테스트: 실행 전 set DATA_GO_KR_KEY=발급키 (Windows)
    #  - Render 배포: 대시보드 Environment 에 DATA_GO_KR_KEY 추가
    DATA_GO_KR_KEY = os.environ.get("DATA_GO_KR_KEY", "")
    # SSL 검증 (사내망 등에서 문제 시 False)
    SSL_VERIFY = os.environ.get("SSL_VERIFY", "true").lower() == "true"
    # 단일 요청에서 수집할 최대 레코드 수 (응답 지연 방지)
    MAX_RECORDS = int(os.environ.get("MAX_RECORDS", "5000"))
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
