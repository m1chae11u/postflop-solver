use postflop_solver::*;
use std::os::raw::{c_char, c_int, c_float, c_uint};
use std::ffi::{CStr, CString};

// Function to run the solver with configurable game state
fn run_solver_for_gamestate(
    oop_range_str: &str,
    ip_range_str: &str,
    flop_str: &str,
    turn_card_opt_str: Option<&str>,
    river_card_opt_str: Option<&str>,
    initial_pot: i32,
    eff_stack: i32,
    bet_options_tuple: (&str, &str),
    use_compression_flag: bool,
    max_iterations_val: u32,
    target_exploit_percentage_val: f32,
    should_print_progress: bool,
) {
    // 1. Configure the Game
    // ----------------------
    let oop_range_parsed = oop_range_str.parse().expect("Failed to parse OOP range");
    let ip_range_parsed = ip_range_str.parse().expect("Failed to parse IP range");

    let flop_cards = flop_from_str(flop_str).expect("Failed to parse flop string");
    
    let turn_card_val = turn_card_opt_str.map_or(NOT_DEALT, |s| {
        if s.trim().is_empty() { NOT_DEALT } else { card_from_str(s).expect("Failed to parse turn card string") }
    });
    
    let river_card_val = river_card_opt_str.map_or(NOT_DEALT, |s| {
        if s.trim().is_empty() { NOT_DEALT } else { card_from_str(s).expect("Failed to parse river card string") }
    });

    let card_config = CardConfig {
        range: [oop_range_parsed, ip_range_parsed],
        flop: flop_cards,
        turn: turn_card_val,
        river: river_card_val,
    };

    let determined_initial_board_state = if river_card_val != NOT_DEALT {
        BoardState::River
    } else if turn_card_val != NOT_DEALT {
        BoardState::Turn
    } else {
        BoardState::Flop
    };

    let bet_sizes = BetSizeOptions::try_from(bet_options_tuple).expect("Failed to parse bet sizes");

    let tree_config = TreeConfig {
        initial_state: determined_initial_board_state,
        starting_pot: initial_pot,
        effective_stack: eff_stack,
        flop_bet_sizes: [bet_sizes.clone(), bet_sizes.clone()],
        turn_bet_sizes: [bet_sizes.clone(), bet_sizes.clone()],
        river_bet_sizes: [bet_sizes.clone(), bet_sizes.clone()],
        ..Default::default()
    };

    let action_tree = ActionTree::new(tree_config.clone()).unwrap();
    let mut game = PostFlopGame::with_config(card_config, action_tree).unwrap();

    let num_board_cards = game.current_board().len();
    let current_board_state_print = match num_board_cards {
        3 => BoardState::Flop,
        4 => BoardState::Turn,
        5 => BoardState::River,
        _ => panic!("Unexpected number of board cards: {}", num_board_cards),
    };
    println!("Game configured. Initial state: {:?}, Current player: {:?}", current_board_state_print, game.current_player());
    println!("OOP private cards: {:?}", holes_to_strings(game.private_cards(0)).unwrap_or_default().len());
    println!("IP private cards: {:?}", holes_to_strings(game.private_cards(1)).unwrap_or_default().len());

    // 2. Allocate Memory
    // -------------------
    game.allocate_memory(use_compression_flag);
    println!("Memory allocated (compression: {}).", use_compression_flag);

    // 3. Run the Solver
    // -----------------
    let target_exploitability = initial_pot as f32 * target_exploit_percentage_val;
    
    println!("Starting solver for {} iterations or target exploitability {:.2}...", max_iterations_val, target_exploitability);
    let exploitability = solve(&mut game, max_iterations_val, target_exploitability, should_print_progress);
    println!("Solver finished. Final Exploitability: {:.4e} (target was {:.4e})", exploitability, target_exploitability);

    // 4. Get and Print Solver Output (for the current node, typically the root after solve)
    // -------------------------------------------------------------------------------------
    let actions = game.available_actions();
    let strategy_values = game.strategy();

    println!("\n--- Strategy at Current Node ---");
    println!("Available Actions: {:?}", actions);

    let current_player_idx = game.current_player();
    println!("Current player to act: {}", if current_player_idx == 0 { "OOP" } else { "IP" });

    let player_hands = game.private_cards(current_player_idx);
    let player_hands_str = holes_to_strings(player_hands).unwrap_or_default();

    if !actions.is_empty() && !strategy_values.is_empty() {
        for (hand_idx, hand_str) in player_hands_str.iter().take(10).enumerate() {
            print!("Hand {}: ", hand_str);
            for (action_idx, action) in actions.iter().enumerate() {
                let strat_flat_idx = action_idx * player_hands.len() + hand_idx;
                if strat_flat_idx < strategy_values.len() {
                    print!("{:?}: {:.3}, ", action, strategy_values[strat_flat_idx]);
                }
            }
            println!();
        }
        if player_hands_str.len() > 10 { println!("... (strategy for more hands not shown for brevity)"); }
    } else {
        println!("No actions available or strategy is empty at the current node.");
    }

    game.back_to_root(); 
    game.cache_normalized_weights(); 
    println!("\n--- Expected Values (EV) for OOP (Player 0) at the root ---");
    let oop_ev = game.expected_values(0);
    let oop_hands_for_ev = game.private_cards(0);
    let oop_hands_str_for_ev = holes_to_strings(oop_hands_for_ev).unwrap_or_default();
    for (i, hand_str) in oop_hands_str_for_ev.iter().take(10).enumerate() {
        if i < oop_ev.len() {
            println!("Hand {}: EV {:.3}", hand_str, oop_ev[i]);
        }
    }
    if oop_hands_str_for_ev.len() > 10 { println!("... (EV for more hands not shown for brevity)"); }

    println!("\n--- Equity for OOP (Player 0) at the root ---");
    let oop_equity = game.equity(0);
    for (i, hand_str) in oop_hands_str_for_ev.iter().take(10).enumerate() {
        if i < oop_equity.len() {
            println!("Hand {}: Equity {:.1}%", hand_str, oop_equity[i] * 100.0);
        }
    }
    if oop_hands_str_for_ev.len() > 10 { println!("... (Equity for more hands not shown for brevity)"); }
    
    let oop_weights = game.normalized_weights(0);
    if !oop_ev.is_empty() && !oop_weights.is_empty() && oop_ev.len() == oop_weights.len() {
        let average_ev_oop = compute_average(&oop_ev, oop_weights); // Assuming compute_average is available
        println!("Average EV for OOP: {:.3}", average_ev_oop);
    } else {
        println!("Could not compute average EV for OOP (empty data or mismatched lengths).");
    }
    if !oop_equity.is_empty() && !oop_weights.is_empty() && oop_equity.len() == oop_weights.len() {
        let average_equity_oop = compute_average(&oop_equity, oop_weights); // Assuming compute_average is available
        println!("Average Equity for OOP: {:.1}%", average_equity_oop * 100.0);
    } else {
        println!("Could not compute average Equity for OOP (empty data or mismatched lengths).");
    }

    // 5. Further Interaction (Example) - Commented out as in original, can be enabled if needed
    // game.back_to_root(); 
    // if !game.available_actions().is_empty() {
    //     println!("\nPlaying first available action at root: {:?}", game.available_actions()[0]);
    //     game.play(0); 
    //     println!("New current player: {}", if game.current_player() == 0 { "OOP" } else { "IP" });
    //     println!("Available actions now: {:?}", game.available_actions());
    // }

    println!("\n--- Solver Run Finished ---");
}

fn main() {
    // Original example values:
    let oop_range = "66+,A8s+,A5s-A4s,AJo+,K9s+,KQo,QTs+,JTs,96s+,85s+,75s+,65s,54s";
    let ip_range = "QQ-22,AQs-A2s,ATo+,K5s+,KJo+,Q8s+,J8s+,T7s+,96s+,86s+,75s+,64s+,53s+";
    let flop = "Td9d6h";
    let turn = Some("Qc");
    let river = None; // River is not dealt yet in the original example
    
    let initial_pot_val: i32 = 200;
    let effective_stack_val: i32 = 900;
    let bet_sizes_tuple = ("60%,e,a", "2.5x");

    let use_compression_val = false;
    let max_num_iterations_val = 100; // Lower for a quick test, increase for more accuracy
    let target_exploitability_percentage_val = 0.01; // e.g., 1% of the pot
    let print_progress_val = true;

    run_solver_for_gamestate(
        oop_range,
        ip_range,
        flop,
        turn,
        river,
        initial_pot_val,
        effective_stack_val,
        bet_sizes_tuple,
        use_compression_val,
        max_num_iterations_val,
        target_exploitability_percentage_val,
        print_progress_val,
    );
    
    println!("\n--- Example Main Finished ---");
} 