import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'runtime'))
from predict_field import predict_field
assert predict_field(600, 10, 100, 100, 20, 4)['validity'] == 'VALID'
assert predict_field(700, 10, 100, 100, 20, 4)['validity'] == 'OUT_OF_DOMAIN'
assert predict_field(600, 10, 4000, 100, 20, 4)['validity'] == 'OUT_OF_DOMAIN'
assert predict_field(600, 40, 100, 100, 20, 4)['validity'] == 'OUT_OF_DOMAIN'   # P>30
assert predict_field(600, 30, 100, 100, 25, 4)['validity'] == 'VALID'            # ss=187.5<=250
assert predict_field(600, 30, 100, 100, 25, 2)['validity'] == 'OUT_OF_DOMAIN'    # ss=375>250
assert predict_field(650, 30, 3000, 150, 25, 3)['validity'] == 'VALID'
print('test_input_validation PASS')
