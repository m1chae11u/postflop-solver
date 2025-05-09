use postflop_solver::*;

fn main() {
    // 1. Configure the Game
    // ----------------------
    // Define player ranges, board cards, etc.
    // These are example values, modify them as needed.
    let oop_range = "66+,A8s+,A5s-A4s,AJo+,K9s+,KQo,QTs+,JTs,96s+,85s+,75s+,65s,54s";
    let ip_range = "QQ-22,AQs-A2s,ATo+,K5s+,KJo+,Q8s+,J8s+,T7s+,96s+,86s+,75s+,64s+,53s+";

    let card_config = CardConfig {
        range: [oop_range.parse().unwrap(), ip_range.parse().unwrap()],
        flop: flop_from_str("Td9d6h").unwrap(), // Example: Flop Td 9d 6h
        turn: card_from_str("Qc").unwrap(),   // Example: Turn Qc
        river: NOT_DEALT,                     // Solving for the turn, river is not dealt yet
    };

    // Define bet sizes, pot, stacks, etc.
    let bet_sizes = BetSizeOptions::try_from(("60%,e,a", "2.5x")).unwrap(); // Example bet sizes

    let tree_config = TreeConfig {
        initial_state: BoardState::Turn, // Must match the card_config (e.g., if turn card is dealt)
        starting_pot: 200,
        effective_stack: 900,
        flop_bet_sizes: [bet_sizes.clone(), bet_sizes.clone()],
        turn_bet_sizes: [bet_sizes.clone(), bet_sizes.clone()],
        river_bet_sizes: [bet_sizes.clone(), bet_sizes.clone()], // Still need to define for potential river actions
        // Add other TreeConfig parameters as needed, see examples/basic.rs for more options
        ..
        Default::default() // Use default for other fields if not specified
    };

    // Build the game tree
    let action_tree = ActionTree::new(tree_config.clone()).unwrap(); // Clone tree_config if needed later
    let mut game = PostFlopGame::with_config(card_config, action_tree).unwrap();

    println!("Game configured. Initial state: {:?}, Current player: {:?}", game.current_state(), game.current_player());
    println!("OOP private cards: {:?}", holes_to_strings(game.private_cards(0)).unwrap_or_default().len());
    println!("IP private cards: {:?}", holes_to_strings(game.private_cards(1)).unwrap_or_default().len());


    // 2. Allocate Memory
    // -------------------
    // Choose whether to use compression (true for 16-bit int, false for 32-bit float)
    let use_compression = false;
    game.allocate_memory(use_compression);
    println!("Memory allocated (compression: {}).", use_compression);

    // 3. Run the Solver
    // -----------------
    let max_num_iterations = 100; // Lower for a quick test, increase for more accuracy
    let target_exploitability_percentage = 0.01; // e.g., 1% of the pot
    let target_exploitability = game.tree_config().starting_pot as f32 * target_exploitability_percentage;
    let print_progress = true;

    println!("Starting solver for {} iterations or target exploitability {:.2}...", max_num_iterations, target_exploitability);
    let exploitability = solve(&mut game, max_num_iterations, target_exploitability, print_progress);
    println!("Solver finished. Final Exploitability: {:.4e} (target was {:.4e})", exploitability, target_exploitability);

    // Ensure weights are cached for EV/Equity calculations if you didn't run finalize or full solve
    game.cache_normalized_weights();

    // 4. Get and Print Solver Output (for the current node, typically the root after solve)
    // -------------------------------------------------------------------------------------

    // --- Strategy --- 
    let actions = game.available_actions();
    let strategy_values = game.strategy();

    println!("\n--- Strategy at Current Node ---");
    println!("Available Actions: {:?}", actions);

    // Output for OOP (player 0) if current player is OOP
    // Adjust player_index and logic if you navigate the tree
    let current_player_idx = game.current_player(); 
    println!("Current player to act: {}", if current_player_idx == 0 { "OOP" } else { "IP" });

    let player_hands = game.private_cards(current_player_idx);
    let player_hands_str = holes_to_strings(player_hands).unwrap_or_default();
    
    if !actions.is_empty() && !strategy_values.is_empty() {
        for (hand_idx, hand_str) in player_hands_str.iter().take(10).enumerate() { // Print for first 10 hands as example
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

    // --- Expected Values (EV) for OOP (Player 0) ---
    // Note: EV and Equity are often most meaningful at the root *before* any actions are played,
    // or for a specific player *before* their action.
    // If you called solve(), the game state is at the root.
    game.back_to_root(); // Ensure we are at the root to get overall EV/Equity if needed
    println!("\n--- Expected Values (EV) for OOP (Player 0) at the root ---");
    let oop_ev = game.expected_values(0);
    let oop_hands_for_ev = game.private_cards(0);
    let oop_hands_str_for_ev = holes_to_strings(oop_hands_for_ev).unwrap_or_default();
    for (i, hand_str) in oop_hands_str_for_ev.iter().take(10).enumerate() { // Print for first 10 hands
        if i < oop_ev.len() {
            println!("Hand {}: EV {:.3}", hand_str, oop_ev[i]);
        }
    }
    if oop_hands_str_for_ev.len() > 10 { println!("... (EV for more hands not shown for brevity)"); }


    // --- Equity for OOP (Player 0) ---
    println!("\n--- Equity for OOP (Player 0) at the root ---");
    let oop_equity = game.equity(0);
    // We can reuse oop_hands_str_for_ev from above
    for (i, hand_str) in oop_hands_str_for_ev.iter().take(10).enumerate() { // Print for first 10 hands
        if i < oop_equity.len() {
            println!("Hand {}: Equity {:.1}%", hand_str, oop_equity[i] * 100.0);
        }
    }
    if oop_hands_str_for_ev.len() > 10 { println!("... (Equity for more hands not shown for brevity)"); }
    
    // --- Average EV and Equity for OOP (Player 0) --- 
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


    // 5. Further Interaction (Example)
    // ---------------------------------
    // You can navigate the tree and get info for other nodes
    // game.back_to_root(); // Go to root if not already there
    // if !game.available_actions().is_empty() {
    //     println!("\nPlaying first available action at root: {:?}", game.available_actions()[0]);
    //     game.play(0); // Play the first available action
    //     println!("New current player: {}", if game.current_player() == 0 { "OOP" } else { "IP" });
    //     println!("Available actions now: {:?}", game.available_actions());
    //     // You could then print strategy for this new node, etc.
    // }

    println!("\n--- Example Finished ---");
} 