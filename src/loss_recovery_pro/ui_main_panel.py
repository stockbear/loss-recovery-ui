# src/loss_recovery_pro/ui_main_panel.py
import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Callable, Optional, Tuple

from .config import DEPOSIT_INFO, TRANSACTION_FEE_RATE, COL_TRADE_ROUND, COL_MARKET_GAIN_PCT, COL_CUMULATIVE_CAPITAL_AMT, COL_NET_PROFIT_AMT
from .calculator import generate_recovery_table_data
from .app_state import get_edited_data_for_table # 콜백에서 edited_data를 업데이트하므로, 여기서는 읽기만 함

def style_data_cell(value: Any) -> str:
    """DataFrame 셀의 값에 따라 스타일을 적용합니다."""
    default_style = "color: black; text-align: right;"
    val_str = str(value)

    if '₩' in val_str and val_str != '₩ 0': # 금액 (0이 아닌 경우)
        try:
            num_val = float(val_str.replace('₩','').replace(',',''))
            if num_val < 0: return f"color: red; {default_style}" # 손실 금액은 빨간색
            return default_style
        except ValueError: # '₩' 포함 문자열이 숫자로 변환 안될 때 (예: 컬럼명에 '₩'이 들어간 경우)
            return "color: black; text-align: center; font-weight: bold;"
    elif val_str == COL_TRADE_ROUND or '₩' in val_str : # 거래 회차 또는 '₩ 0'
            return "color: black; text-align: center; font-weight: bold;" # 회차는 중앙, 굵게
    
    if val_str == '∞ (회복불가)':
        return f"background-color: #E0E0E0; {default_style} font-weight: bold;"

    try: # 수익률(%) 처리
        num_value = float(val_str.replace('%', ''))
        if num_value < 0 : return f"background-color: #FFCDD2; {default_style}" 
        elif num_value < 10.0: return f"background-color: #C8E6C9; {default_style}" 
        elif num_value < 25.0: return f"background-color: #FFF9C4; {default_style}" 
        else: return f"background-color: #FFECB3; {default_style}" 
    except ValueError: # 숫자 변환 안되면 (주로 컬럼명)
        return "color: black; text-align: center; font-weight: bold;"


def parse_edited_value(value_from_editor: Any, type_hint: str = 'pct') -> Optional[float]:
    """
    st.data_editor에서 온 값을 float으로 파싱합니다.
    type_hint: 'pct' (백분율), 'amt' (금액), 'str' (문자열 유지)
    """
    if isinstance(value_from_editor, (int, float)):
        return float(value_from_editor)
    if isinstance(value_from_editor, str):
        cleaned_val = value_from_editor.strip()
        if type_hint == 'pct':
            cleaned_val = cleaned_val.replace('%', '')
        elif type_hint == 'amt':
            cleaned_val = cleaned_val.replace('₩', '').replace(',', '')
        
        # 빈 문자열이거나 변환 불가 특수 문자열이면 None 반환
        if not cleaned_val or cleaned_val in ['∞ (회복불가)', 'N/A', 'inf']:
            return None
        try:
            return float(cleaned_val)
        except ValueError:
            return None # 숫자 변환 실패 시 None
    return None # 그 외 타입은 None

