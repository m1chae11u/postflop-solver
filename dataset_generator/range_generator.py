import random

# --- Constants ---
RANKS = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
SUITS = ['s', 'h', 'd', 'c'] # For deck creation if ever needed, not directly for 169 combos
HAND_TYPES = ['s', 'o'] # Suited, Offsuit

ALL_169_HAND_COMBINATIONS = []

def get_rank_index(rank_char):
    """Returns the index of a rank character (A=0, K=1, ..., 2=12)."""
    if rank_char not in RANKS:
        raise ValueError(f"Invalid rank character: {rank_char}")
    return RANKS.index(rank_char)

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

# Ensure ALL_169_HAND_COMBINATIONS is sorted in a canonical way that can represent strength.
# The _initialize_169_hands already sorts pairs first, then by rank, then suited before offsuit for same ranks.
# For HAND_STRENGTH_RANK, we want a single, definitive sorted list.
# The key used in expand_range_shorthand's final sort is good:
# key=lambda h: (get_rank_index(h[0]), get_rank_index(h[1]), h[2:] if len(h) > 2 else '')
# This effectively groups AA, then AKs, AKo, then AQs, AQo ... KK, KQs, KQo etc.
SORTED_MASTER_HAND_LIST = sorted(ALL_169_HAND_COMBINATIONS, key=lambda h: (
    get_rank_index(h[0]), 
    get_rank_index(h[1]),
    # Ensure pairs (e.g., 'AA', length 2) are treated consistently for sorting attribute
    # by giving them an empty string for the third sort key component (suit/type).
    # Suited ('s') will typically sort before offsuit ('o') with string comparison.
    (h[2:] if len(h) > 2 else '') 
))

HAND_STRENGTH_RANK = {hand_str: rank for rank, hand_str in enumerate(SORTED_MASTER_HAND_LIST)}

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
        h[2:] # keeps 's' before 'o', and pairs like 'AA' distinct
    ))


# --- Reference Range Definitions ---

# These are example shorthand strings. You should tailor these to the specific
# preflop scenarios and player tendencies you want to model.
REFERENCE_RANGES_SHORTHAND = {
    'OOP': { # Out of Position Player
        'Tight': "QQ+,AKs,AKo",
        'Balanced': "77+,AJs+,KQs,ATo+,KQo",
        'Loose': "22+,A2s+,K7s+,Q8s+,J8s+,T7s+,97s+,87s+,A7o+,K9o+,Q9o+,J9o+,T9o"
    },
    'IP': { # In Position Player
        'Tight': "JJ+,AQs+,AQo+",
        'Balanced': "55+,ATs+,KJs+,QTs+,AJo+,KJo+",
        'Loose': "22+,A2s+,K5s+,Q8s+,J7s+,T7s+,96s+,86s+,75s+,64s+,53s+,A2o+,K9o+,Q9o+,J9o+,T8o+"
    }
}

PROCESSED_REFERENCE_RANGES = {}

def _process_reference_ranges():
    """
    Expands the shorthand strings in REFERENCE_RANGES_SHORTHAND
    and populates PROCESSED_REFERENCE_RANGES with lists of actual hand combinations.
    This should be called once when the module is initialized.
    """
    if PROCESSED_REFERENCE_RANGES: # Avoid reprocessing if called multiple times
        return

    for player_role, profiles in REFERENCE_RANGES_SHORTHAND.items():
        PROCESSED_REFERENCE_RANGES[player_role] = {}
        for range_type, shorthand_str in profiles.items():
            if not shorthand_str: # Handle empty shorthand string if any
                PROCESSED_REFERENCE_RANGES[player_role][range_type] = []
                continue
            
            expanded_hands_set = set()
            for part in shorthand_str.split(','):
                part_stripped = part.strip()
                if part_stripped: # Ensure part is not empty after strip
                    expanded_hands_set.update(expand_range_shorthand(part_stripped))
            
            PROCESSED_REFERENCE_RANGES[player_role][range_type] = sorted(list(expanded_hands_set), key=lambda h: (
                get_rank_index(h[0]),
                get_rank_index(h[1]),
                # Check length for pairs like 'AA' which don't have h[2:]
                h[2:] if len(h) > 2 else '' 
            ))
    # print("Debug: PROCESSED_REFERENCE_RANGES populated.")

_process_reference_ranges() # Populate at module load


# --- Utility for Range Analysis ---

