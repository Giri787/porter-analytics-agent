"""
Diagnostic script for Gmail API search.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from email_handler import EmailHandler

def test_gmail_search():
    # Load config
    config_path = Path('config/.env')
    load_dotenv(config_path)
    
    config = {
        'EMAIL_SENDER_FILTER': os.getenv('EMAIL_SENDER_FILTER', 'datainfra@theporter.in'),
        'EMAIL_SUBJECT_FILTER': '3W - EV daily report',
        'ONLY_UNREAD': 'false', # Test with false first to see if we find anything
        'MARK_AS_READ': 'false'
    }
    
    print("="*60)
    print("Gmail Search Diagnostic")
    print("="*60)
    print(f"Sender Filter: {config['EMAIL_SENDER_FILTER']}")
    print(f"Subject Filter: {config['EMAIL_SUBJECT_FILTER']}")
    print()
    
    try:
        handler = EmailHandler(config)
        
        search_query = 'subject:"3W - EV daily report"'
        print(f"Searching for: {search_query}")
        
        results = handler.service.users().messages().list(userId='me', q=search_query, maxResults=50).execute()
        messages = results.get('messages', [])
        
        with open('debug_log.txt', 'w', encoding='utf-8') as log:
            if not messages:
                print("[WARNING] No messages found with that subject.")
                log.write(f"[WARNING] No messages found for query: {search_query}\n")
            else:
                print(f"[SUCCESS] Found {len(messages)} messages.")
                for i, msg in enumerate(messages[:10]): # Just show top 10
                    m = handler.service.users().messages().get(userId='me', id=msg['id']).execute()
                    subject = next((h['value'] for h in m['payload']['headers'] if h['name'].lower() == 'subject'), 'No Subject')
                    date_header = next((h['value'] for h in m['payload']['headers'] if h['name'].lower() == 'date'), 'No Date')
                    sender = next((h['value'] for h in m['payload']['headers'] if h['name'].lower() == 'from'), 'No Sender')
                    result = f"[{date_header}] From: {sender} | Subject: {subject}"
                    print(result)
                    log.write(result + "\n")
            
        print("[SUCCESS] Debug log written to debug_log.txt")
                
    except Exception as e:
        print(f"[ERROR] Error: {str(e)}")

if __name__ == "__main__":
    test_gmail_search()