def _prepare_inputs_for_calculator(
    step_count: int,
    tab_idx: int,
    lev_key: int
) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[str]]]:
    """
    저장된 편집 데이터와 마지막 편집 정보를 바탕으로 calculator에 전달할 입력 리스트들을 준비합니다.
    """
    user_fixed_gains: List[Optional[float]] = [None] * step_count
    user_fixed_profits: List[Optional[float]] = [None] * step_count
    user_edit_priority: List[Optional[str]] = [None] * step_count

    latest_stored_df = get_edited_data_for_table(tab_idx, lev_key)
    last_edit_details = st.session_state.get("last_edited_cell_info", {}).get((tab_idx, lev_key))
    
    last_edited_row_idx = -1
    edited_col_name_at_last_edit: Optional[str] = None

    if last_edit_details:
        last_edited_row_idx = last_edit_details.get('row', -1)
        edited_col_name_at_last_edit = last_edit_details.get('col_name')

    if isinstance(latest_stored_df, pd.DataFrame):
        for idx in range(step_count):
            # 사용자가 마지막으로 수정한 행까지만 값을 "고정"값으로 간주하고,
            # 그 이후 행의 값들은 None으로 남겨 calculator가 재계산하도록 함.
            if idx <= last_edited_row_idx:
                if COL_MARKET_GAIN_PCT in latest_stored_df.columns and idx < len(latest_stored_df):
                    user_fixed_gains[idx] = parse_edited_value(latest_stored_df.iloc[idx][COL_MARKET_GAIN_PCT], 'pct')
                if COL_NET_PROFIT_AMT in latest_stored_df.columns and idx < len(latest_stored_df):
                    user_fixed_profits[idx] = parse_edited_value(latest_stored_df.iloc[idx][COL_NET_PROFIT_AMT], 'amt')
            # else: idx > last_edited_row_idx 인 경우, user_fixed_gains/profits는 None으로 유지됨.

        # 마지막으로 편집된 셀의 우선순위 설정
        if last_edit_details and 0 <= last_edited_row_idx < step_count:
            row_edited = last_edited_row_idx # 이미 위에서 last_edited_row_idx로 사용
            if edited_col_name_at_last_edit == COL_MARKET_GAIN_PCT:
                user_edit_priority[row_edited] = 'gain'
                # 수익률이 최종 수정되었으므로, 해당 회차의 순수익은 자동계산되도록 None 처리
                if user_fixed_profits[row_edited] is not None: # 이전에 순수익이 고정되어 있었다면 해제
                     user_fixed_profits[row_edited] = None
            elif edited_col_name_at_last_edit == COL_NET_PROFIT_AMT:
                user_edit_priority[row_edited] = 'profit'
                # 순수익이 최종 수정되었으므로, 해당 회차의 수익률은 자동계산되도록 None 처리
                if user_fixed_gains[row_edited] is not None: # 이전에 수익률이 고정되어 있었다면 해제
                     user_fixed_gains[row_edited] = None
                     
    return user_fixed_gains, user_fixed_profits, user_edit_priority


