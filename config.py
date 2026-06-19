# -*- coding: utf-8 -*-
"""앱 설정. serviceKey 등 민감정보는 환경변수로 주입하고, 없으면 기본값 사용."""
import os


class Config:
    # data.go.kr 공통 인증키 (조달청·공정위 서비스 활용신청 완료된 키).
    # 보안을 위해 코드에 넣지 않고 환경변수로만 주입합니다.
    #  - 로컬 테스트: 실행 전 set DATA_GO_KR_KEY=발급키 (Windows)
    #  - Render 배포: 대시보드 Environment 에 DATA_GO_KR_KEY 추가
    DATA_GO_KR_KEY = os.environ.get("DATA_GO_KR_KEY", "")
    # 지방행정 인허가데이터(LOCALDATA) — localdata.go.kr 폐쇄(2026-04) 후 신 포털.
    #  엔드포인트/키는 환경변수로 주입(포털에서 활용신청 후 받은 값).
    #  - LOCALDATA_KEY  : 인허가 API 인증키(authKey)
    #  - LICENSE_API_URL: REST openDataApi 요청 URL (신 포털 주소로 교체)
    LOCALDATA_KEY = os.environ.get("LOCALDATA_KEY", "")
    LICENSE_API_URL = os.environ.get(
        "LICENSE_API_URL",
        "https://www.localdata.kr/platform/rest/TO0/openDataApi",
    )

    # SSL 검증 (사내망 등에서 문제 시 False)
    SSL_VERIFY = os.environ.get("SSL_VERIFY", "true").lower() == "true"
    # 단일 요청에서 수집할 최대 레코드 수 (웹 응답시간/메모리 보호).
    # 기간이 매우 길면 이 상한에서 멈추고 'capped'로 알림. 더 키우려면 환경변수로.
    MAX_RECORDS = int(os.environ.get("MAX_RECORDS", "10000"))
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
