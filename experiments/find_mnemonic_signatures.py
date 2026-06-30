import os
import glob
from collections import Counter
import re

def analyze_curve_mnemonics(las_dir):
    files = glob.glob(os.path.join(las_dir, "*.las"))
    
    mnemonic_sets = []
    
    for f in files:
        with open(f, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            
            curve_block = re.search(r'~C.*?(?=~[A-Z])', content, re.DOTALL)
            if not curve_block:
                continue
                
            lines = curve_block.group(0).strip().split('\n')[1:] # Skip ~C line
            
            mnemonics = []
            for line in lines:
                if line.startswith('#'): continue
                if not line.strip(): continue
                # Mnemonic is the first word before the dot
                mnemonic = line.split('.')[0].strip()
                mnemonics.append(mnemonic)
                
            # Filter out DEPT/DEPTH
            mnemonics = [m for m in mnemonics if m not in ('DEPT', 'DEPTH')]
            
            mnemonic_sets.append({
                'file': os.path.basename(f),
                'mnemonics': tuple(sorted(mnemonics))
            })

    print(f"Total files: {len(files)}")
    
    set_counter = Counter([r['mnemonics'] for r in mnemonic_sets])
    print("\n--- Mnemonic Combinations ---")
    for k, v in set_counter.most_common(20): 
        print(f"{v} files: {k}")
        
    # Are there any mnemonics that only appear in a subset of ~200 or ~65 files?
    all_mnemonics = Counter()
    for r in mnemonic_sets:
        for m in r['mnemonics']:
            all_mnemonics[m] += 1
            
    print("\n--- Individual Mnemonic Frequencies ---")
    for k, v in all_mnemonics.most_common(50):
        print(f"{k}: {v} files")

if __name__ == "__main__":
    analyze_curve_mnemonics("data/raw_las")
