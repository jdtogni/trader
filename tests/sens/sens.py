from SALib.sample import saltelli
from SALib.analyze import sobol
from SALib.test_functions import Ishigami
import numpy as np

# buy_roc = np.arange(0.05, 0.41, 0.05)
# sell_roc = np.arange(0.05, 0.41, 0.05)
# buy_target = np.arange(0.2, 1.01, 0.2)
# sell_target = np.arange(0.2, 1.01, 0.2)

# Define the model inputs
problem = {
    'num_vars': 4,
    'names': ['buy_roc', 'sell_roc', 'buy_target', 'sell_target'],
    'bounds': [[0.05, 0.4],
               [0.05, 0.4],
               [0.2, 1],
               [0.2, 1]]
}

# Generate samples
#param_values = saltelli.sample(problem, 1000, calc_second_order=True)
#np.savetxt("eodct_params.txt", param_values)

# Run model (example)
#Y = Ishigami.evaluate(param_values)
Y = np.loadtxt("eodct1_outputs.txt", float)

# Perform analysis
Si = sobol.analyze(problem, Y, print_to_console=False)

# Print the first-order sensitivity indices
print Si['S1']