#!/usr/bin/env python
import numpy as np

# stocks = ['RUSL', 'BRZU', 'CHAU', 'NUGT']
# years = [2014, 2015]
# cash = [10000]
# buy_roc = np.arange(0.05, 0.41, 0.05)
# sell_roc = np.arange(0.05, 0.41, 0.05)
# buy_target = np.arange(0.2, 1.01, 0.2)
# sell_target = np.arange(0.2, 1.01, 0.2)

# stocks = ['SOXL', 'TECL', 'BIB', 'CURE', 'DRN']
# years = [2014, 2015]
# cash = [10000]
# buy_roc = np.arange(0.05, 0.41, 0.05)
# sell_roc = np.arange(0.05, 0.41, 0.05)
# buy_target = np.arange(0.2, 0.81, 0.2)
# sell_target = np.arange(0.2, 0.81, 0.2)

# stocks = ['SOXL', 'TECL', 'BIB', 'CURE', 'DRN']
# years = [2014, 2015]
# quarters = [1, 2, 3, 4]
# cash = [10000]
# buy_roc = np.arange(0.05, 0.46, 0.05)
# sell_roc = np.arange(0.05, 0.46, 0.05)
# buy_target = np.arange(0.2, 1.1, 0.2)
# sell_target = np.arange(0.2, 1.1, 0.2)
#
# for s in stocks:
#     for y in years:
#         for q in quarters:
#             for c in cash:
#                 for br in buy_roc:
#                     for sr in sell_roc:
#                         for bt in buy_target:
#                             for st in sell_target:
#                                 print("python roc_quarterly.py %s %d-%d %d %f %f %f %f" % (s, y, q, c, br, sr, bt, st))

# # stocks = ['SOXL', 'TECL', 'BIB', 'CURE', 'DRN']
# # stocks = ['RUSL', 'BRZU', 'CHAU', 'NUGT']
# stocks = ['SOXL', 'TECL', 'BIB', 'CURE', 'DRN', 'RUSL', 'BRZU', 'NUGT']
# years = [2014, 2015]
# quarters = [1, 2, 3, 4]
# cash = [10000]
# rate = np.arange(0.1, 1.01, 0.1)
# for s in stocks:
#     for y in years:
#         for q in quarters:
#             for c in cash:
#                 for r in rate:
#                     print("python roc_quarterly.py %s %d-%d %d %f" % (s, y, q, c, r))

stocks = ['SOXL', 'TECL', 'BIB', 'CURE', 'DRN', 'RUSL', 'BRZU', 'NUGT']
years = [2014, 2015]
quarters = [1, 2, 3, 4]
cash = [10000]
buy_roc = np.arange(0.1, 0.46, 0.15)
sell_roc = np.arange(0.1, 0.46, 0.15)
buy_target = np.arange(0.25, 0.76, 0.25)
sell_target = np.arange(0.25, 0.76, 0.25)

for s in stocks:
    for y in years:
        for q in quarters:
            for c in cash:
                for br in buy_roc:
                    for sr in sell_roc:
                        for bt in buy_target:
                            for st in sell_target:
                                print("python roc_quarterly.py %s %d-%d %d %.2f %.2f %.2f %.2f" % (s, y, q, c, br, sr, bt, st))
