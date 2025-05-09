# src/loss_recovery_pro/app_state.py
import streamlit as st
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

from .config import USER_CONFIG_FILE, DEPOSIT_INFO
# calculator 임포트는 여기서 직접 사용하지 않으면 제거 가능, ui_sidebar에서 사용
# from .calculator import calculate_actual_account_metrics

def _get_default_app_state() -> Dict[str, Any]:
    """애플리케이션의 기본 상태값을 반환합니다."""
    sorted_deposit_keys = sorted(DEPOSIT_INFO.keys(), reverse=True)
    
    # 기본값 정의 (초기 로드 시 사용)
    initial_capital_default = 1000000.0
    market_loss_default = 7.67
    loss_margin_default = 40 # 증거금 %
    
    # 초기 손실 금액은 앱 실행 시 ui_sidebar에서 계산되어 session_state에 설정됨
    # 여기서는 플레이스홀더 또는 0으로 둘 수 있음. 또는 계산 로직을 여기에 포함.
    # 편의상 여기서는 기본값 계산 로직을 제거하고, ui_sidebar에서 초기화하도록 함.
    # 실제 앱에서는 ui_sidebar에서 초기 계산된 값이 여기 session_state에 반영됨.

    return {
        "initial_capital": initial_capital_default,
        "market_loss_input_pct": market_loss_default,
        "loss_margin_pct_at_loss": loss_margin_default,
        "actual_loss_amount": 0.0, # 초기값. ui_sidebar에서 실제 값으로 계산/업데이트됨.
        "max_recovery_trades": 5,
        "edited_data": {}, # 탭별, 레버리지별 수정된 DataFrame 저장
        "_sorted_deposit_keys": sorted_deposit_keys,
        "_config_loaded": False,
        "_last_financial_input_source": "initial_capital", # "initial_capital" 또는 "loss_amount"
    }

def reset_edited_data_for_table(tab_index: int, recovery_leverage_key: int):
    """특정 테이블에 대한 사용자 수정 정보를 초기화합니다."""
    edit_key = (tab_index, recovery_leverage_key)
    if edit_key in st.session_state.edited_data:
        del st.session_state.edited_data[edit_key]
        # print(f"DEBUG: Reset edited_data for {edit_key}")
    
    if "last_edited_cell_info" in st.session_state and \
       edit_key in st.session_state.last_edited_cell_info:
        del st.session_state.last_edited_cell_info[edit_key]
        # print(f"DEBUG: Reset last_edited_cell_info for {edit_key}")
        
def load_user_config() -> Dict[str, Any]:
    config_path = Path(USER_CONFIG_FILE)
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            try: return json.load(f)
            except json.JSONDecodeError: return {}
    return {}

def save_user_config(state_to_save: Dict[str, Any]):
    keys_to_save = ["initial_capital", "market_loss_input_pct",
                    "loss_margin_pct_at_loss", "max_recovery_trades",
                    "actual_loss_amount"] # 'actual_loss_amount_input' 대신 'actual_loss_amount' 사용
    
    config_data = {key: state_to_save.get(key) for key in keys_to_save if key in state_to_save}

    with open(USER_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=4)

def init_session_state():
    if "_config_loaded" not in st.session_state or not st.session_state._config_loaded:
        default_state = _get_default_app_state()
        user_config = load_user_config()

        for key, default_value in default_state.items():
            # 위젯 생성 전에 session_state를 초기화하므로, 위젯 값과 충돌 없음.
            # 사용자 설정 파일 값 > 기본 상태 값 순으로 우선순위.
            st.session_state[key] = user_config.get(key, default_value)
        
        st.session_state._sorted_deposit_keys = sorted(DEPOSIT_INFO.keys(), reverse=True)
        if st.session_state.loss_margin_pct_at_loss not in st.session_state._sorted_deposit_keys:
            st.session_state.loss_margin_pct_at_loss = 40 
        
        st.session_state._config_loaded = True
        # 초기 로드 후, 실제 값 계산 및 동기화는 ui_sidebar에서 수행

def update_state_and_save_config(key: str, value: Any, source_field: Optional[str] = None):
    st.session_state[key] = value
    if source_field: # 어떤 필드 변경으로 이 업데이트가 트리거됐는지 기록
        st.session_state._last_financial_input_source = source_field
    # save_user_config(st.session_state)

def update_edited_data(tab_index: int, recovery_leverage_key: int, edited_df: pd.DataFrame):
    st.session_state.edited_data[(tab_index, recovery_leverage_key)] = edited_df

def get_edited_data_for_table(tab_index: int, recovery_leverage_key: int) -> Optional[pd.DataFrame]:
    return st.session_state.edited_data.get((tab_index, recovery_leverage_key))