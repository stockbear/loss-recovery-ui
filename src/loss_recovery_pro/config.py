# src/loss_recovery_pro/config.py
from typing import Dict

# 증거금 비율(%)과 해당 레버리지 배율 매핑
# 예: 증거금 40%는 레버리지 2.5배를 의미
DEPOSIT_INFO: Dict[int, Dict[str, float]] = {
    100: {"leverage": 1.0, "margin_rate": 1.0},
    60: {"leverage": 1.66, "margin_rate": 0.6},
    50: {"leverage": 2.0, "margin_rate": 0.5},
    40: {"leverage": 2.5, "margin_rate": 0.4},
    30: {"leverage": 3.33, "margin_rate": 0.3},
    20: {"leverage": 5.0, "margin_rate": 0.2},
}

# 거래 수수료율 (편도, 포지션 크기 기준)
# 예: 0.1%는 0.001로 표현
TRANSACTION_FEE_RATE: float = 0.001

# 사용자 입력값 저장을 위한 JSON 파일 경로
USER_CONFIG_FILE: str = "loss_recovery_config.json"

# DataFrame에 표시될 컬럼명 (편집 및 계산에 사용)
COL_TRADE_ROUND = "거래 회차"
COL_MARKET_GAIN_PCT = "시장 수익률(%)" # 사용자가 편집 가능
COL_CUMULATIVE_CAPITAL_AMT = "누적 자본(₩)"
COL_NET_PROFIT_AMT = "회차별 순수익(₩)"