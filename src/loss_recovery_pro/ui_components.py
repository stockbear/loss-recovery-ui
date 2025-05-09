"""
공통 UI 컴포넌트 및 스타일링 함수
"""
import streamlit as st
from typing import Any

def apply_sidebar_style():
    """사이드바 스타일을 적용합니다."""
    st.markdown("""
        <style>
            [data-testid=stSidebar] [data-testid=stVerticalBlock]{
                gap: 0.1rem;
            }
            [data-testid=stSidebar] .stMetric {
                padding-top: 0.5rem;
                padding-bottom: 0.5rem;
            }
        </style>
    """, unsafe_allow_html=True)

def style_profit_cell(value: Any) -> str:
    """데이터 프레임의 셀에 조건부 스타일링을 적용합니다."""
    default_style = "color: black; text-align: right;"
    val_str = str(value)
    if val_str == '∞ (회복불가)' or val_str == 'inf%':
        return f"background-color: #e0e0e0; {default_style}"
    try:
        num_value = float(val_str.replace('%', '').replace('₩', '').replace(',', ''))
        if isinstance(value, str) and '%' in value: # 수익률인 경우
            if num_value < 10.0: return f"background-color: #dcedc8; {default_style}"
            elif num_value < 20.0: return f"background-color: #fff9c4; {default_style}"
            else: return f"background-color: #ffecb3; {default_style}"
        # 다른 숫자 값 (자본, 순수익)은 기본 스타일
        return default_style
    except ValueError:
        return default_style

def display_header():
    """앱 헤더를 표시합니다."""
    st.title("💸 레버리지 손실 복구 계산기 Pro")