import logging
import email
import imaplib
from imapclient import IMAPClient
from os.path import join
import datetime as dt
from robot import PATH
from settings import SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, SEARCH_SUBJECT, DATE


def download_all_attachments(msg_data, path=PATH):
    """
    Download all files attached in message.
    """

    email_message = msg_data[b'RFC822']
            # Analiza el correo electrónico utilizando el módulo email
    message = email.message_from_bytes(email_message)
    # body = ""
    # raw_body = message.get_payload()
    # body = raw_body[0]._payload[0]._payload
    # body = body.replace('\r\n','')
    # fwo = body.split(': ')[-1]

    # Verifica si el correo tiene adjuntos
    if message.get_content_maintype() == 'multipart':
        for part in message.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue
            
            # Si el contenido es un adjunto, descárgalo
            if "attachment" in part.get('Content-Disposition'):
                if part.get_content_maintype() == 'application' or part.get_content_maintype() == 'text':
                    filename = part.get_filename().replace(': ', '_')
                    if filename:
                        with open(join(path,filename), 'wb') as f:
                            f.write(part.get_payload(decode=True))
                        logging.info(f"file downloaded: {filename}")
                        print(f"Archivo adjunto descargado: {filename}")


def connect_to_mailbox():
    """
    Stablish a connection with mailbox, search all messages with defined subject and download all files attached to message.
    """
    today = DATE

    with IMAPClient(SMTP_HOST, use_uid=True, ssl=True) as conn:
        conn.login(SMTP_USERNAME, password=SMTP_PASSWORD)
        conn.select_folder("inbox", readonly=False)
        # print("Connected to mailbox")
        # Using search method to filter messages by subject (SUBJECT ""), date (ON) and unseen (USEEN).
        data = conn.search(['SUBJECT', f'"{SEARCH_SUBJECT}"', 'UNSEEN']) # 'ON', today.strftime("%d-%b-%Y"),
        if len(data):
            for msg_id, msg_data in conn.fetch(data, ['RFC822']).items():
                download_all_attachments(msg_data)
            return True
        else:
            return False
