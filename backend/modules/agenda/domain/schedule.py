def validate_shift(day, starts, ends, valid_from, valid_until, breaks):
    if starts >= ends:
        return {'ends': 'El turno debe terminar el mismo día después de su inicio.'}
    if valid_until < valid_from:
        return {'valid_until': 'La vigencia final debe ser igual o posterior a la inicial.'}
    previous_end = starts
    for start, end in sorted(breaks):
        if not previous_end <= start < end <= ends:
            return {'breaks': 'Las pausas deben estar dentro del turno y no solaparse.'}
        previous_end = end
    return {}


def shifts_overlap(first, second):
    if first.day != second.day or max(first.starts, second.starts) >= min(first.ends, second.ends):
        return False
    start = max(first.valid_from, second.valid_from)
    offset = (first.day - start.weekday()) % 7
    return offset <= (min(first.valid_until, second.valid_until) - start).days


def subtract(start, end, blocks):
    cursor = start
    for left, right in sorted(blocks):
        if right <= cursor:
            continue
        if left >= end:
            break
        if left > cursor:
            yield cursor, left
        cursor = max(cursor, right)
        if cursor >= end:
            return
    if cursor < end:
        yield cursor, end