def get_range_strength_bounds(range_list):
    """
    Finds the strength ranks of the strongest (lowest rank number) and 
    weakest (highest rank number) hands in a given list of hand strings.

    Args:
        range_list: A list of hand strings (e.g., ["AA", "KK", "AJs"]).

    Returns:
        A tuple (min_strength_rank, max_strength_rank) or (None, None) if range_list is empty.
    """
    if not range_list:
        return None, None

    min_rank = float('inf')
    max_rank = float('-inf')

    for hand_str in range_list:
        if hand_str not in HAND_STRENGTH_RANK:
            # This case should ideally not happen if range_list contains valid 169 hand strings
            print(f"Warning: Hand '{hand_str}' not found in HAND_STRENGTH_RANK. Skipping in bounds calculation.")
            continue
        
        rank = HAND_STRENGTH_RANK[hand_str]
        if rank < min_rank:
            min_rank = rank
        if rank > max_rank:
            max_rank = rank
            
    if min_rank == float('inf'): # Should only happen if all hands were invalid
        return None, None
        
    return min_rank, max_rank


# --- Adaptive Range Selection and Perturbation (Stubbed) ---

PLAYER_ROLES = ['OOP', 'IP']
# Order from tightest to loosest is important for adjustments
RANGE_TYPE_ORDER = ['Tight', 'Balanced', 'Loose'] 
DEFAULT_INITIAL_RANGE_TYPE = 'Balanced'

# How many strength ranks outside a category's bounds is acceptable for hero hand
ACCEPTABLE_WEAKNESS_OFFSET = 30 # e.g., hero hand can be up to X ranks weaker
ACCEPTABLE_STRENGTH_OFFSET = 15 # e.g., hero hand can be up to Y ranks stronger

def determine_hero_range_type_and_base_range(
    hero_hand_str,
    hero_player_role,
    initial_range_type_preference=DEFAULT_INITIAL_RANGE_TYPE,
    weakness_offset=ACCEPTABLE_WEAKNESS_OFFSET,
    strength_offset=ACCEPTABLE_STRENGTH_OFFSET
):
    """
    Determines the most appropriate range type (Tight, Balanced, Loose) for the hero
    based on their actual hand, and returns that type and its base range list.

    Args:
        hero_hand_str: The hero's specific hand (e.g., "AKo").
        hero_player_role: 'OOP' or 'IP'.
        initial_range_type_preference: Start with this type ('Tight', 'Balanced', 'Loose').
        weakness_offset: How much weaker (higher rank) hero hand can be than range's weakest.
        strength_offset: How much stronger (lower rank) hero hand can be than range's strongest.

    Returns:
        A tuple (final_hero_range_type_str, final_base_hero_range_list).
    """
    if hero_hand_str not in HAND_STRENGTH_RANK:
        raise ValueError(f"Hero hand '{hero_hand_str}' not found in HAND_STRENGTH_RANK.")
    hero_strength_rank = HAND_STRENGTH_RANK[hero_hand_str]

    if initial_range_type_preference not in RANGE_TYPE_ORDER:
        print(f"Warning: Invalid initial_range_type_preference '{initial_range_type_preference}'. Using default: '{DEFAULT_INITIAL_RANGE_TYPE}'")
        current_range_type = DEFAULT_INITIAL_RANGE_TYPE
    else:
        current_range_type = initial_range_type_preference
    
    # Iteratively adjust range type - at most a couple of steps
    for _ in range(len(RANGE_TYPE_ORDER)): # Max iterations to prevent infinite loops
        current_base_range_list = PROCESSED_REFERENCE_RANGES[hero_player_role][current_range_type]
        if not current_base_range_list: # Should not happen with current setup
            print(f"Warning: Empty base range for {hero_player_role} {current_range_type}. Cannot assess bounds.")
            break 

        strongest_rank_in_base, weakest_rank_in_base = get_range_strength_bounds(current_base_range_list)

        if strongest_rank_in_base is None: # Empty or invalid range
             print(f"Warning: Could not get bounds for {hero_player_role} {current_range_type}. Using current type.")
             break

        # Check if hero hand is too weak for the current range type
        if hero_strength_rank > weakest_rank_in_base + weakness_offset:
            current_type_idx = RANGE_TYPE_ORDER.index(current_range_type)
            if current_type_idx < len(RANGE_TYPE_ORDER) - 1: # Not already the loosest
                current_range_type = RANGE_TYPE_ORDER[current_type_idx + 1]
                # print(f"Debug: Hero hand {hero_hand_str} (rank {hero_strength_rank}) too weak for {RANGE_TYPE_ORDER[current_type_idx]}. Trying {current_range_type}.")
                continue # Re-evaluate with the new, looser type
            else:
                # print(f"Debug: Hero hand {hero_hand_str} too weak, already at loosest type {current_range_type}.")
                break # Already at the loosest, stop adjusting
        
        # Check if hero hand is too strong for the current range type
        elif hero_strength_rank < strongest_rank_in_base - strength_offset:
            current_type_idx = RANGE_TYPE_ORDER.index(current_range_type)
            if current_type_idx > 0: # Not already the tightest
                current_range_type = RANGE_TYPE_ORDER[current_type_idx - 1]
                # print(f"Debug: Hero hand {hero_hand_str} (rank {hero_strength_rank}) too strong for {RANGE_TYPE_ORDER[current_type_idx]}. Trying {current_range_type}.")
                continue # Re-evaluate with the new, tighter type
            else:
                # print(f"Debug: Hero hand {hero_hand_str} too strong, already at tightest type {current_range_type}.")
                break # Already at the tightest, stop adjusting
        else:
            # print(f"Debug: Hero hand {hero_hand_str} fits within {current_range_type} (bounds: {strongest_rank_in_base}-{weakest_rank_in_base}).")
            break # Hero hand fits, current_range_type is good
            
    final_base_list = PROCESSED_REFERENCE_RANGES[hero_player_role][current_range_type]
    return current_range_type, final_base_list


