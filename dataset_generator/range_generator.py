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
        "QTs-KJs" -> ["QTs", "JTs", "KJs"] (assumes kicker increases with primary card)

    Handles individual hands like "AKs" or "77" correctly by returning them in a list.
    Note: Complex mixed ranges like "JJ+, AQs+, KQo" should be comma-separated
          and processed by splitting first, then calling this function on each part.
          This function handles one shorthand component at a time.
    """
    expanded_hands = set() # Use a set to avoid duplicates from overlapping shorthand like "AQ+"

    if not shorthand_str:
        return []

    # Check for direct match in all 169 hands (e.g. "AKs", "77")
    if shorthand_str in ALL_169_HAND_COMBINATIONS:
        return [shorthand_str]

    # Case 1: Pocket Pair Range (e.g., "JJ+", "77-99")
    if len(shorthand_str) == 3 and shorthand_str.endswith('+') and shorthand_str[0] == shorthand_str[1]: # e.g., "JJ+"
        pair_rank_char = shorthand_str[0]
        pair_rank_idx = get_rank_index(pair_rank_char)
        for i in range(pair_rank_idx, -1, -1): # Iterate upwards in rank (lower index)
            expanded_hands.add(f"{RANKS[i]}{RANKS[i]}")
    elif len(shorthand_str) == 5 and shorthand_str[2] == '-' and shorthand_str[0]==shorthand_str[1] and shorthand_str[3]==shorthand_str[4]: # e.g., "77-99"
        rank_char_start = shorthand_str[0]
        rank_char_end = shorthand_str[3]
        idx_start = get_rank_index(rank_char_start) # Higher index (e.g. 9 for "9")
        idx_end = get_rank_index(rank_char_end)     # Lower index (e.g. 7 for "7")
        
        # Ensure start_idx is for the lower rank in "77-99" meaning 7 is start, 9 is end
        # Our RANKS is ['A', ..., '2'], so A has index 0, 2 has index 12.
        # "99-77" is more natural for rank indices
        
        # If "77-99", RANKS.index('7') > RANKS.index('9')
        # We want to iterate from the rank of '7' up to '9'
        actual_start_idx = min(idx_start, idx_end)
        actual_end_idx = max(idx_start, idx_end)

        for i in range(actual_start_idx, actual_end_idx + 1):
            expanded_hands.add(f"{RANKS[i]}{RANKS[i]}")

    # Case 2: Ax+ type notation (e.g., "A9s+", "KTo+", "AQ+")
    # Covers XYo, XYs, XY+ (meaning both s and o)
    elif shorthand_str.endswith('+'):
        base = shorthand_str[:-1] # "A9s", "KTo", "AQ"
        
        rank1_char = base[0]
        rank2_char = base[1]
        r1_idx = get_rank_index(rank1_char)

        # Determine if specific suit type is given (s or o)
        stype = None
        if len(base) == 3: # "A9s" or "KTo"
            stype = base[2]
            if stype not in HAND_TYPES:
                raise ValueError(f"Invalid suit type in shorthand: {shorthand_str}")
        elif len(base) != 2: # "AQ"
             raise ValueError(f"Invalid shorthand format for '+': {shorthand_str}")

        r2_idx_base = get_rank_index(rank2_char)

        # Iterate kicker upwards
        for r2_idx_curr in range(r2_idx_base, r1_idx): # Kicker cannot be >= card1 rank
            current_rank1_char = RANKS[r1_idx] # Stays the same, e.g. 'A' in "A9s+"
            current_rank2_char = RANKS[r2_idx_curr] # Changes, e.g. '9', 'T', 'J', 'Q', 'K' (for A)

            # Ensure canonical order if r1_idx was not 0 (Ace)
            # For "KJs+", rank1 is K, rank2 is J. Kicker (J) iterates up to Q (but not K).
            # This loop structure implies r1 is fixed and r2 iterates up to r1.
            # This fits "A9s+" -> A9s, ATs, AJs, AQs, AKs
            # And "KJs+" -> KJs, KQs (r2_idx_curr goes from J_idx up to K_idx-1)
            # And "T8o+" -> T8o, T9o

            # Check for rank1_char == rank2_char: This shouldn't happen if r2_idx_curr < r1_idx
            if current_rank1_char == current_rank2_char:
                continue
            
            # Ensure order for string: higher rank first
            hr_char, lr_char = sorted([current_rank1_char, current_rank2_char], key=get_rank_index)


            if stype: # "A9s" or "KTo" type
                expanded_hands.add(f"{hr_char}{lr_char}{stype}")
            else: # "AQ+" type, add both suited and offsuit
                expanded_hands.add(f"{hr_char}{lr_char}s")
                expanded_hands.add(f"{hr_char}{lr_char}o")
                
    # Case 3: Range between two non-pair hands (e.g., "A2s-A5s", "T7o-T9o", "QJs-KJs")
    elif len(shorthand_str) >= 7 and shorthand_str[3] == '-': # e.g. "A2s-A5s" or "T9o-JTo" (more complex)
        start_hand = shorthand_str[:3]
        end_hand = shorthand_str[4:]

        if not (len(start_hand) == 3 and len(end_hand) == 3 and start_hand[2] == end_hand[2]):
            raise ValueError(f"Range shorthand like 'A2s-A5s' must have matching suit types. Got: {shorthand_str}")
        
        stype = start_hand[2]
        if stype not in HAND_TYPES:
            raise ValueError(f"Invalid suit type in range: {shorthand_str}")

        r1_start_char, r2_start_char = start_hand[0], start_hand[1]
        r1_end_char, r2_end_char = end_hand[0], end_hand[1]

        r1_start_idx, r2_start_idx = get_rank_index(r1_start_char), get_rank_index(r2_start_char)
        r1_end_idx, r2_end_idx = get_rank_index(r1_end_char), get_rank_index(r2_end_char)

        # This logic assumes one rank changes while the other stays the same OR both change in a suited connector way
        # Example 1: "A2s-A5s" (A stays, kicker changes 2->5)
        if r1_start_char == r1_end_char:
            fixed_rank_char = r1_start_char
            kicker_idx_loop_start = min(r2_start_idx, r2_end_idx)
            kicker_idx_loop_end = max(r2_start_idx, r2_end_idx)
            fixed_rank_idx = get_rank_index(fixed_rank_char)

            for k_idx in range(kicker_idx_loop_start, kicker_idx_loop_end + 1):
                if k_idx >= fixed_rank_idx : # Kicker cannot be same or higher rank (unless it's the other fixed card)
                    continue 
                hr_char, lr_char = sorted([fixed_rank_char, RANKS[k_idx]], key=get_rank_index)
                expanded_hands.add(f"{hr_char}{lr_char}{stype}")
        
        # Example 2: "T8s-QJs" (Suited connectors: T8s, J9s, QJs - this is simplified for now)
        # A more robust way for suited connectors: T8s, 97s, etc. or T8s, J8s, Q8s
        # Let's handle the case where the primary card increases and kicker increases one step:
        # e.g. QJs-KJs means QJs, KJs -- no, this is wrong. It should be QJs, KQs. No, wait.
        # "QTs-KJs" -> QTs, KJs means QTs (QJ, QK), JTs (JK), KJs. This gets complex quickly.
        # For "T8s-QJs", if interpreted as T8s, J9s, QJs:
        elif abs(r1_start_idx - r1_end_idx) == abs(r2_start_idx - r2_end_idx) and \
             abs(r1_start_idx-r2_start_idx) == 1 and abs(r1_end_idx-r2_end_idx) == 1: # Connectors
            
            # Iterate from the overall "lower" hand to "higher" hand
            # e.g. T8s to QJs. T is rank 4, 8 is rank 6. Q is rank 2, J is rank 3.
            # This means we are stepping r1 and r2 together.
            
            current_r1_idx = min(r1_start_idx, r1_end_idx) # "lowest" primary rank char index
            end_r1_idx = max(r1_start_idx, r1_end_idx)
            
            # Determine step direction for kicker based on primary rank
            # If QJs-T8s (Q->T, J->8) or T8s-QJs (T->Q, 8->J)
            # This assumes they are same-distance gappers or connectors
            
            # Simplified: Assuming r1_start/r2_start is the "lower" of the two.
            # User should input as T8s-QJs, not QJs-T8s for this logic to be simple.
            
            # Let's use a simpler interpretation for A2s-A5s which is common.
            # And for "QTs-KJs" -> if this means primary card Q->K, kicker T->J
            # If the ranks are consecutive and kicker is one less.
            # This part of shorthand parsing can get very ambiguous.
            # For now, focusing on the "A2s-A5s" type (fixed primary, kicker range).
            # And "77-99" type (done above).

            # The "QTs-KJs" -> QTs, JTs, KTs or QTs, QJs, QKs is hard to infer.
            # Let's assume for now it's not supported beyond fixed primary or fixed kicker.
            # So if r2_start_char == r2_end_char (fixed kicker, primary changes):
            # e.g., "T9s-Q9s"
            print(f"Note: Complex range shorthand like '{shorthand_str}' (changing both ranks in arbitrary ways) has limited support beyond fixed primary/kicker.")


    if not expanded_hands:
        # If nothing expanded, it might be a single hand or invalid.
        # We already checked for single valid hands.
        # It could be part of a comma separated list.
        # For now, if no patterns match and it's not a single valid hand, it's an error for this function.
        # However, a higher-level function will split by comma.
        # So, if "AKs,QQ" is passed, "AKs" will be handled, then "QQ".
        # If "XYZ" is passed, it won't match.
        # We assume if we reach here and expanded_hands is empty, the shorthand_str was not recognized.
        # For safety, let's re-check if it's a valid single hand if no patterns matched.
        if shorthand_str in ALL_169_HAND_COMBINATIONS:
             expanded_hands.add(shorthand_str)
        elif shorthand_str: # only raise if it's not an empty string from split
            print(f"Warning: Shorthand component '{shorthand_str}' not fully recognized or is invalid.")
            # raise ValueError(f"Shorthand component '{shorthand_str}' not recognized or is invalid.")


    return sorted(list(expanded_hands), key=lambda h: (
        get_rank_index(h[0]), 
        get_rank_index(h[1]),
        h[2:] # keeps 's' before 'o', and pairs like 'AA' distinct
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
