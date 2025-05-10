import random

# --- Constants ---
RANKS = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
SUITS = ['s', 'h', 'd', 'c'] # For deck creation if ever needed, not directly for 169 combos
HAND_TYPES = ['s', 'o'] # Suited, Offsuit

ALL_169_HAND_COMBINATIONS = []

def _initialize_169_hands():
    """
    Generates and stores all 169 unique starting hand combinations (e.g., 'AA', 'AKs', 'AQo').
    Populates the global ALL_169_HAND_COMBINATIONS list.
    """
    if ALL_169_HAND_COMBINATIONS: # Prevent re-initialization
        return

    # 1. Pocket pairs (13 hands)
    for r_idx, r_val in enumerate(RANKS):
        ALL_169_HAND_COMBINATIONS.append(f"{r_val}{r_val}")

    # 2. Suited and Offsuit hands (78 suited + 78 offsuit = 156 total non-pair combos)
    #    Each unique rank pairing (e.g., AK) has 1 suited and 1 offsuit version. 12C2 = 78 such pairings.
    for i in range(len(RANKS)):
        for j in range(i + 1, len(RANKS)):
            rank1 = RANKS[i]
            rank2 = RANKS[j]
            # Ensure canonical order (e.g., AKs, not KAs)
            ALL_169_HAND_COMBINATIONS.append(f"{rank1}{rank2}s")  # Suited
            ALL_169_HAND_COMBINATIONS.append(f"{rank1}{rank2}o")  # Offsuit
    # print(f"Initialized {len(ALL_169_HAND_COMBINATIONS)} hand combinations.")

_initialize_169_hands()


def get_rank_index(rank_char):
    """Returns the index of a rank character (A=0, K=1, ..., 2=12)."""
    if rank_char not in RANKS:
        raise ValueError(f"Invalid rank character: {rank_char}")
    return RANKS.index(rank_char)

