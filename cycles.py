from isoweek import Week

# Constraints

# First week
first_week = 4
first_version = 44

# Allowed cycles
allowed_cycles = [6, 7, 8]

# Work weeks 
constraints = {24: [[7, 8], -1, -2], # ww in London
               49: [[7, 8], -1, -2], # ww in Hawaii
               45: [[7, 8], +1], # Mozilla's birthday
#               12: [[0], +1, +2], # pwn2own
}

forbidden_weeks = set([27, # Independance Day
                       47, # Thanksgiving
                       52, # Last week of the year
])

# We generate all the possibilities
cycles = [[first_week]]
for i in range(1, 9):
    nuple = []
    for c in cycles:
        last = c[-1]
        for i in range(len(allowed_cycles)):
            ac = allowed_cycles[i]
            # we accept only cycles where the total is less than 52
            if last + ac - first_week <= 52:
                nuple.append(c + [last + ac])
            else:
                if i == 0:
                    nuple.append(c)
            
    cycles = nuple

good_cycles = []

for cycle in cycles:
    # A cycle cannot contain a forbidden week
    if forbidden_weeks & set(cycle):
        continue

    cycle_ok = True
    for k, v in constraints.iteritems():
        len_cycle = v[0]
        possibilities = v[1:]
        ok = True
        for possibility in possibilities:
            w = k + possibility
            if w in cycle:
                i = cycle.index(w)
                if len_cycle != [0] and (cycle[i + 1] - w not in len_cycle or w - cycle[i - 1] not in len_cycle):
                    ok = False
                else:
                    ok = True
                    break
            else:
                ok = False

        if not ok:
            cycle_ok = False
            break

    if cycle_ok:
        good_cycles.append(cycle)

n = 1
for cycle in good_cycles:
    print 'Possibility ' + str(n) + ':'
    n += 1
    v = first_version
    for i in range(0, len(cycle)):
        c = cycle[i]
        if c > 52:
            c = c - 52
            w = Week(2017, c)
        else:
            w = Week(2016, c)
        tue = str(w.tuesday())
        j = tue.rfind('-')
        ym = tue[0:j]
        if i == 0:
            print '%s - %s (W %s), %s' % (v, ym, c, w.tuesday())
        else:
            d = cycle[i] - cycle[i - 1]
            print '%s - %s (W %s), %s (%s weeks cycle)' % (v, ym, c, w.tuesday(), d)
        v += 1
    print ''
