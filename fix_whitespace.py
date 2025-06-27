#!/usr/bin/env python3

def fix_whitespace(filename):
    """Fix whitespace issues in Python file"""
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix trailing whitespace and empty lines with whitespace
    fixed_lines = []
    for line in lines:
        # Remove trailing whitespace
        fixed_line = line.rstrip() + '\n'
        fixed_lines.append(fixed_line)
    
    # Remove final newline if it was added to the last line
    if fixed_lines and fixed_lines[-1] == '\n':
        fixed_lines[-1] = fixed_lines[-1].rstrip('\n')
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print(f"Fixed whitespace in {filename}")

if __name__ == "__main__":
    fix_whitespace("debate_moderator_agent.py")
    fix_whitespace("debate_philosopher_agent.py") 