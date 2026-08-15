# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

# Test the token matching
token = "r51600"
proc_num = "r5 1600"

proc_num_lower = proc_num.lower().replace(' ', '').replace('-', '')
print(f"Token: '{token}'")
print(f"Processor number (normalized): '{proc_num_lower}'")
print(f"In token: {proc_num_lower in token}")

if proc_num_lower in token:
    pos = token.find(proc_num_lower)
    proc_len = len(proc_num_lower)
    token_len = len(token)
    
    is_at_end = (pos + proc_len) == token_len
    has_non_digit_after = False
    if pos + proc_len < token_len:
        next_char = token[pos + proc_len]
        has_non_digit_after = not next_char.isdigit()
    
    print(f"Position: {pos}")
    print(f"Is at end: {is_at_end}")
    print(f"Has non-digit after: {has_non_digit_after}")
    print(f"Should match: {is_at_end or has_non_digit_after}")
