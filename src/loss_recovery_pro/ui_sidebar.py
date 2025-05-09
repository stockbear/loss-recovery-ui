# src/loss_recovery_pro/ui_sidebar.py
import streamlit as st
import math
from .app_state import update_state_and_save_config
from .config import DEPOSIT_INFO
from .calculator import calculate_actual_account_metrics, calculate_initial_capital_from_loss_amount

def render_sidebar():
    st.markdown("""
        <style>
            [data-testid=stSidebar] [data-testid=stVerticalBlock]{ gap: 0.1rem; }
            [data-testid=stSidebar] .stMetric { padding-top: 0.5rem; padding-bottom: 0.5rem; }
            [data-testid=stSidebar] .stSlider { padding-top: 0.3rem; padding-bottom: 0.3rem; }
            [data-testid=stSidebar] .stSelectbox { padding-top: 0.3rem; padding-bottom: 0.3rem; }
            [data-testid=stSidebar] .stNumberInput { padding-top: 0.3rem; padding-bottom: 0.3rem; }
            [data-testid=stSidebar] hr { margin-top: 0.5rem; margin-bottom: 0.5rem; }
            [data-testid=stSidebar] h3 { margin-top: 0.8rem; margin-bottom: 0.3rem; }
        </style>
    """, unsafe_allow_html=True)

    st.sidebar.title("⚙️ 입력 설정")
    st.sidebar.caption("변경사항은 자동으로 파일에 저장됩니다.")

    # --- 콜백 함수 정의 ---
    def sync_financials_on_change(changed_field_key: str):
        # 이 함수는 주요 입력(원금, 손실금, 시장손실률, 증거금비율) 변경 시 호출됨
        
        # 현재 위젯 값들을 session_state의 주 변수에 반영
        if changed_field_key == "initial_capital":
            st.session_state.initial_capital = st.session_state.sb_initial_capital
            st.session_state._last_financial_input_source = "initial_capital"
        elif changed_field_key == "actual_loss_amount":
            st.session_state.actual_loss_amount = st.session_state.sb_actual_loss_amount
            st.session_state._last_financial_input_source = "loss_amount"
        elif changed_field_key == "market_loss_input_pct":
            st.session_state.market_loss_input_pct = st.session_state.sb_market_loss_input_pct
        elif changed_field_key == "loss_margin_pct_at_loss":
            st.session_state.loss_margin_pct_at_loss = st.session_state.sb_loss_margin_pct_at_loss
            
        # 현재 선택된 레버리지 (항상 최신 값 사용)
        current_leverage_at_loss = DEPOSIT_INFO[st.session_state.loss_margin_pct_at_loss]["leverage"]

        # 마지막 사용자 입력 소스에 따라 다른 필드 값을 조정
        if st.session_state._last_financial_input_source == "initial_capital" or \
           changed_field_key in ["market_loss_input_pct", "loss_margin_pct_at_loss"]:
            # 원금, 시장손실률, 증거금비율이 바뀌면 손실금 재계산
            _, calculated_loss_amount = calculate_actual_account_metrics(
                st.session_state.initial_capital,
                st.session_state.market_loss_input_pct,
                current_leverage_at_loss
            )
            st.session_state.actual_loss_amount = round(calculated_loss_amount, 0)
        
        elif st.session_state._last_financial_input_source == "loss_amount":
            # 손실금이 바뀌면 원금 재계산
            calculated_capital = calculate_initial_capital_from_loss_amount(
                st.session_state.actual_loss_amount,
                st.session_state.market_loss_input_pct,
                current_leverage_at_loss
            )
            if not math.isnan(calculated_capital):
                st.session_state.initial_capital = round(calculated_capital, 0)
        
        # 모든 변경 후 설정 저장 (하나의 함수에서 모든 업데이트 처리 후 저장)
        # save_user_config_keys = ["initial_capital", "market_loss_input_pct", "loss_margin_pct_at_loss", "actual_loss_amount", "max_recovery_trades"]
        # config_to_save = {k:st.session_state[k] for k in save_user_config_keys}
        # from .app_state import save_user_config # 순환참조 피하기 위해 여기서 임포트
        # save_user_config(config_to_save)


    # --- 입력 위젯들 ---
    st.sidebar.number_input(
        "초기 원금 (₩)", min_value=0.0, value=float(st.session_state.initial_capital),
        step=100000.0, format="%.0f", key="sb_initial_capital",
        on_change=sync_financials_on_change, args=("initial_capital",),
        help="투자를 시작한 초기 원금 총액을 입력합니다."
    )

    st.sidebar.number_input(
        "시장 기준 손실률 (%)", min_value=0.0, max_value=100.0,
        value=st.session_state.market_loss_input_pct, step=0.1, format="%.2f",
        key="sb_market_loss_input_pct", on_change=sync_financials_on_change, args=("market_loss_input_pct",),
        help="레버리지 및 수수료 적용 전, 순수 시장 가격 하락률(%)을 입력합니다."
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("📌 손실 발생 당시 조건")

    current_loss_margin_index = 0
    if st.session_state.loss_margin_pct_at_loss in st.session_state._sorted_deposit_keys:
        current_loss_margin_index = st.session_state._sorted_deposit_keys.index(st.session_state.loss_margin_pct_at_loss)

    st.sidebar.selectbox(
        "손실 당시 증거금 비율 (%)", options=st.session_state._sorted_deposit_keys,
        index=current_loss_margin_index, key="sb_loss_margin_pct_at_loss",
        on_change=sync_financials_on_change, args=("loss_margin_pct_at_loss",),
        help="실제 손실이 발생했을 때 사용하고 있던 증거금 비율을 선택합니다."
    )
    
    leverage_at_loss_display = DEPOSIT_INFO[st.session_state.loss_margin_pct_at_loss]["leverage"]
    st.sidebar.markdown(f"**손실 당시 레버리지: `{leverage_at_loss_display:.2f}`배**")

    st.sidebar.markdown("---")
    st.sidebar.subheader("📉 계산된 손실 정보")
    
    # "실제 손실 금액" 입력 필드 - 이 값은 sync_financials_on_change에 의해 업데이트됨
    st.sidebar.number_input(
        "실제 손실 금액 (₩)", min_value=0.0, value=float(st.session_state.actual_loss_amount),
        step=10000.0, format="%.0f", key="sb_actual_loss_amount",
        on_change=sync_financials_on_change, args=("actual_loss_amount",),
        help="실제 발생한 손실 금액을 입력하면, 초기 원금이 역산됩니다. 또는 초기 원금에 따라 자동 계산됩니다."
    )

    # 실제 계좌 손실률은 항상 위 값들을 기준으로 계산되어 표시됨
    # 이 시점에는 st.session_state.initial_capital 과 st.session_state.actual_loss_amount가 동기화된 상태여야 함.
    final_actual_loss_percentage, _ = calculate_actual_account_metrics(
        st.session_state.initial_capital,
        st.session_state.market_loss_input_pct,
        leverage_at_loss_display
    )
    # 이 값을 메인 패널 등에서 사용할 수 있도록 session_state에 저장
    st.session_state.actual_account_loss_pct = final_actual_loss_percentage 

    st.sidebar.metric(
        label="실제 계좌 총 손실률", value=f"{st.session_state.actual_account_loss_pct:.2f}%",
        delta="원금 대비" if st.session_state.actual_account_loss_pct < 100 else "원금 전액 이상 손실",
        delta_color="inverse" if st.session_state.actual_account_loss_pct < 100 else "normal"
    )
    if st.session_state.actual_account_loss_pct >= 100.0 and st.session_state.initial_capital > 0 :
        st.sidebar.error("전액 또는 초과 손실로, 수학적 원금 회복이 불가능할 수 있습니다.")

    st.sidebar.markdown("---")
    st.sidebar.subheader("♻️ 복구 시도 조건")
    
    max_trades_val = st.sidebar.slider( # 슬라이더는 on_change 콜백에서 직접 update_state_and_save_config 호출
        "최대 복구 거래 횟수", min_value=1, max_value=20,
        value=st.session_state.max_recovery_trades, key="sb_max_recovery_trades",
        help="손실된 원금을 복구하기 위해 시도할 최대 거래 횟수를 설정합니다.",
        on_change=lambda: update_state_and_save_config("max_recovery_trades", st.session_state.sb_max_recovery_trades)
    )
    st.sidebar.markdown("---")
    st.sidebar.caption("© 2024-2025 Loss Recovery Pro")