def _perform_perturbation(base_range_list, player_role, range_type):
    """
    (STUB) Performs perturbation on a base range list.
    For now, it just returns a copy of the base list.
    """
    # In the future, this will involve logic to slightly alter the base_range_list
    # based on player_role and range_type.
    return list(base_range_list) # Return a copy

def generate_player_range_info(
    player_role,
    is_hero,
    hero_hand_str_if_any=None, # e.g., "AKo"
    range_type_preference=DEFAULT_INITIAL_RANGE_TYPE # For villain, or initial for hero
):
    """
    Generates final range information for a player, adapting for hero if specified.
    Includes (stubbed) perturbation and hero hand force-inclusion.
    """
    if player_role not in PLAYER_ROLES:
        raise ValueError(f"Invalid player_role: {player_role}")
    if range_type_preference not in RANGE_TYPE_ORDER:
        print(f"Warning: Invalid range_type_preference '{range_type_preference}'. Using default: '{DEFAULT_INITIAL_RANGE_TYPE}'")
        range_type_preference = DEFAULT_INITIAL_RANGE_TYPE

    actual_base_hands = []
    chosen_range_type = ""

    if is_hero:
        if not hero_hand_str_if_any:
            raise ValueError("hero_hand_str_if_any must be provided if is_hero is True.")
        
        chosen_range_type, actual_base_hands = determine_hero_range_type_and_base_range(
            hero_hand_str=hero_hand_str_if_any,
            hero_player_role=player_role,
            initial_range_type_preference=range_type_preference
        )
    else: # For Villain
        chosen_range_type = range_type_preference
        actual_base_hands = PROCESSED_REFERENCE_RANGES[player_role][chosen_range_type]

    # --- Perturbation Step (currently a stub) ---
    perturbed_hands_list = _perform_perturbation(actual_base_hands, player_role, chosen_range_type)

    # --- Hero Hand Force Inclusion (Safety Net) ---
    if is_hero and hero_hand_str_if_any:
        if hero_hand_str_if_any not in perturbed_hands_list:
            # Add and re-sort to maintain order if desired, though for solver string order may not matter
            temp_set = set(perturbed_hands_list)
            temp_set.add(hero_hand_str_if_any)
            perturbed_hands_list = sorted(list(temp_set), key=lambda h: HAND_STRENGTH_RANK.get(h, float('inf')))
            # print(f"Debug: Hero hand '{hero_hand_str_if_any}' force-added to perturbed list for {player_role}.")

    # --- Final comma-separated string for the solver ---
    # Solver might not care about the order, but consistency is good.
    final_range_str = ",".join(perturbed_hands_list) 

    return {
        'player_role': player_role,
        'is_hero': is_hero,
        'hero_hand_actual': hero_hand_str_if_any if is_hero else None,
        'range_type_selected': chosen_range_type,
        'base_hands_count': len(actual_base_hands),
        # 'base_hands_sample': actual_base_hands[:5], # For debugging
        'final_hands_count': len(perturbed_hands_list),
        'final_hands_sample': perturbed_hands_list[:10], # For debugging, show post-perturbation/inclusion
        'final_range_str': final_range_str
    }

