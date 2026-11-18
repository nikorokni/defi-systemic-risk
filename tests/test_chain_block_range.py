"""Pure, network-free tests for historical UTC block resolution."""
import importlib.util
from pathlib import Path
import unittest
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("chain_block_range",root/"revision/scripts/chain_block_range.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class BlockSearchTests(unittest.TestCase):
    def test_lower_bound(self):
        seq=[10,12,12,15,19,25,25,31]
        for value,expected in [(10,0),(12,1),(13,3),(25,5),(26,7),(32,8)]:
            self.assertEqual(m.first_block_at_or_after(value,7,lambda i:seq[i]),expected)
    def test_ethereum_timestamp_checks(self):
        s,e=m.timestamp("2024-08-01"),m.timestamp("2024-08-02")
        times=[s-5,s-1,s,s+1,e-1,e,e+1]
        original=m.rpc
        def fake(_,method,args):
            if method=="eth_chainId":return "0x1"
            if method=="eth_blockNumber":return hex(len(times)-1)
            if method=="eth_getBlockByNumber":
                idx=int(args[0],16)
                return {"number":hex(idx),"timestamp":hex(times[idx])}
            raise AssertionError(method)
        try:
            m.rpc=fake
            result=m.resolve("hidden","2024-08-01","2024-08-02")
            self.assertEqual((result["first_inclusive_block"],result["last_inclusive_block"]),(2,4))
        finally:m.rpc=original

if __name__=="__main__":unittest.main()
