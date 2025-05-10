//! An open-source postflop solver library.
//!
//! # Examples
//!
//! See the [examples] directory.
//!
//! [examples]: https://github.com/b-inary/postflop-solver/tree/main/examples
//!
//! # Implementation details
//! - **Algorithm**: The solver uses the state-of-the-art [Discounted CFR] algorithm.
//!   Currently, the value of γ is set to 3.0 instead of the 2.0 recommended in the original paper.
//!   Also, the solver resets the cumulative strategy when the number of iterations is a power of 4.
//! - **Performance**: The solver engine is highly optimized for performance with maintainable code.
//!   The engine supports multithreading by default, and it takes full advantage of unsafe Rust in hot spots.
//!   The developer reviews the assembly output from the compiler and ensures that SIMD instructions are used as much as possible.
//!   Combined with the algorithm described above, the performance surpasses paid solvers such as PioSOLVER and GTO+.
//! - **Isomorphism**: The solver does not perform any abstraction.
//!   However, isomorphic chances (turn and river deals) are combined into one.
//!   For example, if the flop is monotone, the three non-dealt suits are isomorphic,
//!   allowing us to skip the calculation for two of the three suits.
//! - **Precision**: 32-bit floating-point numbers are used in most places.
//!   When calculating summations, temporary values use 64-bit floating-point numbers.
//!   There is also a compression option where each game node stores the values
//!   by 16-bit integers with a single 32-bit floating-point scaling factor.
//! - **Bunching effect**: At the time of writing, this is the only implementation that can handle the bunching effect.
//!   It supports up to four folded players (6-max game).
//!   The implementation correctly counts the number of card combinations and does not rely on heuristics
//!   such as manipulating the probability distribution of the deck.
//!   Note, however, that enabling the bunching effect increases the time complexity
//!   of the evaluation at the terminal nodes and slows down the computation significantly.
//!
//! [Discounted CFR]: https://arxiv.org/abs/1809.04040
//!
//! # Crate features
//! - `bincode`: Uses [bincode] crate (2.0.0-rc.3) to serialize and deserialize the `PostFlopGame` struct.
//!   This feature is required to save and load the game tree.
//!   Enabled by default.
//! - `custom-alloc`: Uses custom memory allocator in solving process (only available in nightly Rust).
//!   It significantly reduces the number of calls of the default allocator,
//!   so it is recommended to use this feature when the default allocator is not so efficient.
//!   Note that this feature assumes that, at most, only one instance of `PostFlopGame` is available
//!   when solving in a program.
//!   Disabled by default.
//! - `rayon`: Uses [rayon] crate for parallelization.
//!   Enabled by default.
//! - `zstd`: Uses [zstd] crate to compress and decompress the game tree.
//!   This feature is required to save and load the game tree with compression.
//!   Disabled by default.
//!
//! [bincode]: https://github.com/bincode-org/bincode
//! [rayon]: https://github.com/rayon-rs/rayon
//! [zstd]: https://github.com/gyscos/zstd-rs

#![cfg_attr(feature = "custom-alloc", feature(allocator_api))]

#[cfg(feature = "custom-alloc")]
mod alloc;

#[cfg(feature = "bincode")]
mod file;

mod action_tree;
mod atomic_float;
mod bet_size;
mod bunching;
mod card;
mod game;
mod hand;
mod hand_table;
mod interface;
mod mutex_like;
mod range;
mod sliceop;
mod solver;
mod utility;

#[cfg(feature = "bincode")]
pub use file::*;

pub use action_tree::*;
pub use bet_size::*;
pub use bunching::*;
pub use card::*;
pub use game::*;
pub use interface::*;
pub use mutex_like::*;
pub use range::*;
pub use solver::*;
pub use utility::*;

// Added for FFI
use std::os::raw::{c_char, c_int, c_float, c_uint};
use std::ffi::CStr;

#[no_mangle]
pub extern "C" fn run_solver_for_gamestate_ffi(
    oop_range_c_str: *const c_char,
    ip_range_c_str: *const c_char,
    flop_c_str: *const c_char,
    turn_card_opt_c_str: *const c_char,
    river_card_opt_c_str: *const c_char,
    initial_pot: c_int,
    eff_stack: c_int,
    use_compression_flag_c: u8,
    max_iterations_val: c_uint,
    target_exploit_percentage_val: c_float,
    should_print_progress_c: u8,
) {
    let oop_range_str = unsafe { CStr::from_ptr(oop_range_c_str).to_str().expect("Invalid OOP range string") };
    let ip_range_str = unsafe { CStr::from_ptr(ip_range_c_str).to_str().expect("Invalid IP range string") };
    let flop_str = unsafe { CStr::from_ptr(flop_c_str).to_str().expect("Invalid flop string") };

    let turn_card_opt_str = if turn_card_opt_c_str.is_null() {
        None
    } else {
        let s = unsafe { CStr::from_ptr(turn_card_opt_c_str).to_str().expect("Invalid turn card string") };
        if s.is_empty() { None } else { Some(s) }
    };

    let river_card_opt_str = if river_card_opt_c_str.is_null() {
        None
    } else {
        let s = unsafe { CStr::from_ptr(river_card_opt_c_str).to_str().expect("Invalid river card string") };
        if s.is_empty() { None } else { Some(s) }
    };
    
    let use_compression_flag = use_compression_flag_c != 0;
    let should_print_progress = should_print_progress_c != 0;
    
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

    let bet_sizes = BetSizeOptions::default();

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

    if should_print_progress {
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
    }

    // 2. Allocate Memory
    // -------------------
    game.allocate_memory(use_compression_flag);
    if should_print_progress {
        println!("Memory allocated (compression: {}).", use_compression_flag);
    }

    // 3. Run the Solver
    // -----------------
    let target_exploitability = initial_pot as f32 * target_exploit_percentage_val;
    
    if should_print_progress {
        println!("Starting solver for {} iterations or target exploitability {:.2}...", max_iterations_val, target_exploitability);
    }
    let exploitability = solve(&mut game, max_iterations_val, target_exploitability, should_print_progress);
    if should_print_progress {
        println!("Solver finished. Final Exploitability: {:.4e} (target was {:.4e})", exploitability, target_exploitability);
    }

    // 4. Get and Print Solver Output (for the current node, typically the root after solve)
    // -------------------------------------------------------------------------------------
    if should_print_progress {
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
            let average_ev_oop = compute_average(&oop_ev, oop_weights);
            println!("Average EV for OOP: {:.3}", average_ev_oop);
        } else {
            println!("Could not compute average EV for OOP (empty data or mismatched lengths).");
        }
        if !oop_equity.is_empty() && !oop_weights.is_empty() && oop_equity.len() == oop_weights.len() {
            let average_equity_oop = compute_average(&oop_equity, oop_weights);
            println!("Average Equity for OOP: {:.1}%", average_equity_oop * 100.0);
        } else {
            println!("Could not compute average Equity for OOP (empty data or mismatched lengths).");
        }
        println!("\n--- Solver Run Finished (FFI) ---");
    }
}