def expand_range_shorthand(shorthand_str):
    """
    Expands poker range shorthand into a list of specific hand combinations.
    Examples:
        "JJ+" -> ["JJ", "QQ", "KK", "AA"]
        "A9s+" -> ["A9s", "ATs", "AJs", "AQs", "AKs"]
        "KTo+" -> ["KTo", "KJo", "KQo"]
        "AQ+" -> ["AQs", "AQo", "AKs", "AKo"] (Covers both suited and offsuit if not specified)
        "77-99" -> ["77", "88", "99"]
        "A2s-A5s" -> ["A2s", "A3s", "A4s", "A5s"]
        "QTs-KJs" -> QTs, KJs - this interpretation is tricky. Current support: KTs-KQs -> KTs, KJs, KQs

    Handles individual hands like "AKs" or "77" correctly by returning them in a list.
    Note: Complex mixed ranges like "JJ+, AQs+, KQo" should be comma-separated
          and processed by splitting first, then calling this function on each part.
          This function handles one shorthand component at a time.
    """
    expanded_hands = set() # Use a set to avoid duplicates

    if not shorthand_str:
        return []

    # Check for direct match in all 169 hands (e.g. "AKs", "77")
    if shorthand_str in ALL_169_HAND_COMBINATIONS:
        return [shorthand_str]

    # Case 1: Pocket Pair Range (e.g., "JJ+", "77-99")
    if len(shorthand_str) == 3 and shorthand_str.endswith('+') and shorthand_str[0] == shorthand_str[1]: # e.g., "JJ+"
        pair_rank_char = shorthand_str[0]
        pair_rank_idx = get_rank_index(pair_rank_char)
        # Iterate upwards in rank (lower index means stronger rank)
        for i in range(pair_rank_idx, -1, -1):
            expanded_hands.add(f"{RANKS[i]}{RANKS[i]}")
    elif len(shorthand_str) == 5 and shorthand_str[2] == '-' and shorthand_str[0]==shorthand_str[1] and shorthand_str[3]==shorthand_str[4]: # e.g., "77-99"
        rank_char_1 = shorthand_str[0]
        rank_char_2 = shorthand_str[3]
        idx_1 = get_rank_index(rank_char_1)
        idx_2 = get_rank_index(rank_char_2)
        
        # Iterate from the lower rank (higher index) to the higher rank (lower index)
        # or vice-versa, min/max handles order e.g. "99-77" or "77-99"
        start_loop_idx = min(idx_1, idx_2)
        end_loop_idx = max(idx_1, idx_2)

        for i in range(start_loop_idx, end_loop_idx + 1):
            expanded_hands.add(f"{RANKS[i]}{RANKS[i]}")

    # Case 2: Ax+ type notation (e.g., "A9s+", "KTo+", "AQ+")
    # Covers XYo, XYs, XY+ (meaning both s and o)
    # This case assumes shorthand_str[0] is the higher ranked card of the two initial ones.
    elif shorthand_str.endswith('+') and len(shorthand_str) >= 2 and shorthand_str[0] != shorthand_str[1]: # Avoids re-processing pairs like "AA+"
        base = shorthand_str[:-1] # "A9s", "KTo", "AQ"
        
        primary_rank_char = base[0]
        base_kicker_char = base[1]
        primary_rank_idx = get_rank_index(primary_rank_char)

        stype = None
        if len(base) == 3: # "A9s" or "KTo"
            stype = base[2]
            if stype not in HAND_TYPES:
                # This could be an error, or we could try to infer if it's a typo for a rank.
                # For now, let's assume it's an invalid suit type.
                print(f"Warning: Invalid suit type '{stype}' in shorthand: {shorthand_str}")
                return [] # Or raise error
        elif len(base) != 2: # e.g. from "A+" or something too short
            print(f"Warning: Invalid base for '+' shorthand: {base} from {shorthand_str}")
            return [] # Or raise error
        
        base_kicker_idx = get_rank_index(base_kicker_char)

        if base_kicker_idx <= primary_rank_idx: # Kicker is stronger or same as primary card (e.g. "AAs+" or "KAs+")
            print(f"Warning: Kicker '{base_kicker_char}' not weaker than primary '{primary_rank_char}' in {shorthand_str}")
            # Potentially handle this as an error or specific case if e.g. KAs+ should mean AKs.
            # For now, returning empty as it's ambiguous or implies a pair, which is Case 1.
            if primary_rank_char == base_kicker_char and stype is None: # e.g. AA+ (no s/o) should be JJ+
                 # This should have been caught by Case 1 if it was e.g. "AA+" format. If it's "AAo+", it's invalid.
                 pass # Let it fall through to a general warning if nothing is added.
            else:
                return []

        # Iterate kicker upwards in strength (downwards in index) from base_kicker up to (but not including) primary_rank
        for k_idx in range(base_kicker_idx, primary_rank_idx, -1):
            current_kicker_char = RANKS[k_idx]
            
            # sorted() ensures canonical order (higher rank first)
            hr_char, lr_char = sorted([primary_rank_char, current_kicker_char], key=get_rank_index)

            if stype: # Specific suit type given e.g. "A9s+"
                expanded_hands.add(f"{hr_char}{lr_char}{stype}")
            else: # No suit type given e.g. "AQ+", add both suited and offsuit
                expanded_hands.add(f"{hr_char}{lr_char}s")
                expanded_hands.add(f"{hr_char}{lr_char}o")
                
    # Case 3: Range between two non-pair hands (e.g., "A2s-A5s", "KTs-KQs")
    # Assumes the primary card is fixed, and the kicker varies.
    elif '-' in shorthand_str and len(shorthand_str) >= 7 : # e.g. "A2s-A5s"
        parts = shorthand_str.split('-')
        if len(parts) == 2:
            start_hand_sh = parts[0].strip() # Clean input
            end_hand_sh = parts[1].strip()   # Clean input

            # Validate format: e.g., XNs (3 chars), primary card is X, kicker N, suit s
            if not (len(start_hand_sh) == 3 and len(end_hand_sh) == 3 and \
                    start_hand_sh[0].isalnum() and start_hand_sh[1].isalnum() and \
                    end_hand_sh[0].isalnum() and end_hand_sh[1].isalnum() and \
                    start_hand_sh[2] in HAND_TYPES and end_hand_sh[2] in HAND_TYPES):
                print(f"Warning: Invalid component format for '-' range: '{shorthand_str}'. Expected XNs-XZs.")
                return []
            
            # Further validation: primary card and suit type must be the same,
            # and primary card should not be the same as its kicker (not a pair like AAs)
            if not (start_hand_sh[0] == end_hand_sh[0] and 
                    start_hand_sh[2] == end_hand_sh[2] and 
                    start_hand_sh[0] != start_hand_sh[1] and # Start hand is not a pair e.g. AAs from AAs-A5s
                    end_hand_sh[0] != end_hand_sh[1]):   # End hand is not a pair e.g. AAs from A2s-AAs
                print(f"Warning: Range shorthand like '{shorthand_str}' expects fixed primary card, fixed suit type, and non-pair components (e.g. A2s-A5s)." )
                return []
            
            stype = start_hand_sh[2]
            # This stype check is technically redundant due to earlier check, but safe.
            # if stype not in HAND_TYPES:
            #     print(f"Warning: Invalid suit type '{stype}' in range: {shorthand_str}")
            #     return []

            fixed_primary_char = start_hand_sh[0]
            kicker1_char = start_hand_sh[1]
            kicker2_char = end_hand_sh[1]

            # Check if kickers are valid ranks
            if not (fixed_primary_char in RANKS and kicker1_char in RANKS and kicker2_char in RANKS):
                print(f"Warning: Invalid ranks in '-' range components: {shorthand_str}")
                return []

            fixed_primary_idx = get_rank_index(fixed_primary_char)
            kicker1_idx = get_rank_index(kicker1_char)
            kicker2_idx = get_rank_index(kicker2_char)

            # Kicker cannot be the same as primary (e.g. AAs from A2s-AAs where A is primary)
            # This is implicitly handled by sorted([fixed_primary_char, current_kicker_char], key=get_rank_index)
            # as it would form a pair, but we can be explicit if needed.
            # However, the check `start_hand_sh[0] != start_hand_sh[1]` already prevents initial pair format.

            loop_kicker_start_idx = min(kicker1_idx, kicker2_idx)
            loop_kicker_end_idx = max(kicker1_idx, kicker2_idx)

            for k_idx in range(loop_kicker_start_idx, loop_kicker_end_idx + 1):
                if k_idx == fixed_primary_idx: # Avoid forming a pair with the primary card e.g. AA from AAs-AKs (if A was kicker)
                    continue
                
                current_kicker_char = RANKS[k_idx]
                # Ensure canonical order (higher rank first)
                hr_char, lr_char = sorted([fixed_primary_char, current_kicker_char], key=get_rank_index)
                expanded_hands.add(f"{hr_char}{lr_char}{stype}")
        else:
             print(f"Warning: Invalid format for '-' range (expected one dash): {shorthand_str}")

    # Final check and warning if no hands were generated by patterns above
    # Strip trailing comma for single hand check like "AA,"
    cleaned_shorthand_str = shorthand_str.rstrip(',')
    if not expanded_hands and cleaned_shorthand_str in ALL_169_HAND_COMBINATIONS:
        expanded_hands.add(cleaned_shorthand_str)
    elif not expanded_hands and shorthand_str not in ALL_169_HAND_COMBINATIONS: # if still no match after trying cleaned
        print(f"Warning: Shorthand component '{shorthand_str}' not recognized or fully expanded.")

    return sorted(list(expanded_hands), key=lambda h: (
        get_rank_index(h[0]), 
        get_rank_index(h[1]),
        h[2:] # Suffix for sorting: pairs (empty) < offsuit ('o') < suited ('s') or alphabetically by suffix
    ))


