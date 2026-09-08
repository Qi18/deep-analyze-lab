"""Offline correctness and safety checks for repair gates."""
import importlib.util, sys, unittest
from pathlib import Path
SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPTS))
from repair_dev import cases,score,FENCE,RestrictedPython
from run_repair import regression,qualifies
class RepairTests(unittest.TestCase):
    def test_references(self):
        self.assertEqual(len(cases()),32)
        self.assertEqual(len({c["id"] for c in cases()}),32)
        for c in cases():
            with self.subTest(case=c["id"]):
                self.assertTrue(score(c,FENCE+"python\n"+c["reference"]+"\n"+FENCE)["passed"])
    def test_hidden_input(self):
        c=cases()[0]
        text=FENCE+"python\nresult = "+repr(c["checks"][0]["expected"])+"\n"+FENCE
        self.assertFalse(score(c,text)["passed"])
    def test_missing_code(self):
        self.assertEqual(score(cases()[0],"Analysis only")["error"],"missing_code")
    def test_no_arbitrary_execution(self):
        payloads=["import os\nresult = os.getcwd()","result = open('/etc/passwd').read()",
                  "result = (1).__class__.__base__.__subclasses__()",
                  "result = eval('1+1')","while True:\n pass","result = [0]*1000000000",
                  "result = list(range(1000000000))","result = 2**10000000"]
        for code in payloads:
            with self.subTest(code=code):
                with self.assertRaises(Exception):RestrictedPython({}).run(code)
    def test_loops(self):
        self.assertEqual(RestrictedPython({"values":[2,3]}).run("result=0\nfor x in values:\n result += x"),5)
    def test_gate(self):
        base=dict(passed=31,has_code=31,ended=31,repetitive=1)
        self.assertTrue(qualifies(base,base))
        self.assertFalse(qualifies(base,dict(base,passed=30)))
        self.assertEqual(regression(base,dict(base,passed=23)),(True,True))
        self.assertEqual(regression(base,dict(base,passed=27)),(False,True))
        self.assertEqual(regression(base,base),(False,False))
if __name__=="__main__":unittest.main()
