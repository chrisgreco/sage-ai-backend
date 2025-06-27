#!/usr/bin/env python3

def fix_indentation_issues():
    """Fix E128 indentation issues in debate agent files"""
    
    # Fix moderator agent
    with open('debate_moderator_agent.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the specific indentation issues
    content = content.replace(
        '        "dominating_speaker": ("Try: \'Thank you [Name]. Let\'s hear from someone who hasn\'t "\n'
        '                              "spoken yet on this point.\'"),',
        '        "dominating_speaker": ("Try: \'Thank you [Name]. Let\'s hear from someone who hasn\'t "\n'
        '                               "spoken yet on this point.\'"),'
    )
    
    content = content.replace(
        '        "off_topic": ("Try: \'That\'s an interesting point. How does it connect to our main "\n'
        '                     "question about [topic]?\'")',
        '        "off_topic": ("Try: \'That\'s an interesting point. How does it connect to our main "\n'
        '                      "question about [topic]?\'"),'
    )
    
    content = content.replace(
        '        "personal_attack": ("Try: \'Let\'s focus on the ideas rather than personal "\n'
        '                           "characterizations. What specifically about that position concerns you?\'")',
        '        "personal_attack": ("Try: \'Let\'s focus on the ideas rather than personal "\n'
        '                            "characterizations. What specifically about that position concerns you?\'")'
    )
    
    content = content.replace(
        '        "confusion": ("Try: \'Let me see if I can summarize what I\'m hearing... "\n'
        '                     "Does that capture the key points?\'")',
        '        "confusion": ("Try: \'Let me see if I can summarize what I\'m hearing... "\n'
        '                      "Does that capture the key points?\'")'
    )
    
    content = content.replace(
        '        "polarization": ("Try: \'I\'m hearing some different values here. Are there any shared "\n'
        '                        "concerns we might build on?\'")',
        '        "polarization": ("Try: \'I\'m hearing some different values here. Are there any shared "\n'
        '                         "concerns we might build on?\'")'
    )
    
    with open('debate_moderator_agent.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Fixed indentation issues in debate_moderator_agent.py")

if __name__ == "__main__":
    fix_indentation_issues() 