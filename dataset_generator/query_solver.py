import ctypes
import csv
import os
import platform

def run_solver_from_rust(
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
    Loads the Rust shared library and calls the run_solver_for_gamestate_ffi function.
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
    # Define the return type (void in this case)
    solver_lib.run_solver_for_gamestate_ffi.restype = None
    
    def to_c_char_p_or_null(s):
        return s.encode('utf-8') if s is not None and s != "" else None

    # Call the Rust function
    solver_lib.run_solver_for_gamestate_ffi(
        oop_range_str.encode('utf-8'),
        ip_range_str.encode('utf-8'),
        flop_str.encode('utf-8'),
        to_c_char_p_or_null(turn_card_opt_str),
        to_c_char_p_or_null(river_card_opt_str),
        ctypes.c_int(initial_pot),
        ctypes.c_int(eff_stack),
        ctypes.c_uint8(1 if use_compression_flag else 0),
        ctypes.c_uint(max_iterations_val),
        ctypes.c_float(target_exploit_percentage_val),
        ctypes.c_uint8(1 if should_print_progress else 0),
    )
    if should_print_progress: # Only print this if Rust is also printing
        print(f"Python: Rust solver FFI function called for flop: {flop_str}")


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
                200, 900, False, 10, 0.01, True 
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
                
                run_solver_from_rust(
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
            except Exception as e:
                print(f"Error processing row {i+1} ({row.get('flop', 'N/A')}): {row}")
                print(f"Exception: {e}")
                import traceback
                traceback.print_exc()
            print(f"--- Finished gamestate {i+1} ({row['flop']}) ---\n")

if __name__ == "__main__":
    main()
