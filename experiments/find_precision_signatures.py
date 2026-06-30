import os
import glob
from collections import Counter
import re

def analyze_data_precision(las_dir):
    files = glob.glob(os.path.join(las_dir, "*.las"))
    
    results = []
    
    for f in files:
        with open(f, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            
            # Find the start of the data block
            data_start = content.find('~A')
            if data_start == -1:
                continue
                
            data_block = content[data_start+2:].strip().split('\n')
            
            # Take a sample of 100 rows to determine precision profile
            sample_rows = data_block[:100]
            
            decimal_lengths = set()
            has_trailing_zeros = False
            
            for row in sample_rows:
                vals = row.split()
                for val in vals:
                    if val == '-999.2500' or val == '-999.25':
                        continue
                    if '.' in val:
                        decimals = val.split('.')[1]
                        decimal_lengths.add(len(decimals))
                        if len(decimals) > 1 and decimals.endswith('00'):
                            has_trailing_zeros = True
                            
            # Convert set to sorted tuple for grouping
            dec_profile = tuple(sorted(list(decimal_lengths)))
            
            results.append({
                'file': os.path.basename(f),
                'profile': dec_profile,
                'trailing_zeros': has_trailing_zeros
            })

    print(f"Total files: {len(files)}")
    
    profile_counter = Counter([r['profile'] for r in results])
    print("\n--- Decimal Precision Profiles ---")
    for k, v in profile_counter.most_common(10): 
        print(f"{k}: {v} files")
        
    tz_counter = Counter([r['trailing_zeros'] for r in results])
    print("\n--- Trailing Zeros ---")
    for k, v in tz_counter.most_common(): 
        print(f"{k}: {v} files")

if __name__ == "__main__":
    analyze_data_precision("data/raw_las")
