from typing import Union, Optional, List, Dict, Any
from .solver_output_types import HeroDecisionOutput, OpponentDecisionOutput, ChanceNodeOutput, ActionEvaluation

def get_current_street(evaluation_at: Optional[str], flop: Optional[str], turn: Optional[str], river: Optional[str]) -> str:
    """Determines the current street based on evaluation_at or board cards."""
    if evaluation_at:
        street_val = evaluation_at.strip().capitalize()
        if street_val in ["Flop", "Turn", "River"]:
            return street_val
    
    # Fallback if evaluation_at is not definitive
    if river and river.strip():
        return "River"
    if turn and turn.strip():
        return "Turn"
    if flop and flop.strip():
        return "Flop"
    return "Preflop" # Should ideally not happen if we are postflop

def format_board_cards(flop: Optional[str], turn: Optional[str], river: Optional[str]) -> str:
    """Formats board cards into a single string."""
    cards = []
    if flop and flop.strip():
        cards.append(flop.strip())
    if turn and turn.strip():
        cards.append(turn.strip())
    if river and river.strip():
        cards.append(river.strip())
    return "".join(cards) # Example: "JcJh4s4dAs"

def format_history(preflop_action: Optional[str], postflop_action: Optional[str], evaluation_at: str) -> str:
    """Constructs a history string up to the point of evaluation."""
    history_parts = []
    if preflop_action and preflop_action.strip():
        history_parts.append(f"PREFLOP:{preflop_action.strip()}")
    
    if postflop_action and postflop_action.strip():
        # The postflop_action string often contains the full sequence.
        # We need to truncate it at the point of the current 'evaluation_at' street.
        # This is a simplified approach; a more robust parser might be needed for complex action strings.
        # Example: "OOP_CHECK/IP_BET_1/OOP_CALL/dealcards/4d/OOP_CHECK/IP_BET_8/OOP_CALL/dealcards/As/OOP_CHECK"
        # If evaluation_at is River, we want most of this. If Turn, we want up to before "dealcards/As".
        
        actions = postflop_action.strip()
        # Simplified: if evaluating on the flop, we probably don't take much from postflop_action for *prior* history
        # unless postflop_action is *only* flop actions for this decision.
        # For Turn, we take actions up to the dealing of the turn card.
        # For River, we take actions up to the dealing of the river card.

        # This is a heuristic and might need refinement based on exact postflop_action structure.
        history_to_append = actions # Default to full if not easily splittable or if it represents current street decision context

        # Attempt to truncate postflop_action for history
        # This simplified logic assumes dealcards always precedes the street card and new actions for that street.
        # More complex logic might be needed if `postflop_action` represents the options AT the evaluation point rather than leading up to it.
        current_history_segment = ""
        if evaluation_at == "River":
            # Include flop and turn actions if present
            parts = actions.split("dealcards/")
            if len(parts) > 2 : # Flop actions, turn card + turn actions, river card + river actions
                current_history_segment = f"FLOP:{parts[0].strip('/')}DEAL_TURN:{parts[1].split('/')[0].strip()}TURN:{('/'.join(parts[1].split('/')[1:])).strip('/')}DEAL_RIVER:{parts[2].split('/')[0].strip()}"
            elif len(parts) > 1:
                current_history_segment = f"FLOP:{parts[0].strip('/')}DEAL_TURN:{parts[1].split('/')[0].strip()}"
            else:
                 current_history_segment = f"FLOP:{actions.strip('/')}" # Only flop actions

        elif evaluation_at == "Turn":
            parts = actions.split("dealcards/")
            if len(parts) > 1:
                current_history_segment = f"FLOP:{parts[0].strip('/')}DEAL_TURN:{parts[1].split('/')[0].strip()}"
            else:
                current_history_segment = f"FLOP:{actions.strip('/')}" # Only flop actions
        elif evaluation_at == "Flop":
             current_history_segment = f"FLOP:{actions.strip('/')}" # Assumes actions are for current flop decision or leading to it

        if current_history_segment:
            history_parts.append(current_history_segment)
            
    return "|".join(history_parts) # Using pipe as a separator, methodology used comma and space

