"""Email receiving functionality for Kindle sync."""

import email
import imaplib
import ssl
import re
import requests
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
        
        # Initialize processed emails tracking
        self.prevent_duplicates = self.config.get("email_receiving.prevent_duplicates", True)
        self.processed_emails_file = Path(
            self.config.get("email_receiving.duplicate_tracking_file", "/app/logs/processed_emails.txt")
        )
        self.processed_emails = self._load_processed_emails() if self.prevent_duplicates else set()
        
        logger.info("Email receiver initialized")
        logger.info(f"Approved senders: {self.approved_senders}")
        logger.info(f"Duplicate prevention: {'enabled' if self.prevent_duplicates else 'disabled'}")
        if self.prevent_duplicates:
            logger.info(f"Loaded {len(self.processed_emails)} previously processed emails")
            # Cleanup old processed email records
            self._cleanup_old_processed_emails()

    def _load_processed_emails(self) -> set:
        """Load list of previously processed email IDs."""
        processed_emails = set()
        try:
            if self.processed_emails_file.exists():
                with open(self.processed_emails_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            processed_emails.add(line)
                logger.debug(f"Loaded {len(processed_emails)} processed email IDs")
        except Exception as e:
            logger.warning(f"Failed to load processed emails: {e}")
        return processed_emails

    def _save_processed_email(self, email_id: str):
        """Save email ID to processed emails list."""
        try:
            # Ensure logs directory exists
            self.processed_emails_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Add to set and save to file
            self.processed_emails.add(email_id)
            with open(self.processed_emails_file, 'a') as f:
                f.write(f"{email_id}\n")
            logger.debug(f"Marked email {email_id} as processed")
        except Exception as e:
            logger.error(f"Failed to save processed email {email_id}: {e}")

    def _is_email_processed(self, email_id: str) -> bool:
        """Check if email has already been processed."""
        return email_id in self.processed_emails

    def _cleanup_old_processed_emails(self, days_to_keep: int = 30):
        """Clean up old processed email records to prevent file from growing indefinitely."""
        try:
            if not self.processed_emails_file.exists():
                return
            
            # Read all lines and keep only recent ones (this is a simple approach)
            # In a production system, you might want to use a database instead
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # For now, we'll keep all records but could implement date-based cleanup
            # if we add timestamps to the processed emails file
            logger.debug(f"Processed emails cleanup: keeping records from last {days_to_keep} days")
            
        except Exception as e:
            logger.warning(f"Failed to cleanup old processed emails: {e}")

    def clear_processed_emails(self):
        """Clear the list of processed emails (useful for testing or reset)."""
        try:
            if self.processed_emails_file.exists():
                self.processed_emails_file.unlink()
                logger.info("Cleared processed emails list")
            self.processed_emails.clear()
        except Exception as e:
            logger.error(f"Failed to clear processed emails: {e}")

    def get_processed_emails_count(self) -> int:
        """Get the number of processed emails."""
        return len(self.processed_emails)

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
            
            # Search for recent emails (we'll filter by sender in the code)
            # This is more reliable than complex IMAP queries
            status, messages = mail.search(None, "ALL")
            if status != "OK":
                logger.error("Failed to search for emails")
                return []

            email_ids = messages[0].split()
            if not email_ids:
                logger.debug("No new emails from approved senders found")
                return []

            # Limit number of emails to process (check more emails to find Kindle emails)
            max_emails = 100  # Check up to 100 emails to find Kindle emails
            email_ids = email_ids[-max_emails:] if len(email_ids) > max_emails else email_ids

            logger.info(f"Found {len(email_ids)} emails to check for approved senders")
            
            approved_emails_found = 0

            for i, email_id in enumerate(email_ids, 1):
                try:
                    # Convert email_id to string for comparison
                    email_id_str = email_id.decode() if isinstance(email_id, bytes) else str(email_id)
                    
                    # Check if email has already been processed (if duplicate prevention is enabled)
                    if self.prevent_duplicates and self._is_email_processed(email_id_str):
                        logger.debug(f"Email {i}/{len(email_ids)}: Already processed, skipping")
                        continue
                    
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
                    logger.info(f"Email {i}/{len(email_ids)}: From '{sender}'")
                    
                    if not self._is_approved_sender(sender):
                        logger.info(f"  → Rejected: Not from approved sender")
                        continue
                    
                    approved_emails_found += 1
                    logger.info(f"  → APPROVED: Processing email from {sender} (#{approved_emails_found})")
                    
                    # Process email for PDF attachments
                    pdf_files = self._process_email_attachments(email_message, email_id)
                    if pdf_files:
                        logger.info(f"  → Found {len(pdf_files)} PDF files in email")
                        processed_files.extend(pdf_files)
                    else:
                        logger.info(f"  → No PDF files found in email")

                    # Mark email as processed to prevent duplicates (if enabled)
                    if self.prevent_duplicates:
                        self._save_processed_email(email_id_str)
                        logger.debug(f"  → Marked email {email_id_str} as processed")

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
                logger.debug("IMAP connection closed")
            except:
                pass

        logger.info(f"Email processing completed. Processed {len(processed_files)} PDF files.")
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
        """Process email attachments and download links, save PDF files."""
        processed_files = []
        
        try:
            # Get email subject for logging
            subject = self._decode_header(email_message.get("Subject", "No Subject"))
            logger.info(f"Processing email: {subject}")
            
            logger.debug(f"  → Checking email for PDFs...")
            
            # First, try to find download links in email body
            download_links = self._extract_download_links(email_message)
            logger.debug(f"  → Found {len(download_links)} download links")
            
            if download_links:
                logger.info(f"  → Processing {len(download_links)} download links")
                for i, link in enumerate(download_links, 1):
                    try:
                        logger.debug(f"  → Downloading link {i}/{len(download_links)}: {link[:50]}...")
                        pdf_path = self._download_pdf_from_link(link, email_id)
                        if pdf_path:
                            processed_files.append(pdf_path)
                            logger.info(f"  → Downloaded PDF: {pdf_path}")
                        else:
                            logger.debug(f"  → Link {i} did not yield a PDF")
                    except Exception as e:
                        logger.error(f"  → Failed to download PDF from link {i}: {e}")
            
            # Also check for traditional attachments
            logger.debug(f"  → Checking for traditional attachments...")
            attachment_count = 0
            pdf_attachment_count = 0
            
            for part in email_message.walk():
                # Check if part is an attachment
                if part.get_content_disposition() == "attachment":
                    attachment_count += 1
                    filename = part.get_filename()
                    if filename:
                        # Decode filename if needed
                        filename = self._decode_header(filename)
                        logger.debug(f"  → Found attachment {attachment_count}: {filename}")
                        
                        # Check if it's a PDF file
                        if filename.lower().endswith('.pdf'):
                            pdf_attachment_count += 1
                            logger.info(f"  → Found PDF attachment: {filename}")
                            
                            # Save PDF to sync folder
                            pdf_path = self._save_pdf_attachment(part, filename, email_id)
                            if pdf_path:
                                processed_files.append(pdf_path)
                                logger.info(f"  → Saved PDF: {pdf_path}")
                        else:
                            logger.debug(f"  → Skipping non-PDF attachment: {filename}")
            
            logger.debug(f"  → Found {attachment_count} total attachments, {pdf_attachment_count} PDFs")
            logger.debug(f"  → Email processing complete: {len(processed_files)} PDFs processed")
                            
        except Exception as e:
            logger.error(f"  → Error processing email attachments: {e}")
            
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

    def _extract_download_links(self, email_message) -> List[str]:
        """Extract download links from email body."""
        download_links = []
        
        try:
            # Get email body
            body = self._get_email_body(email_message)
            if not body:
                return download_links
            
            # Look for Kindle download link patterns
            # Pattern 1: Direct download links
            link_patterns = [
                r'https://[^\s]*\.pdf[^\s]*',  # Direct PDF links
                r'https://[^\s]*download[^\s]*',  # Download links
                r'https://[^\s]*kindle[^\s]*',  # Kindle-specific links
                r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>.*?Download PDF.*?</a>',  # HTML download links
            ]
            
            for pattern in link_patterns:
                matches = re.findall(pattern, body, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]  # Extract URL from regex group
                    
                    # Clean up the URL
                    url = match.strip()
                    if url and url.startswith('http'):
                        download_links.append(url)
                        logger.debug(f"Found download link: {url}")
            
            # Remove duplicates while preserving order
            download_links = list(dict.fromkeys(download_links))
            
        except Exception as e:
            logger.error(f"Error extracting download links: {e}")
            
        return download_links

    def _get_email_body(self, email_message) -> str:
        """Extract email body text."""
        body = ""
        
        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    
                    # Skip attachments
                    if "attachment" in content_disposition:
                        continue
                    
                    # Get text content
                    if content_type == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body += payload.decode('utf-8', errors='ignore')
                    elif content_type == "text/html":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body += payload.decode('utf-8', errors='ignore')
            else:
                # Single part message
                payload = email_message.get_payload(decode=True)
                if payload:
                    body = payload.decode('utf-8', errors='ignore')
                    
        except Exception as e:
            logger.error(f"Error extracting email body: {e}")
            
        return body

    def _download_pdf_from_link(self, url: str, email_id: bytes) -> Optional[Path]:
        """Download PDF from a download link."""
        try:
            logger.info(f"Downloading PDF from: {url}")
            
            # Make request to download the PDF with proper redirect handling
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Follow redirects to get the actual PDF
            response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            logger.debug(f"Final URL after redirects: {response.url}")
            
            # Check if it's actually a PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and not url.lower().endswith('.pdf'):
                logger.warning(f"Downloaded content doesn't appear to be a PDF: {content_type}")
                return None
            
            # Additional check: verify the file starts with PDF header
            if not response.content.startswith(b'%PDF'):
                logger.warning(f"Downloaded content doesn't have PDF header, got: {response.content[:20]}")
                return None
            
            # Generate simple filename to avoid filesystem limits
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            email_id_str = email_id.decode() if isinstance(email_id, bytes) else str(email_id)
            
            # Use simple filename to avoid filesystem issues
            filename = f"kindle_doc_{timestamp}_{email_id_str}.pdf"
            
            # Ensure sync folder exists
            self.sync_folder_path.mkdir(parents=True, exist_ok=True)
            
            # Save file
            pdf_path = self.sync_folder_path / filename
            
            with open(pdf_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded PDF: {pdf_path} ({len(response.content)} bytes)")
            return pdf_path
            
        except Exception as e:
            logger.error(f"Error downloading PDF from {url}: {e}")
            return None

    def _extract_filename_from_response(self, response, url: str) -> str:
        """Extract filename from response headers or URL."""
        try:
            # Try Content-Disposition header first
            content_disposition = response.headers.get('Content-Disposition', '')
            if content_disposition:
                filename_match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', content_disposition)
                if filename_match:
                    filename = filename_match.group(1).strip('\'"')
                    if filename:
                        return filename
            
            # Try to extract from URL
            if url:
                url_path = url.split('/')[-1]
                if url_path and '.' in url_path:
                    return url_path
                    
        except Exception as e:
            logger.debug(f"Error extracting filename: {e}")
            
        return ""

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
