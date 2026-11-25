import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.dirname(__file__))

import test_calculation_regression
import test_audit_15
import test_rag_cycle
import test_streamlit_syntax
import test_final_release_audit_15

suite = unittest.TestSuite()
for mod in [test_calculation_regression, test_audit_15, test_rag_cycle, test_streamlit_syntax, test_final_release_audit_15]:
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(mod))

runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=2)
result = runner.run(suite)
print('\n================ SUMMARY ================')
print('Tests run:', result.testsRun)
print('Failures:', len(result.failures))
for f in result.failures:
    print('FAIL IN:', f[0])
    print(f[1])
print('Errors:', len(result.errors))
for e in result.errors:
    print('ERROR IN:', e[0])
    print(e[1])
if result.wasSuccessful():
    print('ALL RUN TESTS PASSED SUCCESSFULLY!')

