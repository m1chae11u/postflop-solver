import ctypes
import csv
import os
import platform
import json
from .solver_output_types import HeroDecisionOutput, OpponentDecisionOutput, ChanceNodeOutput, ActionEvaluation

def run_solver_from_rust(
    expected_node_type: str,
    oop_range_str,
    ip_range_str,
    flop_str,
    turn_card_opt_str,
    river_card_opt_str,
    initial_pot,
    eff_stack,
    use_compression_flag,
    max_iterations_val,
    target_exploit_percentage_val,
    should_print_progress,
):
    """
    Loads the Rust shared library and calls the FFI function.
    FOR NOW: This function simulates the FFI call and returns dummy Pydantic objects.
    Eventually, it will parse the JSON string returned by the actual FFI call.
    """
    lib_name = "postflop_solver_ffi"
    
    # Determine the correct library file extension and path
    if platform.system() == "Linux":
        lib_filename = f"lib{lib_name}.so"
    elif platform.system() == "Darwin": # macOS
        lib_filename = f"lib{lib_name}.dylib"
    elif platform.system() == "Windows":
        lib_filename = f"{lib_name}.dll"
    else:
        raise OSError(f"Unsupported OS: {platform.system()}")

    # Construct the path to the library, assuming the script is in 'dataset_generator'
    # and the library is in 'target/release' relative to the project root.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    lib_path_abs = os.path.join(project_root, "target", "release", lib_filename)


    if not os.path.exists(lib_path_abs):
        raise FileNotFoundError(
            f"Shared library not found at {lib_path_abs}. "
            f"Make sure you have compiled the Rust project using 'cargo build --release' "
            f"from the project root ('{project_root}')."
        )

    # Load the shared library
    solver_lib = ctypes.CDLL(lib_path_abs)

    # Define argument types for the FFI function
    solver_lib.run_solver_for_gamestate_ffi.argtypes = [
        ctypes.c_char_p,  # oop_range_c_str
        ctypes.c_char_p,  # ip_range_c_str
        ctypes.c_char_p,  # flop_c_str
        ctypes.c_char_p,  # turn_card_opt_c_str
        ctypes.c_char_p,  # river_card_opt_c_str
        ctypes.c_int,     # initial_pot
        ctypes.c_int,     # eff_stack
        ctypes.c_uint8,   # use_compression_flag_c (0 or 1)
        ctypes.c_uint,    # max_iterations_val
        ctypes.c_float,   # target_exploit_percentage_val
        ctypes.c_uint8,   # should_print_progress_c (0 or 1)
    ]
    # Define the return type - expecting a C string (JSON from Rust)
    solver_lib.run_solver_for_gamestate_ffi.restype = ctypes.c_char_p
    
    def to_c_char_p_or_null(s):
        return s.encode('utf-8') if s is not None and s != "" else None

    # --- START STUBBED FFI CALL AND DUMMY DATA GENERATION ---
    if should_print_progress:
        print(f"Python: Simulating FFI call for flop: {flop_str}, expected_node_type: {expected_node_type}")
        print(f"  Pot: {initial_pot}, Eff Stack: {eff_stack}")
        print(f"  OOP Range: {oop_range_str[:50]}..., IP Range: {ip_range_str[:50]}...")
        print(f"  Turn: {turn_card_opt_str}, River: {river_card_opt_str}")


    dummy_pydantic_object = None
    if expected_node_type == "hero_decision":
        actions = [
            ActionEvaluation(action_description="CHECK", ev_for_hero=0.05 * initial_pot, probability=0.6),
            ActionEvaluation(action_description=f"BET {max(1, round(initial_pot*0.5))}BB", ev_for_hero=0.15 * initial_pot, probability=0.4)
        ]
        # Add a FOLD option if not on the flop (i.e., if turn or river card is present, or implied by game state)
        # This is a simplified check; a real game state parser would be more robust.
        if turn_card_opt_str or river_card_opt_str or (flop_str and not turn_card_opt_str and not river_card_opt_str and "dealcards" in flop_str.lower()): # Crude check for later streets
             actions.append(ActionEvaluation(action_description="FOLD", ev_for_hero=0.0, probability=0.0)) # Placeholder probability
        dummy_pydantic_object = HeroDecisionOutput(possible_actions=actions)
    elif expected_node_type == "opponent_decision":
        # Example: Opponent responding to a previous Hero bet
        dummy_pydantic_object = OpponentDecisionOutput(possible_actions=[
            ActionEvaluation(action_description="FOLD", ev_for_hero=float(initial_pot), probability=0.4), # Hero wins current pot
            ActionEvaluation(action_description="CALL", ev_for_hero=0.1 * initial_pot, probability=0.5),
            ActionEvaluation(action_description=f"RAISE {max(1,round(initial_pot*1.5))}BB", ev_for_hero=-0.2 * initial_pot, probability=0.1)
        ])
    elif expected_node_type == "chance_node":
        dummy_pydantic_object = ChanceNodeOutput(abstracted_outcomes=[
            ActionEvaluation(action_description="FLUSH_CARD_COMPLETES_DRAW", ev_for_hero=-0.3 * initial_pot, probability=0.15),
            ActionEvaluation(action_description="STRAIGHT_CARD_COMPLETES_DRAW", ev_for_hero=-0.25 * initial_pot, probability=0.10),
            ActionEvaluation(action_description="BOARD_PAIRS", ev_for_hero=0.01 * initial_pot, probability=0.20),
            ActionEvaluation(action_description="BLANK_CARD_NO_DRAW_IMPACT", ev_for_hero=0.05 * initial_pot, probability=0.55)
        ])
    else:
        # In a real scenario, we might return None or raise an error.
        # For now, to allow pipeline development, let's return a default HeroDecision.
        print(f"Warning: Unknown expected_node_type: {expected_node_type}. Returning default dummy HeroDecisionOutput.")
        dummy_pydantic_object = HeroDecisionOutput(possible_actions=[
            ActionEvaluation(action_description="DEFAULT_CHECK", ev_for_hero=0.0)
        ])

    # The actual FFI call is currently stubbed.
    # When enabled, the Rust FFI function would be called here.
    # It would need to accept parameters defining the game state and the type of evaluation requested.
    # e.g., rust_json_output_bytes = solver_lib.run_solver_for_gamestate_ffi(
    #     # ... arguments ...
    # )
    #
    # If the Rust side returns a JSON string:
    # rust_json_output_str = rust_json_output_bytes.decode('utf-8')
    # parsed_json = json.loads(rust_json_output_str)
    #
    # Then, based on expected_node_type or a type field in the JSON,
    # you would parse into the Pydantic model:
    # if expected_node_type == "hero_decision":
    #     dummy_pydantic_object = HeroDecisionOutput(**parsed_json)
    # elif expected_node_type == "opponent_decision":
    #     dummy_pydantic_object = OpponentDecisionOutput(**parsed_json)
    # elif expected_node_type == "chance_node":
    #     dummy_pydantic_object = ChanceNodeOutput(**parsed_json)
    
    if should_print_progress:
        print(f"Python: Rust solver FFI was 'called'. Returning dummy Pydantic object.")
    
    return dummy_pydantic_object # Return the Pydantic model instance directly
    # --- END STUBBED FFI CALL AND DUMMY DATA GENERATION ---


