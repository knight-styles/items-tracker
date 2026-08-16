import re
from typing import List, Tuple, Any, Dict, Optional


def damerau_levenshtein_distance(s1: str, s2: str) -> int:
    """
    Computes Damerau-Levenshtein distance between strings s1 and s2.
    Handles insertions, deletions, substitutions, and adjacent transpositions.
    """
    len1, len2 = len(s1), len(s2)
    if len1 == 0:
        return len2
    if len2 == 0:
        return len1

    # Matrix for distance calculation
    d = {}
    for i in range(-1, len1 + 1):
        d[(i, -1)] = i + 1
    for j in range(-1, len2 + 1):
        d[(-1, j)] = j + 1

    for i in range(len1):
        for j in range(len2):
            cost = 0 if s1[i] == s2[j] else 1
            d[(i, j)] = min(
                d[(i - 1, j)] + 1,        # deletion
                d[(i, j - 1)] + 1,        # insertion
                d[(i - 1, j - 1)] + cost,  # substitution
            )
            if i > 0 and j > 0 and s1[i] == s2[j - 1] and s1[i - 1] == s2[j]:
                d[(i, j)] = min(d[(i, j)], d[(i - 2, j - 2)] + cost)  # transposition

    return d[(len1 - 1, len2 - 1)]


def normalize_text(text: str) -> str:
    """Strips whitespace, converts to lowercase, and collapses multiple spaces."""
    if not text:
        return ""
    text = text.lower().strip()
    return re.sub(r"\s+", " ", text)


def get_allowed_max_distance(query_token_len: int) -> int:
    """Determines maximum allowable edit distance based on token length."""
    if query_token_len <= 3:
        return 0
    elif query_token_len <= 7:
        return 1
    else:
        return 2


def score_token_match(q_token: str, target_words: List[str], full_target_str: str) -> Tuple[float, bool]:
    """
    Scores how well a query token matches target words and string.
    Returns (score, is_fuzzy).
    Higher scores indicate better relevance.
    """
    if not q_token or not full_target_str:
        return 0.0, False

    # 1. Exact full string match
    if q_token == full_target_str:
        return 1000.0, False

    # 2. Exact word match
    if q_token in target_words:
        return 800.0, False

    # 3. Word Prefix Match
    for word in target_words:
        if word.startswith(q_token):
            # Give higher score if token covers a larger portion of the word
            prefix_ratio = len(q_token) / len(word)
            return 500.0 + (prefix_ratio * 100.0), False

    # 4. Partial Substring Match
    if q_token in full_target_str:
        return 300.0, False

    # 5. Fuzzy Match (Damerau-Levenshtein)
    max_dist = get_allowed_max_distance(len(q_token))
    if max_dist == 0:
        return 0.0, False

    best_fuzzy_score = 0.0
    for word in target_words:
        # Optimization: skip words with large length differences
        if abs(len(word) - len(q_token)) > max_dist:
            continue

        dist = damerau_levenshtein_distance(q_token, word)
        if dist <= max_dist:
            # Score formula based on edit distance and word length
            similarity = 1.0 - (dist / max(len(q_token), len(word)))
            fuzzy_score = 100.0 + (similarity * 100.0)
            if fuzzy_score > best_fuzzy_score:
                best_fuzzy_score = fuzzy_score

    if best_fuzzy_score > 0:
        return best_fuzzy_score, True

    return 0.0, False


def fuzzy_filter_and_rank(queryset, query_str: str, searchable_fields: List[str]) -> Tuple[List[Any], bool]:
    """
    Filters and ranks a Django QuerySet using intelligent typo-tolerant search across specified fields.
    
    Returns:
        Tuple[List[obj], is_fuzzy_match]:
        - List of objects sorted by relevance (highest relevance first).
        - Boolean flag indicating whether fuzzy matching was required (no exact/prefix match found).
    """
    norm_query = normalize_text(query_str)
    if not norm_query:
        return list(queryset), False

    query_tokens = norm_query.split(" ")
    
    scored_items = []
    has_any_exact_or_prefix = False

    for obj in queryset:
        # Extract target field values
        field_values = []
        for field in searchable_fields:
            val = getattr(obj, field, "")
            if val:
                field_values.append(str(val))
        
        combined_text = normalize_text(" ".join(field_values))
        if not combined_text:
            continue
        
        target_words = combined_text.split(" ")

        # All query tokens must match at least one field/word
        total_score = 0.0
        obj_has_fuzzy = False
        all_tokens_matched = True

        for token in query_tokens:
            token_score, is_fuzzy = score_token_match(token, target_words, combined_text)
            if token_score == 0.0:
                all_tokens_matched = False
                break
            
            total_score += token_score
            if is_fuzzy:
                obj_has_fuzzy = True

        if all_tokens_matched:
            if not obj_has_fuzzy:
                has_any_exact_or_prefix = True
            scored_items.append((total_score, obj, obj_has_fuzzy))

    # Sort items by relevance score descending
    scored_items.sort(key=lambda x: x[0], reverse=True)
    
    result_objects = [item[1] for item in scored_items]
    is_fuzzy_result = len(result_objects) > 0 and not has_any_exact_or_prefix

    return result_objects, is_fuzzy_result
