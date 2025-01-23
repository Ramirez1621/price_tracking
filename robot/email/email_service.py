import logging
import smtplib
import os
from email import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from settings import CC, MESSAGE, SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_RECIPIENTS, MESSAGE_SUBJECT


def send_email(message: MIMEMultipart):
    """
    Sends an email to message['To'] recipients value with content of message MIMEMultipart argument.
    """
    try:
        with smtplib.SMTP(host=SMTP_HOST, port=SMTP_PORT, timeout=10) as conn:
            conn.starttls()
            conn.login(user=SMTP_USERNAME,
                       password=SMTP_PASSWORD)
            conn.sendmail(from_addr=message.get('From'), to_addrs=message.get(
                'To').split(','), msg=message.as_string())
    except Exception as e:
        logging.info(
            f'The following exception has ocurred during sending email notifications: {e}')
    else:
        logging.info('The email notifications were sent successfully.')


def set_email_format(subject=MESSAGE_SUBJECT, message=MESSAGE,recipients=None, files_to_attach=None) -> MIMEMultipart:
    """
    Sets format of an e-mail message with the recipients and EMAIL_RECIPIENTS as recipients and inserting the file specified by filename as attachment.
    If recipients is None, the message will only include the recipients in environment variable EMAIL_RECIPIENTS.
    If filename is None, no file will be inserted as an attachment. 
    """
    msg = MIMEMultipart()

    # Setting of the email message
    msg_to = EMAIL_RECIPIENTS.split(',')
    if recipients:
        msg_to = recipients

    msg['From'] = SMTP_USERNAME
    msg['To'] = ",".join(msg_to)
    msg['Cc'] = CC
    msg['Subject'] = subject

    if files_to_attach:

        for file in files_to_attach:

            attachment = MIMEBase("application", "octect-stream")

            with open(file, mode='rb') as part:
                attachment.set_payload(part.read())

            encoders.encode_base64(attachment)

            attachment.add_header("content-Disposition",
                                  'attachment', filename=os.path.basename(file))

            msg.attach(attachment)

    # add in the message body
    msg.attach(MIMEText(message, 'plain'))

    return msg