if __name__ == '__main__':
    print(f"Total 169 hand combos: {len(ALL_169_HAND_COMBINATIONS)}")
    # print(ALL_169_HAND_COMBINATIONS)

    # Removing older, direct tests for expand_range_shorthand to keep main output cleaner.
    # Those tests were: 
    # print("\\n--- Testing expand_range_shorthand ---")
    # tests = [...]
    # for test_str in tests: ...
    # print("\\n--- Testing comma separated (manual split) ---")
    # compound_test = "AA,KK,QQ+,AJs-AQs,KTs+"
    # ...
    # compound_test_2 = "22+,A2s+,K9s+,Q9s+,J9s+,T8s+,97s+,86s+,75s+,65s,54s,A2o+,KTo+,QTo+,JTo+"
    # ...

    print("\\n--- Displaying Processed Reference Ranges & Their Strength Bounds ---")
    for role, profiles in PROCESSED_REFERENCE_RANGES.items():
        print(f"Role: {role}")
        for r_type, hands in profiles.items():
            min_r, max_r = get_range_strength_bounds(hands)
            min_h = SORTED_MASTER_HAND_LIST[min_r] if min_r is not None else "N/A"
            max_h = SORTED_MASTER_HAND_LIST[max_r] if max_r is not None else "N/A"
            print(f"  Type: {r_type} ({len(hands)} combos)")
            print(f"    Hands sample: {hands[:10]}...")
            print(f"    Strength Ranks: Min={min_r} (Hand: {min_h}), Max={max_r} (Hand: {max_h})")

    print("\\n--- Master Hand List Sample (for strength reference) ---")
    print(f"Strongest 10: {SORTED_MASTER_HAND_LIST[:10]}")
    print(f"Weakest 10: {SORTED_MASTER_HAND_LIST[-10:]}")
    if 'AKs' in HAND_STRENGTH_RANK and '72o' in HAND_STRENGTH_RANK:
        print(f"Strength rank of AKs: {HAND_STRENGTH_RANK['AKs']}")
        print(f"Strength rank of T9s: {HAND_STRENGTH_RANK.get('T9s', 'N/A')}")
        print(f"Strength rank of 22: {HAND_STRENGTH_RANK.get('22', 'N/A')}")
        print(f"Strength rank of 72o: {HAND_STRENGTH_RANK['72o']}")

    print("\\n--- Testing Adaptive Range Selection for Hero ---")
    hero_test_cases = [
        {"role": "OOP", "hand": "AA", "pref": "Balanced"}, # Should likely stay Tight or Balanced
        {"role": "OOP", "hand": "AKs", "pref": "Balanced"},
        {"role": "IP", "hand": "T9s", "pref": "Tight"},   # Should shift to Balanced or Loose
        {"role": "OOP", "hand": "72o", "pref": "Balanced"}, # Should shift to Loose
        {"role": "IP", "hand": "22", "pref": "Tight"},    # Should shift to Balanced or Loose
        {"role": "OOP", "hand": "65s", "pref": "Tight"},  # Should shift to Loose or Balanced
        {"role": "IP", "hand": "A5s", "pref": "Loose"} # Might stay loose, or balanced
    ]

    for test_case in hero_test_cases:
        print(f"\nInput: Hero={test_case['role']}, Hand='{test_case['hand']}', Initial Pref='{test_case['pref']}'")
        result = generate_player_range_info(
            player_role=test_case['role'],
            is_hero=True,
            hero_hand_str_if_any=test_case['hand'],
            range_type_preference=test_case['pref']
        )
        print(f"  Output: Selected Type='{result['range_type_selected']}', Final Hands ({result['final_hands_count']}): {result['final_hands_sample']}...")
        if test_case['hand'] not in result['final_hands_sample'] and test_case['hand'] not in result['final_range_str']:
            print(f"  WARNING: Hero hand '{test_case['hand']}' missing from final range string/sample!")
        elif test_case['hand'] not in result['final_hands_sample'] and test_case['hand'] in result['final_range_str']:
             # This is fine if sample is small
            pass # print(f"  Note: Hero hand '{test_case['hand']}' in string but not in first 10 sample.")

    print("\\n--- Testing Villain Range Generation (No Adaptation) ---")
    villain_test_cases = [
        {"role": "IP", "pref": "Tight"},
        {"role": "OOP", "pref": "Loose"}
    ]
    for test_case in villain_test_cases:
        print(f"\nInput: Villain={test_case['role']}, Pref='{test_case['pref']}'")
        result = generate_player_range_info(
            player_role=test_case['role'],
            is_hero=False,
            range_type_preference=test_case['pref']
        )
        print(f"  Output: Selected Type='{result['range_type_selected']}' (should match pref), Final Hands ({result['final_hands_count']}): {result['final_hands_sample']}...")
