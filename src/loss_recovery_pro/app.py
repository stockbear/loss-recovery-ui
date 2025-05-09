# src/loss_recovery_pro/app.py

# 1. 표준 라이브러리 임포트 (sys, pathlib 먼저)
import sys
from pathlib import Path

# 2. sys.path 조작 (다른 어떤 임포트보다 먼저 수행)
APP_DIR = Path(__file__).resolve().parent
SRC_DIR = APP_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# 3. 이제 다른 라이브러리 및 프로젝트 모듈 임포트
import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any, List # 여기에 필요한 모든 타입 힌트

# 프로젝트 모듈 임포트 (이제 loss_recovery_pro 패키지를 찾을 수 있어야 함)
from loss_recovery_pro.app_state import init_session_state, update_edited_data, reset_edited_data_for_table # reset_edited_data_for_table 추가
# get_edited_data_for_table은 app.py에서 직접 사용하지 않으므로 제거해도 됨 (ui_main_panel에서 사용)
from loss_recovery_pro.ui_sidebar import render_sidebar
from loss_recovery_pro.ui_main_panel import render_main_panel, parse_edited_value
from loss_recovery_pro.config import COL_MARKET_GAIN_PCT, COL_NET_PROFIT_AMT

# ... (나머지 함수 정의: find_changed_cell_from_edit_dict, handle_data_editor_change 등은 기존과 동일하게 유지) ...

def find_changed_cell_from_edit_dict(edit_dict: Dict[str, Any], old_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    st.data_editor가 반환한 edit_dict (예: {'edited_rows':...}) 와 원본 DataFrame을 기반으로
    실제 변경된 첫 번째 셀 정보를 반환합니다.
    """
    if "edited_rows" in edit_dict and edit_dict["edited_rows"]:
        for row_idx_str, changed_cols_dict in edit_dict["edited_rows"].items():
            try:
                row_idx = int(row_idx_str) # DataFrame 인덱스가 정수라고 가정
                for col_name, new_value_str in changed_cols_dict.items():
                    if 0 <= row_idx < len(old_df) and col_name in old_df.columns:
                        # 사용자가 입력한 값은 문자열일 수 있음
                        type_hint_for_parsing = 'pct' if '%' in col_name or col_name == COL_MARKET_GAIN_PCT else \
                                               'amt' if '₩' in col_name or col_name == COL_NET_PROFIT_AMT or col_name == "누적 자본(₩)" else \
                                               'str' # COL_CUMULATIVE_CAPITAL_AMT 대신 실제 문자열 사용 (config.py 와 일치 확인 필요)

                        parsed_new_val = parse_edited_value(new_value_str, type_hint_for_parsing)
                        
                        return {"row": row_idx, "col_name": col_name, "new_value": parsed_new_val}
            except (ValueError, IndexError, KeyError) as e:
                print(f"Warning: Error processing edited_rows in find_changed_cell_from_edit_dict: {e}")
                continue 
    return None


def apply_edits_to_dataframe(original_df: pd.DataFrame, edit_info_dict: Dict[str, Any]) -> pd.DataFrame:
    """
    st.data_editor가 반환한 edit_info_dict (예: {'edited_rows':...})를
    원본 DataFrame에 적용하여 수정된 DataFrame을 반환합니다.
    """
    df_copy = original_df.copy()
    if "edited_rows" in edit_info_dict:
        for row_idx_str, changed_cols_dict in edit_info_dict["edited_rows"].items():
            try:
                row_idx = int(row_idx_str) 
                if 0 <= row_idx < len(df_copy):
                    for col_name, new_value_str in changed_cols_dict.items():
                        if col_name in df_copy.columns:
                            df_copy.loc[df_copy.index[row_idx], col_name] = new_value_str
            except ValueError:
                print(f"Warning: Could not convert row index '{row_idx_str}' to int in apply_edits.")
            except Exception as e:
                print(f"Error applying edit to DataFrame in apply_edits: {e}")
    return df_copy


def handle_data_editor_change(tab_idx: int, lev_key: int, editor_widget_key: str, prev_df_for_comparison: pd.DataFrame):
    if editor_widget_key not in st.session_state:
        st.error(f"편집기 키 '{editor_widget_key}'가 세션 상태에 없습니다.")
        return

    edit_info_dict = st.session_state[editor_widget_key] 
    updated_df: Optional[pd.DataFrame] = None 

    if not isinstance(edit_info_dict, dict):
        if isinstance(st.session_state[editor_widget_key], pd.DataFrame): 
            updated_df = st.session_state[editor_widget_key].copy()
        else:
            st.error(f"편집기 데이터가 예상된 dict 또는 DataFrame 타입이 아닙니다 (타입: {type(st.session_state[editor_widget_key])}). 업데이트 안됨.", icon="❌")
            return
    elif not edit_info_dict.get("edited_rows") and \
         not edit_info_dict.get("added_rows") and \
         not edit_info_dict.get("deleted_rows"):
        from loss_recovery_pro.app_state import get_edited_data_for_table # 여기서 임포트
        existing_df = get_edited_data_for_table(tab_idx, lev_key) 
        if existing_df is None and prev_df_for_comparison is not None:
             update_edited_data(tab_idx, lev_key, prev_df_for_comparison.copy())
        return
    else: 
        try:
            updated_df = apply_edits_to_dataframe(prev_df_for_comparison, edit_info_dict)
        except Exception as e:
            st.error(f"편집 내용을 DataFrame에 적용 중 오류 발생: {e}. 업데이트 안됨.", icon="❌")
            print(f"ERROR_DETAILS: Failed to apply edits. Edit dict: {edit_info_dict}, Prev DF: \n{prev_df_for_comparison.to_string()}")
            return

    if updated_df is not None: 
        changed_cell_info = find_changed_cell_from_edit_dict(edit_info_dict, prev_df_for_comparison)
        
        if changed_cell_info:
            if "last_edited_cell_info" not in st.session_state:
                st.session_state["last_edited_cell_info"] = {}
            st.session_state["last_edited_cell_info"][(tab_idx, lev_key)] = changed_cell_info
        else:
            if "last_edited_cell_info" in st.session_state:
                st.session_state["last_edited_cell_info"].pop((tab_idx, lev_key), None)
                
        update_edited_data(tab_idx, lev_key, updated_df)

def run_app():
    init_session_state()
    render_sidebar()
    # render_main_panel 호출 시 handle_reset_callback 인자 추가
    render_main_panel(
        handle_edit_callback=handle_data_editor_change,
        handle_reset_callback=reset_edited_data_for_table # 추가된 부분
    )

if __name__ == "__main__":
    run_app()