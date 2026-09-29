
def sort_list(items):
    if len(items) <= 1:
        return items
    p    = items[len(items) // 2]
    lo   = [x for x in items if x < p]
    same = [x for x in items if x == p]
    hi   = [x for x in items if x > p]
    return sort_list(lo) + same + sort_list(hi)
