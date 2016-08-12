from isoweek import Week

# The first version of the year (just for pretty print)
first_version = 52

# Current year
current_year = 2017

# Constraints

# First week
first_week = 4

# Allowed cycles
allowed_cycles = [6, 7, 8]

# Work weeks
# week => [ [allowed_duration...], +/-i, +/-j, ... ]
# allowed_duration is the number of weeks with the previous release
#    if allowed_duration is 0 then the duration doesn't matter
# +/-i is the allowed week after/before the ww
# For example: 24: [[7, 8], -1, -2]
#   we want a release in 23 or 22 and the diff with the previous one must be 7 or 8 weeks
#
constraints = {26: [[7, 8], -1, -2],  # ww in SF
               50: [[7, 8], -1, -2],  # ww in Cancun
#               45: [[7, 8], +1],  # Mozilla's birthday
#               12: [[0], +1, +2], # pwn2own
}

# Other kind of constraint: no release during these weeks
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
        # check all the allowed possibilities (+1, +2, ...)
        for possibility in possibilities:
            w = k + possibility
            if w in cycle:
                i = cycle.index(w)
                # check if the duration between this release and the previous one is allowed (first parameter in constraint)
                if len_cycle != [0] and ((i + 1 < len(cycle) and cycle[i + 1] - w not in len_cycle) or (i - 1 >= 0 and w - cycle[i - 1] not in len_cycle)):
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

# Pretty print of the results (if any)
n = 1
for cycle in good_cycles:
    print 'Possibility ' + str(n) + ':'
    numbers = {6:0, 7:0, 8:0}
    n += 1
    v = first_version
    for i in range(0, len(cycle)):
        c = cycle[i]
        if c > 52:
            c = c - 52
            w = Week(current_year + 1, c)
        else:
            w = Week(current_year, c)
        tue = str(w.tuesday())
        j = tue.rfind('-')
        ym = tue[0:j]
        if i == 0:
            print '%s - %s (W %s), %s' % (v, ym, c, w.tuesday())
        else:
            d = cycle[i] - cycle[i - 1]
            print '%s - %s (W %s), %s (%s weeks cycle)' % (v, ym, c, w.tuesday(), d)
            numbers[d] = numbers[d] + 1
        v += 1
    print "Number of different length cycles: " + str(numbers)
    print ''
