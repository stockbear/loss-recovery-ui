# src/loss_recovery_pro/calculator.py
import pandas as pd
from typing import Tuple, List, Dict, Any, Optional
from .config import TRANSACTION_FEE_RATE, DEPOSIT_INFO, COL_MARKET_GAIN_PCT, COL_CUMULATIVE_CAPITAL_AMT, COL_NET_PROFIT_AMT, COL_TRADE_ROUND


def calculate_actual_account_metrics(
    initial_capital: float,
    market_loss_input_pct: float,
    loss_leverage: float
) -> Tuple[float, float]:
    # (이전과 동일)
    if initial_capital <= 0:
        return 0.0, 0.0
    market_loss_ratio = market_loss_input_pct / 100.0
    fee_on_entry_ratio = loss_leverage * TRANSACTION_FEE_RATE
    leveraged_market_loss_ratio = market_loss_ratio * loss_leverage
    total_loss_on_capital_ratio = leveraged_market_loss_ratio + fee_on_entry_ratio
    actual_loss_percentage = total_loss_on_capital_ratio * 100.0
    actual_loss_amount = initial_capital * total_loss_on_capital_ratio
    return actual_loss_percentage, actual_loss_amount

def calculate_initial_capital_from_loss_amount(
    actual_loss_amount_input: float,
    market_loss_input_pct: float,
    loss_leverage: float
) -> float:
    # (이전과 동일)
    if actual_loss_amount_input < 0: return 0.0
    market_loss_ratio = market_loss_input_pct / 100.0
    fee_on_entry_ratio = loss_leverage * TRANSACTION_FEE_RATE
    leveraged_market_loss_ratio = market_loss_ratio * loss_leverage
    total_loss_on_capital_ratio = leveraged_market_loss_ratio + fee_on_entry_ratio
    if total_loss_on_capital_ratio <= 0:
        if actual_loss_amount_input > 0 : return float('nan')
        return 0.0
    initial_capital = actual_loss_amount_input / total_loss_on_capital_ratio
    return initial_capital if initial_capital >= 0 else 0.0

def calculate_market_gain_from_net_profit(
    net_profit_amount: float,
    capital_at_step_start: float,
    recovery_leverage: float
) -> Optional[float]:
    """
    해당 회차의 목표 순수익 금액을 달성하기 위한 시장 수익률(%)을 역계산합니다.
    """
    if capital_at_step_start <= 0: # 시작 자본이 없으면 수익률 계산 불가
        return float('inf') if net_profit_amount > 0 else 0.0 # 손실인데 이익을 원하면 무한대
    if recovery_leverage == 0: # 레버리지 0이면
        return float('inf') if net_profit_amount > 0 else 0.0 # 이익을 원하면 무한대 수익률 필요

    # net_profit_amount = capital_at_step_start * (market_gain_ratio * recovery_leverage - trade_fee_ratio_on_position)
    # market_gain_ratio * recovery_leverage = (net_profit_amount / capital_at_step_start) + trade_fee_ratio_on_position
    # market_gain_ratio = ((net_profit_amount / capital_at_step_start) + trade_fee_ratio_on_position) / recovery_leverage
    
    trade_fee_ratio_on_position = recovery_leverage * TRANSACTION_FEE_RATE
    
    try:
        market_gain_ratio = ((net_profit_amount / capital_at_step_start) + trade_fee_ratio_on_position) / recovery_leverage
        return market_gain_ratio * 100.0 # %로 변환
    except ZeroDivisionError: # recovery_leverage가 0인 경우 (위에서 이미 처리했지만 방어용)
        return float('inf') if net_profit_amount > 0 else 0.0