def format_internal_search_trace(
    solver_data_model: Union[HeroDecisionOutput, OpponentDecisionOutput, ChanceNodeOutput],
    csv_row: Dict[str, Any],
    eff_stack: int # Effective stack, assumed to be same for both hero and opponent for now
) -> str:
    """Formats the solver output and CSV data into an internal search trace string."""
    trace_lines = []

    # 1. Game Context
    hero_pos_str = csv_row.get('hero_position', 'IP').strip().upper()
    opponent_pos_str = "OOP" if hero_pos_str == "IP" else "IP"
    pot_size_bb = float(csv_row.get('pot_size', 0)) # Assuming pot_size is in BB or a unit convertible to BB for display
    
    board_flop = csv_row.get('board_flop')
    board_turn = csv_row.get('board_turn')
    board_river = csv_row.get('board_river')
    evaluation_at_str = csv_row.get('evaluation_at')
    current_street = get_current_street(evaluation_at_str, board_flop, board_turn, board_river)

    game_history = format_history(
        csv_row.get('preflop_action'), 
        csv_row.get('postflop_action'),
        current_street
    )

    trace_lines.append(
        f'<GameContext stack_hero="{eff_stack}bb" stack_opponent="{eff_stack}bb" ' \
        f'hero_pos="{hero_pos_str}" opponent_pos="{opponent_pos_str}" pot="{pot_size_bb}bb" history="{game_history}">'
    )

    # 2. Hero Hand
    hero_holding = csv_row.get('holding', '').strip()
    trace_lines.append(f'  <HeroHand cards="{hero_holding}" />')

    # 3. Board
    full_board_str = format_board_cards(board_flop, board_turn, board_river)
    trace_lines.append(f'  <Board cards="{full_board_str}" />')
    trace_lines.append("") # Blank line for readability like in example

    # 4. Decision Node (Currently only handling HeroDecisionOutput)
    if isinstance(solver_data_model, HeroDecisionOutput):
        trace_lines.append(f'  <Hero{current_street}Decision>')
        for action_eval in solver_data_model.possible_actions:
            ev_str = f'{action_eval.ev_for_hero:+.2f}bb' # Format EV to two decimal places with sign
            # Probability might not be present for initial hero EV estimates in the methodology example
            # prob_str = f' probability="{action_eval.probability}"' if action_eval.probability is not None else ""
            trace_lines.append(
                f'    <ProposeAction action="{action_eval.action_description}" immediate_ev="{ev_str}" />'
            )
        trace_lines.append(f'  </Hero{current_street}Decision>')
    
    # Future: Handle OpponentDecisionOutput and ChanceNodeOutput for deeper traces
    # Future: Handle <ExpandHeroAction>, <StateAfter...>, etc. for deeper traces

    trace_lines.append("</GameContext>")
    return "\n".join(trace_lines)


# Example Usage (for testing this module independently):
if __name__ == '__main__':
    # Sample CSV row data (mimicking what create_internal_search_data.py would provide)
    sample_csv_row = {
        'preflop_action': "HJ/2.0bb/BB/call",
        'board_flop': "JcJh4s",
        'board_turn': "4d",
        'board_river': "As",
        'aggressor_position': "OOP",
        'postflop_action': "OOP_CHECK/IP_BET_1/OOP_CALL/dealcards/4d/OOP_CHECK/IP_BET_8/OOP_CALL/dealcards/As/OOP_CHECK",
        'evaluation_at': "River",
        'available_moves': "['Check', 'Bet 17']",
        'pot_size': 21,
        'hero_position': "IP",
        'holding': "AhKd",
        'correct_decision': "Check",
        # 'eff_stack' would typically be passed separately or be in the row
    }
    sample_eff_stack = 100

    # Sample Solver Output (HeroDecisionOutput)
    sample_solver_output = HeroDecisionOutput(
        possible_actions=[
            ActionEvaluation(action_description="Check", ev_for_hero=2.5, probability=0.6),
            ActionEvaluation(action_description="Bet 17bb", ev_for_hero=-1.5, probability=0.4)
        ]
    )

    formatted_trace = format_internal_search_trace(sample_solver_output, sample_csv_row, sample_eff_stack)
    print("--- Sample Formatted Trace ---")
    print(formatted_trace)
    print("-----------------------------")

    sample_csv_row_flop = {
        'preflop_action': "BTN_RAISE_2.5BB,SB_CALL,BB_FOLD",
        'board_flop': "Ah8c7d",
        'board_turn': None,
        'board_river': None,
        'postflop_action': "SB_CHECK", # Action leading to Hero's decision on flop
        'evaluation_at': "Flop",
        'pot_size': 5.5,
        'hero_position': "BTN",
        'holding': "AsKd",
    }
    sample_solver_output_flop = HeroDecisionOutput(
        possible_actions=[
            ActionEvaluation(action_description="check", ev_for_hero=0.2),
            ActionEvaluation(action_description="bet_3bb", ev_for_hero=0.8)
        ]
    )
    formatted_trace_flop = format_internal_search_trace(sample_solver_output_flop, sample_csv_row_flop, 97.5)
    print("--- Sample Formatted Trace (Flop) ---")
    print(formatted_trace_flop)
    print("----------------------------------") 