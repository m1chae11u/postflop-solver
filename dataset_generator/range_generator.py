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
            start_hand_sh = parts[0]
            end_hand_sh = parts[1]

            if not (len(start_hand_sh) == 3 and len(end_hand_sh) == 3 and start_hand_sh[0] == end_hand_sh[0] and start_hand_sh[2] == end_hand_sh[2]):
                # This condition specifically checks for A2s-A5s or KTs-KQs type (fixed primary, fixed suit type)
                # It doesn't support T8s-QJs yet easily.
                print(f"Warning: Range shorthand like '{shorthand_str}' currently expects fixed primary card and suit type (e.g. A2s-A5s or KTs-KQs).")
                # Attempt to process if they are single valid hands (e.g. AKs-AQo - no, this won't work here)
            else:
                stype = start_hand_sh[2]
                if stype not in HAND_TYPES:
                    print(f"Warning: Invalid suit type '{stype}' in range: {shorthand_str}")
                    return []

                fixed_primary_char = start_hand_sh[0]
                kicker1_char = start_hand_sh[1]
                kicker2_char = end_hand_sh[1]

                fixed_primary_idx = get_rank_index(fixed_primary_char)
                kicker1_idx = get_rank_index(kicker1_char)
                kicker2_idx = get_rank_index(kicker2_char)

                # Iterate kicker through the specified range
                # Ensure kicker is not same rank as primary_fixed_card
                loop_kicker_start_idx = min(kicker1_idx, kicker2_idx)
                loop_kicker_end_idx = max(kicker1_idx, kicker2_idx)

                for k_idx in range(loop_kicker_start_idx, loop_kicker_end_idx + 1):
                    if k_idx == fixed_primary_idx: # Avoid forming a pair like AA from A2s-AAs
                        continue
                    
                    current_kicker_char = RANKS[k_idx]
                    hr_char, lr_char = sorted([fixed_primary_char, current_kicker_char], key=get_rank_index)
                    expanded_hands.add(f"{hr_char}{lr_char}{stype}")
        else:
             print(f"Warning: Invalid format for '-' range: {shorthand_str}")

    # Final check and warning if no hands were generated by patterns above
    if not expanded_hands and shorthand_str not in ALL_169_HAND_COMBINATIONS:
        # If it was not a single valid hand and no patterns matched or pattern matching failed silently.
        print(f"Warning: Shorthand component '{shorthand_str}' not recognized or fully expanded.")

    return sorted(list(expanded_hands), key=lambda h: (
        get_rank_index(h[0]), 
        get_rank_index(h[1]),
        h[2:] # Suffix for sorting: pairs (empty) < offsuit ('o') < suited ('s') or alphabetically by suffix
    ))


if __name__ == '__main__':
    print(f"Total 169 hand combos: {len(ALL_169_HAND_COMBINATIONS)}")
    # print(ALL_169_HAND_COMBINATIONS)

    print("\\n--- Testing expand_range_shorthand ---")
    tests = [
        "AA",
        "KKs", # Should be invalid, but let's see. Corrected to warning.
        "AKs",
        "T9o",
        "JJ+",
        "QQ+",
        "A2s+",
        "AJs+",
        "KQs+", # KQs
        "KTs+", # KTs, KJs, KQs
        "QJo+", # QJo, QKo
        "AQ+",  # AQs, AQo, AKs, AKo
        "77-99",
        "TT-QQ",
        "QQ-TT", # Order should not matter
        "A2s-A5s",
        "A5s-A2s", # Order should not matter
        "KQo",
        "KTs-KQs", # KTs, KJs, KQs
        # "T8s-QJs" # More complex, currently limited support
    ]
    for test_str in tests:
        try:
            expanded = expand_range_shorthand(test_str)
            print(f"'{test_str}' -> {expanded}")
        except ValueError as e:
            print(f"Error for '{test_str}': {e}")

    print("\\n--- Testing comma separated (manual split) ---")
    compound_test = "AA,KK,QQ+,AJs-AQs,KTs+"
    all_expanded_hands = set()
    for part in compound_test.split(','):
        all_expanded_hands.update(expand_range_shorthand(part.strip()))
    print(f"'{compound_test}' -> {sorted(list(all_expanded_hands))}")

    compound_test_2 = "22+,A2s+,K9s+,Q9s+,J9s+,T8s+,97s+,86s+,75s+,65s,54s,A2o+,KTo+,QTo+,JTo+"
    all_expanded_hands_2 = set()
    for part in compound_test_2.split(','):
        all_expanded_hands_2.update(expand_range_shorthand(part.strip()))
    print(f"'{compound_test_2}' -> {len(list(all_expanded_hands_2))} hands") # Check count
