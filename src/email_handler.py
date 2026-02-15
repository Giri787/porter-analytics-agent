"""
Email Handler Module
Handles fetching Porter data Excel files from Gmail and sending analysis reports.
"""

import os.path
import base64
from typing import Optional, List
import logging
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import mimetypes

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]

logger = logging.getLogger(__name__)

class EmailHandler:
    """Handles email operations using Gmail API (OAuth2)."""
    
    def __init__(self, config: dict):
        self.config = config
        self.creds = None
        self.service = None
        self.sender_filter = config.get('EMAIL_SENDER_FILTER')
        self.subject_filter = config.get('EMAIL_SUBJECT_FILTER')
        self._authenticate()
        
    def _authenticate(self):
        """Authenticate using OAuth2 credentials."""
        try:
            # The file token.json stores the user's access and refresh tokens
            if os.path.exists('token.json'):
                self.creds = Credentials.from_authorized_user_file('token.json', SCOPES)
                
            # If there are no (valid) credentials available, let the user log in.
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    if not os.path.exists('credentials.json'):
                        raise FileNotFoundError(
                            "credentials.json not found! Please download it from Google Cloud Console."
                        )
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'credentials.json', SCOPES)
                    self.creds = flow.run_local_server(port=0)
                    
                # Save the credentials for the next run
                with open('token.json', 'w') as token:
                    token.write(self.creds.to_json())
            
            self.service = build('gmail', 'v1', credentials=self.creds)
            logger.info("Successfully authenticated with Gmail API")
            
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise

    def fetch_latest_report(self, save_dir: str) -> Optional[str]:
        """Fetch latest report attachment using Gmail API."""
        try:
            logger.info("Searching for emails...")
            
            # The user provided subject: "3W - EV daily report - Dated:15-02-2026"
            # We search for the base part of the subject to find the most recent one.
            search_subject = self.subject_filter if self.subject_filter else "3W - EV daily report"
            query = f"from:{self.sender_filter} subject:\"{search_subject}\""
            
            if self.config.get('ONLY_UNREAD', 'true').lower() == 'true':
                query += " is:unread"
            
            logger.debug(f"Gmail query: {query}")
            
            results = self.service.users().messages().list(userId='me', q=query, maxResults=5).execute()
            messages = results.get('messages', [])

            if not messages:
                logger.warning(f"No matching emails found for query: {query}")
                return None

            # Get the most recent message
            msg_id = messages[0]['id']
            message = self.service.users().messages().get(userId='me', id=msg_id).execute()
            
            logger.info(f"Processing email: {message['snippet'][:50]}...")

            # Get attachments
            file_path = None
            if 'parts' in message['payload']:
                for part in message['payload']['parts']:
                    if part['filename']:
                        filename = part['filename']
                        ext = os.path.splitext(filename)[1].lower()
                        
                        if ext in ['.xlsx', '.xls', '.csv']:
                            if 'data' in part['body']:
                                data = part['body']['data']
                            else:
                                att_id = part['body']['attachmentId']
                                att = self.service.users().messages().attachments().get(
                                    userId='me', messageId=msg_id, id=att_id).execute()
                                data = att['data']
                            
                            file_data = base64.urlsafe_b64decode(data.encode('UTF-8'))
                            
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            safe_filename = f"porter_data_{timestamp}{ext}"
                            file_path = os.path.join(save_dir, safe_filename)

                            with open(file_path, 'wb') as f:
                                f.write(file_data)
                                
                            logger.info(f"Downloaded file: {file_path}")
                            break
            
            # Mark as read
            if file_path and self.config.get('MARK_AS_READ', 'true').lower() == 'true':
                self.service.users().messages().modify(
                    userId='me', id=msg_id, 
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
                logger.info("Marked email as read")
                
            return file_path

        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            return None

    def send_report(self, recipients: List[str], subject: str, html_content: str, 
                   attachments: Optional[List[str]] = None, from_name: str = None) -> bool:
        """Send email report using Gmail API."""
        try:
            message = MIMEMultipart()
            message['to'] = ", ".join(recipients)
            message['subject'] = subject

            msg = MIMEText(html_content, 'html')
            message.attach(msg)

            if attachments:
                for filepath in attachments:
                    if os.path.exists(filepath):
                        content_type, encoding = mimetypes.guess_type(filepath)
                        if content_type is None or encoding is not None:
                            content_type = 'application/octet-stream'
                        
                        main_type, sub_type = content_type.split('/', 1)
                        
                        with open(filepath, 'rb') as f:
                            part = MIMEBase(main_type, sub_type)
                            part.set_payload(f.read())
                        
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', 
                                      f'attachment; filename="{os.path.basename(filepath)}"')
                        message.attach(part)

            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            create_message = {'raw': raw_message}

            self.service.users().messages().send(userId='me', body=create_message).execute()
            logger.info(f"Report sent to {len(recipients)} recipients")
            return True

        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            return False