if __name__ == '__main__':
    print(f"Total 169 hand combos: {len(ALL_169_HAND_COMBINATIONS)}")

    print("\\n--- Comprehensive Test Cases for expand_range_shorthand ---")
    # Note: ALL_169_HAND_COMBINATIONS is already sorted by _initialize_169_hands and the key in expand_range_shorthand
    # We will sort the expected_list for consistent comparison.
    
    # Helper to generate all Ax hands (suited and offsuit, excluding AA)
    all_ax_hands = []
    for r_idx, r_val in enumerate(RANKS):
        if r_val == 'A':
            continue
        all_ax_hands.append(f"A{r_val}s")
        all_ax_hands.append(f"A{r_val}o")
    all_ax_hands = sorted(all_ax_hands, key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]), h[2:]))


    test_cases = {
        # Single Hands
        "AA": ["AA"],
        "AKs": ["AKs"],
        "T9o": ["T9o"],
        "22": ["22"],
        # Invalid single hands (or non-shorthand)
        "KKs": [], # Invalid pair format, should be caught by not being in ALL_169_HAND_COMBINATIONS and no pattern match
        "AXs": [], # Invalid rank 'X'
        "AAs": [], # Invalid suited pair

        # Pairs Plus Notation
        "JJ+": sorted(["AA", "KK", "QQ", "JJ"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]))),
        "QQ+": sorted(["AA", "KK", "QQ"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]))),
        "AA+": ["AA"], # AA already highest
        "22+": sorted([r+r for r in RANKS], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]))), # All pairs AA down to 22

        # Pairs Dash Notation
        "77-99": sorted(["99", "88", "77"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]))),
        "TT-QQ": sorted(["QQ", "JJ", "TT"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]))),
        "QQ-TT": sorted(["QQ", "JJ", "TT"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]))), # Order shouldn't matter
        "AA-KK": sorted(["AA", "KK"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]))),
        "22-44": sorted(["44", "33", "22"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]))),
        "55-55": ["55"],

        # XYs+ Notation (X fixed, Y lowest kicker, Y iterates up to X-1)
        "AQs+": sorted(["AKs", "AQs"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]), h[2:])),
        "AJs+": sorted(["AKs", "AQs", "AJs"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]), h[2:])),
        "A2s+": sorted([f"A{r}s" for r in RANKS[1:]], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]), h[2:])), # AKs...A2s
        "KJs+": sorted(["KQs", "KJs"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]), h[2:])),
        "KTs+": sorted(["KQs", "KJs", "KTs"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]), h[2:])),
        "QJs+": ["QJs"], # Q fixed, J is kicker. No K kicker as K > Q.
        "QTs+": sorted(["QJs", "QTs"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]), h[2:])),
        "JTs+": ["JTs"],
        "AKs+": ["AKs"], # No kicker stronger than K for A, already AK.
        
        # XYos+ Notation
        "AQo+": sorted(["AKo", "AQo"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]), h[2:])),
        "AJo+": sorted(["AKo", "AQo", "AJo"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]), h[2:])),
        "A2o+": sorted([f"A{r}o" for r in RANKS[1:]], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]), h[2:])), # AKo...A2o
        "KJo+": sorted(["KQo", "KJo"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]), h[2:])),
        "KQo+": ["KQo"],
        "QJo+": ["QJo"], # As confirmed
        
        # XY+ general (no suit specified) -> expands to both s and o
        "AQ+": sorted(["AKs", "AKo", "AQs", "AQo"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]), h[2:])),
        "AJ+": sorted(["AKs", "AKo", "AQs", "AQo", "AJs", "AJo"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]), h[2:])),
        "A2+": all_ax_hands, # All Ax suited and offsuit, excluding AA
        "KQ+": sorted(["KQs", "KQo"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]), h[2:])),
        
        # XNs-XZs Notation (fixed primary, kicker range)
        "A2s-A5s": sorted(["A5s", "A4s", "A3s", "A2s"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]), h[2:])),
        "A5s-A2s": sorted(["A5s", "A4s", "A3s", "A2s"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]), h[2:])), # Order shouldn't matter
        "ATs-AQs": sorted(["AQs", "AJs", "ATs"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]), h[2:])),
        "K9s-KJs": sorted(["KJs", "KTs", "K9s"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]), h[2:])),
        "Q8s-QTs": sorted(["QTs", "Q9s", "Q8s"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]), h[2:])),
        "AAs-A5s": [], # Invalid: cannot make AA into AAs
        "A2o-A4o": sorted(["A4o", "A3o", "A2o"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]), h[2:])),
        "T7o-T9o": sorted(["T9o", "T8o", "T7o"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]), h[2:])),

        # Edge cases and invalid shorthand for XY+ and XNs-XZs
        "KAs+": [], # Kicker A is stronger than K (should be AKs, which is a single hand)
        "AAo+": [], # Pair with suit type plus
        "A2s-K2s": [], # Primary card changes, not supported by this pattern
        "A2s-A2o": [], # Suit type changes, not supported
        "A2x-A5x": [], # Invalid suit type 'x'
        "A2s-AAs": [], # Trying to make pair from kicker range (A2s-AAs -> AAs not valid hand)
        "62s+": ["62s", "63s", "64s", "65s"], # Fixed primary 6, kickers 2,3,4,5

        # From previous user tests that caused issues (re-confirming)
        "KTs-KQs": sorted(["KQs", "KJs", "KTs"], key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]), h[2:])),

        # Empty string
        "": [],
        # Just a comma (would be split to empty strings)
        ",": [], # expand_range_shorthand would receive ""
        "AA,": ["AA"] # Trailing comma, part is "AA"
    }

    passed_count = 0
    failed_count = 0
    failed_details = []

    print("\\nRunning tests...")
    for test_str, expected_list_val in test_cases.items():
        # The function itself returns a sorted list based on rank indices and then suffix.
        # Ensure expected_list_val is also sorted with the same key for fair comparison.
        expected_sorted = sorted(list(set(expected_list_val)), key=lambda h: (
            get_rank_index(h[0]) if len(h) >=1 else -1, 
            get_rank_index(h[1]) if len(h) >=2 else -1,
            h[2:] if len(h) >=3 else ""
        ))
        
        actual_expanded = expand_range_shorthand(test_str)
        # actual_expanded is already sorted by the function's key

        if actual_expanded == expected_sorted:
            # print(f"PASSED: '{test_str}' -> {actual_expanded}")
            passed_count += 1
        else:
            print(f"FAILED: '{test_str}'")
            print(f"  Expected: {expected_sorted}")
            print(f"  Actual:   {actual_expanded}")
            failed_count += 1
            failed_details.append({
                "test": test_str,
                "expected": expected_sorted,
                "actual": actual_expanded
            })

    print("\\n--- Test Summary ---")
    print(f"Total tests: {len(test_cases)}")
    print(f"Passed: {passed_count}")
    print(f"Failed: {failed_count}")

    if failed_count > 0:
        print("\\n--- Failed Test Details ---")
        for fail in failed_details:
            print(f"Test:     '{fail['test']}'")
            print(f"  Expected: {fail['expected']}")
            print(f"  Actual:   {fail['actual']}")
            print("-" * 20)