def render_main_panel(handle_edit_callback: Callable, handle_reset_callback: Callable):
    """메인 패널 UI (결과 테이블 등)를 렌더링합니다."""
    st.title("💸 레버리지 손실 복구 계산기 Pro")
    
    initial_capital = st.session_state.initial_capital
    actual_loss_pct = st.session_state.get("actual_account_loss_pct", 0.0) 
    actual_loss_amt = st.session_state.get("actual_loss_amount", 0.0)

    st.markdown(
        f"초기 원금 **₩ {initial_capital:,.0f}**에서 실제 계좌 총 손실률 "
        f"**`{actual_loss_pct:.2f}%`** (손실액 `₩ {actual_loss_amt:,.0f}`)이 발생한 후, "
        "원금(또는 목표 금액) 회복을 위한 시나리오입니다."
    )
    st.caption(f"각 표의 '{COL_MARKET_GAIN_PCT}' 및 '{COL_NET_PROFIT_AMT}' 컬럼은 직접 수정 가능하며, 수정 시 해당 시나리오가 재계산됩니다. '초기화' 버튼으로 원래 계산값으로 되돌릴 수 있습니다.")

    max_trades = st.session_state.max_recovery_trades
    steps_to_show: List[int] = sorted(list(set([1, 2, 3, 4, 5, max_trades]))) 
    steps_to_show = [s for s in steps_to_show if 0 < s <= max_trades]
    if not steps_to_show and max_trades > 0: steps_to_show.append(max_trades)
    steps_to_show = sorted(list(set(steps_to_show)))

    if not steps_to_show:
        st.warning("표시할 복구 거래 횟수가 없습니다.")
        return
    
    if actual_loss_pct >= 100.0 and not any(st.session_state.edited_data): 
        st.error(f"실제 계좌 손실률이 {actual_loss_pct:.2f}%입니다. '{COL_MARKET_GAIN_PCT}' 또는 '{COL_NET_PROFIT_AMT}' 값을 수동 입력하여 시뮬레이션을 시작할 수 있습니다.")

    tab_titles = [f"{s}회 거래" for s in steps_to_show]
    tabs = st.tabs(tab_titles)

    for i, tab_widget in enumerate(tabs):
        with tab_widget: 
            current_trade_step_count = steps_to_show[i]
            st.subheader(f"🎯 {current_trade_step_count}회 거래로 원금 복구 (목표: ₩ {initial_capital:,.0f})")
            
            sorted_deposit_info = sorted(DEPOSIT_INFO.items(), key=lambda item: item[1]["leverage"], reverse=True)

            for deposit_pct_key, info in sorted_deposit_info:
                recovery_leverage = info["leverage"]
                leverage_label = f"증거금 {deposit_pct_key}% ({recovery_leverage:.2f}배)"
                
                # 테이블 제목과 리셋 버튼을 한 줄에 배치
                title_cols = st.columns([0.85, 0.15])
                with title_cols[0]:
                    st.markdown(f"##### {leverage_label}")
                with title_cols[1]:
                    reset_button_key = f"reset_btn_tab{i}_lev{deposit_pct_key}"
                    if st.button("⚙️ 초기화", key=reset_button_key, help="이 테이블의 모든 사용자 수정을 초기화합니다.", use_container_width=True):
                        handle_reset_callback(i, deposit_pct_key)
                        # 콜백에서 rerun하므로 여기서는 추가 작업 불필요
                
                user_fixed_gains, user_fixed_profits, user_edit_priority = _prepare_inputs_for_calculator(
                    current_trade_step_count, i, deposit_pct_key
                )
                
                table_df = generate_recovery_table_data(
                    initial_capital=initial_capital,
                    actual_total_loss_pct=actual_loss_pct,
                    recovery_leverage=recovery_leverage,
                    trade_steps=current_trade_step_count,
                    edited_gains_pct=user_fixed_gains,
                    edited_net_profits=user_fixed_profits,
                    edited_field_priority=user_edit_priority
                )
                
                editor_key = f"editor_tab{i}_lev{deposit_pct_key}"
                # data_editor에 전달되는 data_to_edit이 prev_df_for_comparison으로 사용됨
                data_to_edit = table_df.copy() # 수정 전 상태를 콜백에 전달하기 위해 복사

                # DataFrame 스타일 적용 (st.dataframe 대신 st.data_editor는 스타일 직접 적용 불가)
                # 따라서, 표시는 data_editor로 하고, 값에 따른 시각적 피드백은 calculator에서 문자열 포맷팅 시 반영
                # 또는 data_editor 이후에 st.dataframe(table_df.style.applymap(style_data_cell))을 추가로 보여줄 수도 있음 (중복 표시)
                # 현재는 style_data_cell 함수는 사용되지 않음. generate_recovery_table_data에서 문자열 포맷팅으로 처리.

                st.data_editor(
                    data_to_edit, 
                    key=editor_key, 
                    use_container_width=True, 
                    num_rows="fixed",
                    disabled=[COL_TRADE_ROUND, COL_CUMULATIVE_CAPITAL_AMT], 
                    hide_index=True, 
                    on_change=handle_edit_callback,
                    args=(i, deposit_pct_key, editor_key, data_to_edit.copy()) 
                )
                st.markdown("---") # 각 레버리지 테이블 구분을 위한 선

    with st.expander("⚠️ 참고 및 주의사항", expanded=False):
        st.markdown(f"""
        - **손실 계산:**
            - 사용자가 입력한 '시장 기준 손실률(%)', '손실 당시 레버리지', 초기 원금을 바탕으로 실제 계좌에 발생한 총 손실률 및 손실 금액이 계산됩니다.
            - 이때, 포지션 진입 시 레버리지된 포지션 크기에 대한 편도 수수료 (`{TRANSACTION_FEE_RATE*100:.1f}%`)가 손실에 포함됩니다.
        - **복구 계산:**
            - 계산된 '실제 계좌 총 손실률'을 기준으로, 원금을 회복하기 위해 각 거래 회차마다 필요한 '{COL_MARKET_GAIN_PCT}', '{COL_CUMULATIVE_CAPITAL_AMT}', '{COL_NET_PROFIT_AMT}'을 보여줍니다.
            - 사용자는 각 레버리지 조건 테이블의 **'{COL_MARKET_GAIN_PCT}'** 또는 **'{COL_NET_PROFIT_AMT}'** 컬럼 값을 직접 수정할 수 있습니다.
            - 하나의 값을 수정하면 다른 값 및 **수정된 행 이후의 모든 회차들**이 연동되어 재계산됩니다.
            - 복구 시도 시에도 각 거래마다 해당 거래에 사용된 레버리지와 포지션 크기에 대한 편도 수수료 (`{TRANSACTION_FEE_RATE*100:.1f}%`)가 반영됩니다.
        - **복리 계산:** 모든 자본 계산은 복리 기준입니다.
        - **'∞ (회복불가)':** 해당 조건으로는 원금 회복이 수학적으로 불가능함을 의미합니다.
        - **수익률 색상 가이드 (수익률 % 기준):** (generate_recovery_table_data에서 문자열 포맷으로 처리, style_data_cell은 data_editor에 직접 적용 안됨)
            - 표시되는 값의 배경색은 현재 지원되지 않으며, 값 자체의 포맷팅(예: '∞ (회복불가)')으로 구분됩니다.
        - **초기화 버튼:** 각 표 우측 상단의 '⚙️ 초기화' 버튼을 누르면 해당 표의 모든 사용자 수정 내용이 사라지고, 원래의 자동 계산 값으로 돌아갑니다.
        - **단순 시뮬레이션:** 본 결과는 시장 변동성, 슬리피지 등 실제 거래 변수를 고려하지 않은 단순 계산 결과입니다. 투자 결정은 신중히 하세요.
        """, unsafe_allow_html=True)