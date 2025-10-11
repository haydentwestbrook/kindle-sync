"""Email receiving functionality for Kindle sync."""

import email
import imaplib
import ssl
from email.header import decode_header
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime, timedelta

from loguru import logger

from .config import Config


class EmailReceiver:
    """Handle receiving emails from Kindle with PDF attachments."""

    def __init__(self, config: Config):
        """Initialize email receiver."""
        self.config = config
        self.imap_config = self.get_imap_config()
        self.approved_senders = config.get_approved_senders()
        self.sync_folder_path = config.get_sync_folder_path()
        
        logger.info("Email receiver initialized")

    def get_imap_config(self) -> dict:
        """Get IMAP configuration from config."""
        return {
            "server": self.config.get("email_receiving.imap_server", ""),
            "port": self.config.get("email_receiving.imap_port", 993),
            "username": self.config.get("email_receiving.username", ""),
            "password": self.config.get("email_receiving.password", ""),
            "check_interval": self.config.get("email_receiving.check_interval", 300),
            "max_emails": self.config.get("email_receiving.max_emails_per_check", 10),
            "mark_as_read": self.config.get("email_receiving.mark_as_read", True),
            "delete_after": self.config.get("email_receiving.delete_after_processing", False),
        }

    def is_enabled(self) -> bool:
        """Check if email receiving is enabled."""
        return self.config.get("email_receiving.enabled", False)

    def connect_to_imap(self) -> Optional[imaplib.IMAP4_SSL]:
        """Connect to IMAP server."""
        try:
            # Create SSL context
            context = ssl.create_default_context()
            
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(
                self.imap_config["server"], 
                self.imap_config["port"],
                ssl_context=context
            )
            
            # Login
            mail.login(self.imap_config["username"], self.imap_config["password"])
            
            logger.info("Connected to IMAP server successfully")
            return mail
            
        except Exception as e:
            logger.error(f"Failed to connect to IMAP server: {e}")
            return None

    def check_for_new_emails(self) -> List[Path]:
        """Check for new emails with PDF attachments from approved senders."""
        if not self.is_enabled():
            logger.debug("Email receiving is disabled")
            return []

        mail = self.connect_to_imap()
        if not mail:
            return []

        processed_files = []
        
        try:
            # Select inbox
            mail.select("INBOX")
            
            # Search for unread emails
            status, messages = mail.search(None, "UNSEEN")
            if status != "OK":
                logger.error("Failed to search for emails")
                return []

            email_ids = messages[0].split()
            if not email_ids:
                logger.debug("No new emails found")
                return []

            # Limit number of emails to process
            max_emails = self.imap_config["max_emails"]
            email_ids = email_ids[-max_emails:] if len(email_ids) > max_emails else email_ids

            logger.info(f"Found {len(email_ids)} new emails to process")

            for email_id in email_ids:
                try:
                    # Fetch email
                    status, msg_data = mail.fetch(email_id, "(RFC822)")
                    if status != "OK":
                        logger.warning(f"Failed to fetch email {email_id}")
                        continue

                    # Parse email
                    email_body = msg_data[0][1]
                    email_message = email.message_from_bytes(email_body)
                    
                    # Check if email is from approved sender
                    sender = self._get_sender_email(email_message)
                    if not self._is_approved_sender(sender):
                        logger.debug(f"Email from {sender} is not from approved sender")
                        continue

                    # Process email for PDF attachments
                    pdf_files = self._process_email_attachments(email_message, email_id)
                    processed_files.extend(pdf_files)

                    # Mark as read if configured
                    if self.imap_config["mark_as_read"]:
                        mail.store(email_id, "+FLAGS", "\\Seen")

                    # Delete if configured (not recommended for safety)
                    if self.imap_config["delete_after"]:
                        mail.store(email_id, "+FLAGS", "\\Deleted")

                except Exception as e:
                    logger.error(f"Error processing email {email_id}: {e}")
                    continue

            # Expunge deleted emails if any were marked for deletion
            if self.imap_config["delete_after"]:
                mail.expunge()

        except Exception as e:
            logger.error(f"Error during email processing: {e}")
        finally:
            try:
                mail.close()
                mail.logout()
            except:
                pass

        return processed_files

    def _get_sender_email(self, email_message) -> str:
        """Extract sender email address from email message."""
        try:
            sender = email_message.get("From", "")
            if "<" in sender and ">" in sender:
                # Extract email from "Name <email@domain.com>" format
                start = sender.find("<") + 1
                end = sender.find(">")
                return sender[start:end].strip()
            return sender.strip()
        except Exception as e:
            logger.error(f"Error extracting sender email: {e}")
            return ""

    def _is_approved_sender(self, sender: str) -> bool:
        """Check if sender is in approved senders list."""
        if not sender:
            return False
        
        # Check if sender matches any approved sender
        for approved_sender in self.approved_senders:
            if sender.lower() == approved_sender.lower():
                return True
        
        # Check if sender is from Kindle domain (for Kindle-generated emails)
        if "@kindle.com" in sender.lower() or "@kindle." in sender.lower():
            return True
            
        return False

    def _process_email_attachments(self, email_message, email_id: bytes) -> List[Path]:
        """Process email attachments and save PDF files."""
        processed_files = []
        
        try:
            # Get email subject for logging
            subject = self._decode_header(email_message.get("Subject", "No Subject"))
            logger.info(f"Processing email: {subject}")
            
            # Walk through email parts
            for part in email_message.walk():
                # Check if part is an attachment
                if part.get_content_disposition() == "attachment":
                    filename = part.get_filename()
                    if filename:
                        # Decode filename if needed
                        filename = self._decode_header(filename)
                        
                        # Check if it's a PDF file
                        if filename.lower().endswith('.pdf'):
                            logger.info(f"Found PDF attachment: {filename}")
                            
                            # Save PDF to sync folder
                            pdf_path = self._save_pdf_attachment(part, filename, email_id)
                            if pdf_path:
                                processed_files.append(pdf_path)
                                logger.info(f"Saved PDF: {pdf_path}")
                        else:
                            logger.debug(f"Skipping non-PDF attachment: {filename}")
                            
        except Exception as e:
            logger.error(f"Error processing email attachments: {e}")
            
        return processed_files

    def _decode_header(self, header_value: str) -> str:
        """Decode email header value."""
        try:
            if not header_value:
                return ""
                
            decoded_parts = decode_header(header_value)
            decoded_string = ""
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_string += part.decode(encoding)
                    else:
                        decoded_string += part.decode('utf-8', errors='ignore')
                else:
                    decoded_string += part
                    
            return decoded_string
        except Exception as e:
            logger.error(f"Error decoding header: {e}")
            return str(header_value)

    def _save_pdf_attachment(self, part, filename: str, email_id: bytes) -> Optional[Path]:
        """Save PDF attachment to sync folder."""
        try:
            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            email_id_str = email_id.decode() if isinstance(email_id, bytes) else str(email_id)
            base_name = Path(filename).stem
            extension = Path(filename).suffix
            
            # Create unique filename
            unique_filename = f"{base_name}_{timestamp}_{email_id_str}{extension}"
            
            # Ensure sync folder exists
            self.sync_folder_path.mkdir(parents=True, exist_ok=True)
            
            # Save file
            pdf_path = self.sync_folder_path / unique_filename
            
            with open(pdf_path, 'wb') as f:
                f.write(part.get_payload(decode=True))
            
            logger.info(f"Saved PDF attachment: {pdf_path}")
            return pdf_path
            
        except Exception as e:
            logger.error(f"Error saving PDF attachment: {e}")
            return None

    def start_polling(self, callback_func=None):
        """Start polling for new emails (for use in main application loop)."""
        if not self.is_enabled():
            logger.info("Email receiving is disabled, skipping email polling")
            return

        try:
            processed_files = self.check_for_new_emails()
            
            if processed_files:
                logger.info(f"Processed {len(processed_files)} PDF files from emails")
                
                # Call callback function if provided (e.g., to trigger file processing)
                if callback_func:
                    for pdf_path in processed_files:
                        callback_func(pdf_path)
            else:
                logger.debug("No new emails with PDF attachments found")
                
        except Exception as e:
            logger.error(f"Error during email polling: {e}")