def generate_recovery_table_data(
    initial_capital: float,
    actual_total_loss_pct: float,
    recovery_leverage: float,
    trade_steps: int,
    edited_gains_pct: Optional[List[Optional[float]]] = None,
    edited_net_profits: Optional[List[Optional[float]]] = None,
    # edited_field_priority는 어떤 필드가 "수정"되었음을 나타냄.
    # 예: edited_field_priority[n] == 'gain' 이면, n회차는 edited_gains_pct[n]을 사용.
    # 예: edited_field_priority[n] == 'profit' 이면, n회차는 edited_net_profits[n]을 사용하고 이를 바탕으로 gain 계산.
    edited_field_priority: Optional[List[Optional[str]]] = None
) -> pd.DataFrame:
    # ... (초기 빈 테이블 반환 로직 등은 이전과 동일) ...
    if initial_capital <= 0:
        empty_data = {COL_TRADE_ROUND: [f"{i+1}회차" for i in range(trade_steps)], COL_MARKET_GAIN_PCT: ['N/A'] * trade_steps, COL_CUMULATIVE_CAPITAL_AMT: [f"₩ 0"] * trade_steps, COL_NET_PROFIT_AMT: [f"₩ 0"] * trade_steps}
        return pd.DataFrame(empty_data)

    all_gains_none = not edited_gains_pct or all(g is None for g in edited_gains_pct)
    all_profits_none = not edited_net_profits or all(p is None for p in edited_net_profits)

    if actual_total_loss_pct >= 100.0 and all_gains_none and all_profits_none:
        empty_data = {COL_TRADE_ROUND: [f"{i+1}회차" for i in range(trade_steps)], COL_MARKET_GAIN_PCT: ['∞ (회복불가)'] * trade_steps, COL_CUMULATIVE_CAPITAL_AMT: [f"₩ 0"] * trade_steps, COL_NET_PROFIT_AMT: [f"₩ 0"] * trade_steps}
        return pd.DataFrame(empty_data)

    remaining_capital_after_loss = initial_capital * max(0, (1.0 - actual_total_loss_pct / 100.0))
    current_capital_amount_for_step_start = remaining_capital_after_loss
    target_final_capital = initial_capital
    data_rows = []

    # 확정된 (사용자 입력 또는 이전 계산 결과) 시장 수익률 저장용
    final_market_gains_for_steps: List[Optional[float]] = [None] * trade_steps

    for n in range(trade_steps):
        trade_fee_ratio_on_position = recovery_leverage * TRANSACTION_FEE_RATE
        market_gain_pct_this_step: float # 이번 스텝에서 사용할 확정된 시장 수익률

        # 현재 회차의 우선순위 필드 및 값 확인
        priority_this_step = edited_field_priority[n] if edited_field_priority and n < len(edited_field_priority) and edited_field_priority[n] is not None else 'gain' # 기본은 수익률 우선
        user_edited_gain = edited_gains_pct[n] if edited_gains_pct and n < len(edited_gains_pct) and edited_gains_pct[n] is not None else None
        user_edited_profit = edited_net_profits[n] if edited_net_profits and n < len(edited_net_profits) and edited_net_profits[n] is not None else None

        is_user_edited_this_step = False

        if priority_this_step == 'profit' and user_edited_profit is not None:
            # 사용자가 순수익을 수정했고, 우선순위가 'profit'
            calculated_gain = calculate_market_gain_from_net_profit(
                user_edited_profit,
                current_capital_amount_for_step_start,
                recovery_leverage
            )
            market_gain_pct_this_step = calculated_gain if calculated_gain is not None else float('inf')
            is_user_edited_this_step = True
        elif user_edited_gain is not None: # 우선순위가 'gain'이거나, 순수익 수정이 없거나, 수익률 수정이 명시적일 때
            market_gain_pct_this_step = user_edited_gain
            is_user_edited_this_step = True
        else:
            # 자동 계산 로직 (이전 스텝까지의 결과로 현재 자본이 확정된 상태에서 다음 스텝 계산)
            if current_capital_amount_for_step_start <= 0:
                market_gain_pct_this_step = float('inf')
            else:
                remaining_steps_to_recover = trade_steps - n
                if target_final_capital <= 0 or current_capital_amount_for_step_start <= 0 or (target_final_capital / current_capital_amount_for_step_start) < 0:
                    required_total_asset_ratio_for_remaining = float('inf')
                else:
                    required_total_asset_ratio_for_remaining = target_final_capital / current_capital_amount_for_step_start
                
                if required_total_asset_ratio_for_remaining == float('inf'):
                    required_asset_ratio_this_step = float('inf')
                elif remaining_steps_to_recover <= 0:
                    required_asset_ratio_this_step = float('inf') if current_capital_amount_for_step_start < target_final_capital else 1.0
                else:
                    required_asset_ratio_this_step = required_total_asset_ratio_for_remaining ** (1 / remaining_steps_to_recover)

                if required_asset_ratio_this_step == float('inf'):
                    market_gain_pct_this_step = float('inf')
                elif recovery_leverage == 0:
                    market_gain_pct_this_step = float('inf') if required_asset_ratio_this_step > 1.00001 else 0.0
                else:
                    market_gain_pct_this_step = ((required_asset_ratio_this_step - 1.0 + trade_fee_ratio_on_position) / recovery_leverage) * 100.0
        
        final_market_gains_for_steps[n] = market_gain_pct_this_step # 확정된 수익률 저장

        # 확정된 market_gain_pct_this_step을 사용하여 자본 및 순수익 업데이트
        net_profit_this_step_amount: float
        current_capital_after_trade: float

        if market_gain_pct_this_step != float('inf'):
            gain_from_market_ratio = (market_gain_pct_this_step / 100.0) * recovery_leverage
            net_change_on_capital_ratio = gain_from_market_ratio - trade_fee_ratio_on_position
            
            net_profit_this_step_amount = current_capital_amount_for_step_start * net_change_on_capital_ratio
            current_capital_after_trade = current_capital_amount_for_step_start * (1.0 + net_change_on_capital_ratio)
            current_capital_after_trade = max(0, current_capital_after_trade)
        else:
            net_profit_this_step_amount = 0.0
            current_capital_after_trade = 0.0 if not is_user_edited_this_step else current_capital_amount_for_step_start # 사용자가 직접 입력한 경우 이전 자본 유지 또는 0 처리

        gain_display = f"{market_gain_pct_this_step:.2f}%" if market_gain_pct_this_step != float('inf') else '∞ (회복불가)'
        data_rows.append({
            COL_TRADE_ROUND: f"{n+1}회차",
            COL_MARKET_GAIN_PCT: gain_display, # 화면 표시용은 확정된 수익률
            COL_CUMULATIVE_CAPITAL_AMT: f"₩ {current_capital_after_trade:,.0f}",
            COL_NET_PROFIT_AMT: f"₩ {net_profit_this_step_amount:,.0f}",
        })
        
        current_capital_amount_for_step_start = current_capital_after_trade

    return pd.DataFrame(data_rows)