def main():
    # Assuming the CSV is in the same directory as this script
    csv_file_path = os.path.join(os.path.dirname(__file__), 'gamestates.csv')

    if not os.path.exists(csv_file_path):
        print(f"'{csv_file_path}' not found. Creating a dummy CSV for demonstration.")
        with open(csv_file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "oop_range", "ip_range", "flop", "turn", "river",
                "initial_pot", "eff_stack", "compress", "max_iter", "exploit_pct", "print_progress"
            ])
            writer.writerow([
                "66+,A8s+,A5s-A4s,AJo+,K9s+,KQo,QTs+,JTs,96s+,85s+,75s+,65s,54s",
                "QQ-22,AQs-A2s,ATo+,K5s+,KJo+,Q8s+,J8s+,T7s+,96s+,86s+,75s+,64s+,53s+",
                "Td9d6h", "Qc", "", 
                200, 900, False, 10000, 0.01, True 
            ])
            writer.writerow([
                "AA,KK,QQ,AKs,AKo", "JJ,TT,AQs,AQo", "2h7dKh", "Ts", "Js",
                150, 1000, True, 20, 0.005, True
            ])

    with open(csv_file_path, mode='r', newline='') as file:
        reader = csv.DictReader(file)
        for i, row in enumerate(reader):
            print(f"--- Processing gamestate {i+1} from CSV ({row['flop']}) ---")
            try:
                turn_card = row['turn'] if row['turn'] and row['turn'].strip() else None
                river_card = row['river'] if row['river'] and row['river'].strip() else None
                
                # Ensure boolean and numeric types are correctly converted
                compress_flag = str(row['compress']).lower() == 'true'
                print_progress_flag = str(row['print_progress']).lower() == 'true'
                
                # Determine expected_node_type based on CSV or other logic.
                # For this example, we'll default to "hero_decision" as the CSV rows
                # often imply a point where Hero needs to make a decision.
                # In a more complex setup, this could be derived from 'evaluation_at' or 'postflop_action' fields.
                current_expected_node_type = "hero_decision" 
                
                solver_output_data = run_solver_from_rust(
                    expected_node_type=current_expected_node_type,
                    oop_range_str=row['oop_range'],
                    ip_range_str=row['ip_range'],
                    flop_str=row['flop'],
                    turn_card_opt_str=turn_card,
                    river_card_opt_str=river_card,
                    initial_pot=int(row['initial_pot']),
                    eff_stack=int(row['eff_stack']),
                    use_compression_flag=compress_flag,
                    max_iterations_val=int(row['max_iter']),
                    target_exploit_percentage_val=float(row['exploit_pct']),
                    should_print_progress=print_progress_flag,
                )

                if solver_output_data:
                    print(f"Solver Output for {row['flop']} (Type: {solver_output_data.node_type}):")
                    # Pretty print the Pydantic model as JSON
                    print(solver_output_data.model_dump_json(indent=2))
                else:
                    # This case should ideally not be hit if dummy_pydantic_object always gets a default
                    print(f"No solver output received for {row['flop']}.")

            except Exception as e:
                print(f"Error processing row {i+1} ({row.get('flop', 'N/A')}): {row}")
                print(f"Exception: {e}")
                import traceback
                traceback.print_exc()
            print(f"--- Finished gamestate {i+1} ({row['flop']}) ---\n")

if __name__ == "__main__":
    main()
