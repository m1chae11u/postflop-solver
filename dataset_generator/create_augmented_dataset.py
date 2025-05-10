import csv
import os
import random # Still needed for range_generator's random choices
from typing import List, Dict, Any, Tuple, Union

# Assuming range_generator.py is in the same directory (dataset_generator)
from .range_generator import (
    augment_gamestate_with_ranges,
    holding_to_hand_str,
    # We don't directly need holding_to_hand_str here as augment_gamestate_with_ranges uses it,
    # but good to be aware of it. We need to prepare the holding for it.
)

OUTPUT_DIR = os.path.dirname(__file__) # Ensures output is in dataset_generator

def parse_holding_from_str(holding_str: str) -> List[str]:
    """
    Parses a 4-character holding string (e.g., "AhKd") into a list of two cards (e.g., ["Ah", "Kd"]).
    Args:
        holding_str: A string like "AhKd".

    Returns:
        A list of two card strings, e.g., ["Ah", "Kd"].
        Raises ValueError if the string is not 4 characters long.
    """
    if not isinstance(holding_str, str) or len(holding_str) != 4:
        raise ValueError(f"Invalid holding string format: {holding_str}. Expected 4 characters, e.g., 'AhKd'.")
    return [holding_str[0:2], holding_str[2:4]]

def process_input_csv(input_csv_path, output_csv_path, num_rows_to_process=None):
    """
    Reads the input CSV, augments gamestates with ranges, and writes to output CSV.
    """
    print(f"Starting CSV processing...")
    print(f"Input file: {input_csv_path}")
    print(f"Output file: {output_csv_path}")
    if num_rows_to_process is not None:
        print(f"Processing a sample of {num_rows_to_process} rows.")

    processed_rows = []
    fieldnames = []

    try:
        with open(input_csv_path, mode='r', newline='', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames + ['oop_range_str', 'oop_range_type_selected', 'ip_range_str', 'ip_range_type_selected', 'hero_hand_parsed_str']
            
            for i, row in enumerate(reader):
                if num_rows_to_process is not None and i >= num_rows_to_process:
                    print(f"Reached processing limit of {num_rows_to_process} rows.")
                    break
                
                # print(f"Processing row {i+1}: {row.get('id', '')}")
                gamestate_data = dict(row) # Make a mutable copy

                # 1. Determine hero_is_oop from 'hero_position'
                hero_pos_str = gamestate_data.get('hero_position')
                if hero_pos_str == 'OOP':
                    gamestate_data['_hero_is_oop_internal'] = True
                elif hero_pos_str == 'IP':
                    gamestate_data['_hero_is_oop_internal'] = False
                else:
                    print(f"Warning: Row {i+1}: Unknown or missing 'hero_position': '{hero_pos_str}'. Skipping row.")
                    continue

                # 2. Prepare hero_holding for augment_gamestate_with_ranges
                holding_str_from_csv = gamestate_data.get('holding')
                parsed_holding_for_func = parse_holding_from_str(holding_str_from_csv)
                if not parsed_holding_for_func:
                    print(f"Warning: Row {i+1}: Could not parse 'holding': '{holding_str_from_csv}'. Skipping row.")
                    continue
                gamestate_data['_hero_holding_internal'] = parsed_holding_for_func

                try:
                    augmented_row_dict = augment_gamestate_with_ranges(
                        gamestate_data,
                        hero_is_oop_field='_hero_is_oop_internal',
                        hero_holding_field='_hero_holding_internal'
                    )
                    # Remove temporary internal fields if they are not meant to be in output
                    del augmented_row_dict['_hero_is_oop_internal']
                    del augmented_row_dict['_hero_holding_internal']
                    processed_rows.append(augmented_row_dict)
                except Exception as e_augment:
                    print(f"Error augmenting row {i+1} (Original data: {row}): {e_augment}")
                    import traceback
                    traceback.print_exc() # Print full traceback for augmentation error
                    # Optionally add original row or row with error flag to output

    except FileNotFoundError:
        print(f"Error: Input CSV file not found at {input_csv_path}")
        return
    except Exception as e_read:
        print(f"An error occurred while reading '{input_csv_path}': {e_read}")
        import traceback
        traceback.print_exc()
        return

    if not processed_rows:
        print("No rows were processed. Output file will not be created.")
        return

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)

    try:
        with open(output_csv_path, mode='w', newline='', encoding='utf-8') as outfile:
            # Filter fieldnames to only include those present in the first processed row 
            # (in case some rows were skipped or had issues, ensuring all columns are valid)
            # Or, more robustly, ensure all expected fieldnames (original + new) are written.
            # Using the fieldnames list built from the reader and new additions is safer.
            writer = csv.DictWriter(outfile, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(processed_rows)
        print(f"Successfully processed {len(processed_rows)} rows.")
        print(f"Augmented data saved to: {output_csv_path}")
    except Exception as e_write:
        print(f"An error occurred while writing to '{output_csv_path}': {e_write}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # Determine project root path assuming this script is in dataset_generator
    # and dataset_generator is in the project root.
    # This way of pathing is fragile. A more robust way is to use absolute paths
    # or have a clear environment variable for project root.
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) 
    
    # Path to the full dataset (relative from project_root)
    full_input_csv = os.path.join(PROJECT_ROOT, 'datasets', 'postflop_500k_train_set_game_scenario_information.csv')
    
    # Output path for the small sample test (in dataset_generator directory)
    sample_output_csv = os.path.join(OUTPUT_DIR, 'augmented_sample_output.csv')

    # Output path for the full processed dataset (also in dataset_generator for now)
    # full_output_csv = os.path.join(OUTPUT_DIR, 'augmented_full_dataset.csv')

    print(f"Project Root (estimated): {PROJECT_ROOT}")
    print(f"Full input CSV path: {full_input_csv}")
    print(f"Sample output CSV path: {sample_output_csv}")

    # --- Process a small sample for testing ---
    # This uses the first few rows of your actual large CSV.
    process_input_csv(
        input_csv_path=full_input_csv,
        output_csv_path=sample_output_csv,
        num_rows_to_process=5 
    )

    # --- To process the full dataset ( uncomment after testing with sample) ---
    # print("\n--- Processing Full Dataset (this might take a while) ---")
    # process_input_csv(
    #     input_csv_path=full_input_csv,
    #     output_csv_path=full_output_csv
    # ) 