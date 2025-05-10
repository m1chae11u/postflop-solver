import csv
import os
from dataset_generator.query_solver import run_solver_from_rust
from dataset_generator.trace_formatter import format_internal_search_trace

# Placeholder for the input CSV file path. 
# !!! YOU WILL NEED TO CHANGE THIS TO THE ACTUAL PATH OF YOUR CSV FILE !!!
DEFAULT_INPUT_CSV_PATH = "./input_poker_data.csv" # Example path

def process_gamestate_row(row_data: dict):
    """Parses a row from the CSV, gets solver data, and formats the trace."""
    try:
        oop_range_str = row_data.get('oop_range_str', "")
        ip_range_str = row_data.get('ip_range_str', "")
        flop_str = row_data.get('board_flop', "")
        
        turn_card = row_data.get('board_turn')
        turn_card_opt_str = turn_card if turn_card and turn_card.strip() else None
        
        river_card = row_data.get('board_river')
        river_card_opt_str = river_card if river_card and river_card.strip() else None
        
        initial_pot = int(row_data.get('pot_size', 0))

        # Parameters not in the provided CSV snippet - using defaults/placeholders
        # These might need to be read from the CSV or configured if they become important
        # for the Rust solver's evaluation logic beyond just running a simulation.
        eff_stack = int(row_data.get('eff_stack', 100)) # Placeholder if not in CSV
        use_compression_flag = str(row_data.get('compress', 'false')).lower() == 'true' # Placeholder
        max_iterations_val = int(row_data.get('max_iter', 10000)) # Placeholder
        target_exploit_percentage_val = float(row_data.get('exploit_pct', 0.01)) # Placeholder
        should_print_progress = str(row_data.get('print_progress', 'false')).lower() == 'true' # Changed default to false for cleaner trace output

        # For now, assuming all rows from this CSV are for Hero's decision point
        expected_node_type = "hero_decision"

        solver_output_model = run_solver_from_rust(
            expected_node_type=expected_node_type,
            oop_range_str=oop_range_str,
            ip_range_str=ip_range_str,
            flop_str=flop_str,
            turn_card_opt_str=turn_card_opt_str,
            river_card_opt_str=river_card_opt_str,
            initial_pot=initial_pot,
            eff_stack=eff_stack, 
            use_compression_flag=use_compression_flag,
            max_iterations_val=max_iterations_val,
            target_exploit_percentage_val=target_exploit_percentage_val,
            should_print_progress=should_print_progress,
        )
        
        if not solver_output_model:
            print(f"Warning: No solver output model received for row: {row_data.get('board_flop', 'N/A')}")
            return None

        # Now, format this solver output model into the trace string
        trace_string = format_internal_search_trace(
            solver_data_model=solver_output_model,
            csv_row=row_data,
            eff_stack=eff_stack
        )
        return trace_string

    except Exception as e:
        print(f"Error processing row: {row_data.get('board_flop', 'N/A')}")
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        return None

def main_create_trace_data(input_csv_path: str):
    """
    Main function to read the CSV, process each row, and generate solver output traces.
    """
    if not os.path.exists(input_csv_path):
        print(f"Error: Input CSV file not found at {input_csv_path}")
        print("Please update the DEFAULT_INPUT_CSV_PATH variable in the script or provide a valid path.")
        # Create a dummy CSV if the specified one is the default and not found, for demonstration
        if input_csv_path == DEFAULT_INPUT_CSV_PATH:
            print(f"Creating a dummy '{DEFAULT_INPUT_CSV_PATH}' for demonstration.")
            with open(DEFAULT_INPUT_CSV_PATH, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "preflop_action","board_flop","board_turn","board_river","aggressor_position",
                    "postflop_action","evaluation_at","available_moves","pot_size","hero_position",
                    "holding","correct_decision","oop_range_str","oop_range_type_selected",
                    "ip_range_str","ip_range_type_selected", "eff_stack", "compress", "max_iter", "exploit_pct", "print_progress"
                ])
                writer.writerow([
                    "HJ/2.0bb/BB/call","JcJh4s","4d","As","OOP",
                    "OOP_CHECK/IP_BET_1/OOP_CALL/dealcards/4d/OOP_CHECK/IP_BET_8/OOP_CALL/dealcards/As/OOP_CHECK",
                    "River","['Check', 'Bet 17']","21","IP","AhKd","Check", # pot_size as string, matching DictReader output
                    "AA,AKo,AKs,AQo,AQs,AJo,AJs,ATo,A3s,KK,KQo,K9o,QQ,JJ,J4o,TT,99,77",
                    "Balanced",
                    "AA,AKo,AKs,AQo,AQs,AJo,AJs,ATo,ATs,A9o,A8o,A8s,A7o,A7s,A6o,A6s,A5o,A5s,A4o,A4s,A3o,A3s,A2o,A2s,KK,KQo,KQs,KJo,KJs,KTo,KTs,K9o,K9s,K8o,K8s,K7o,K6s,K5s,QQ,QJo,QJs,QTo,QTs,Q9o,Q9s,Q7o,Q7s,JTo,J9o,J9s,J8s,J7s,TT,T9o,T9s,T8o,T8s,T7s,T6o,99,97s,96s,88,87s,86s,83s,77,76s,75s,73s,72s,66,65s,64s,54s,44,33",
                    "Loose", "100", "False", "10000", "0.01", "False" # eff_stack and others as strings
                ])
        return

    processed_row_count = 0
    with open(input_csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for i, row in enumerate(reader):
            print(f"--- Processing row {i+1} from CSV (Flop: {row.get('board_flop', 'N/A')}) ---")
            # Pass the raw row (dict of strings) to process_gamestate_row
            trace_output_string = process_gamestate_row(row) 
            if trace_output_string:
                print("Generated Internal Search Trace:")
                print(trace_output_string)
                processed_row_count += 1
            else:
                print(f"Skipping row {i+1} due to processing error or no solver output.")
            print(f"--- Finished row {i+1} ---\n")
            
            # Limiter for testing - remove for full run
            # if processed_row_count >= 3:
            #     print("Reached test limit of 3 processed rows.")
            #     break 

    print(f"Finished processing. Total rows successfully processed: {processed_row_count}")

if __name__ == "__main__":
    # You can change this to directly pass a file path if needed, e.g.:
    # import sys
    # csv_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT_CSV_PATH
    csv_path = DEFAULT_INPUT_CSV_PATH
    main_create_trace_data(csv_path) 