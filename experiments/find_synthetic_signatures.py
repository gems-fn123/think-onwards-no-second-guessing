import os
import glob
from collections import Counter
import re

def analyze_las_headers(las_dir):
    files = glob.glob(os.path.join(las_dir, "*.las"))
    
    comp_counter = Counter()
    srvc_counter = Counter()
    date_counter = Counter()
    null_counter = Counter()
    
    results = []
    
    for f in files:
        with open(f, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            
            # Extract header values
            comp_match = re.search(r'^COMP\.\s+([^:]+)', content, re.MULTILINE)
            srvc_match = re.search(r'^SRVC\.\s+([^:]+)', content, re.MULTILINE)
            date_match = re.search(r'^DATE\.\s+([^:]+)', content, re.MULTILINE)
            null_match = re.search(r'^NULL\.\s+([^:]+)', content, re.MULTILINE)
            
            comp = comp_match.group(1).strip() if comp_match else "MISSING"
            srvc = srvc_match.group(1).strip() if srvc_match else "MISSING"
            date = date_match.group(1).strip() if date_match else "MISSING"
            null_val = null_match.group(1).strip() if null_match else "MISSING"
            
            comp_counter[comp] += 1
            srvc_counter[srvc] += 1
            date_counter[date] += 1
            null_counter[null_val] += 1
            
            # Count block lengths
            param_block = re.search(r'~P.*?(?=~[A-Z])', content, re.DOTALL)
            other_block = re.search(r'~O.*?(?=~[A-Z])', content, re.DOTALL)
            
            p_len = len(param_block.group(0).strip().split('\n')) if param_block else 0
            o_len = len(other_block.group(0).strip().split('\n')) if other_block else 0
            
            results.append({
                'file': os.path.basename(f),
                'comp': comp,
                'srvc': srvc,
                'date': date,
                'null': null_val,
                'p_len': p_len,
                'o_len': o_len
            })

    print(f"Total files: {len(files)}")
    print("\n--- COMP ---")
    for k, v in comp_counter.most_common(10): print(f"{k}: {v}")
    print("\n--- SRVC ---")
    for k, v in srvc_counter.most_common(10): print(f"{k}: {v}")
    print("\n--- DATE ---")
    for k, v in date_counter.most_common(10): print(f"{k}: {v}")
    print("\n--- NULL ---")
    for k, v in null_counter.most_common(10): print(f"{k}: {v}")
    
    # Check for clusters of size ~200 or ~65
    p_len_counter = Counter([r['p_len'] for r in results])
    o_len_counter = Counter([r['o_len'] for r in results])
    
    print("\n--- Parameter Block Lines ---")
    for k, v in p_len_counter.most_common(10): print(f"{k} lines: {v} files")
    
    print("\n--- Other Block Lines ---")
    for k, v in o_len_counter.most_common(10): print(f"{k} lines: {v} files")

if __name__ == "__main__":
    analyze_las_headers("data/raw_las")
