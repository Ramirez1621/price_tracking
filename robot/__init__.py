import logging
from robot.manage_directories import create_directories
from settings import LOG_NAME
import time as t


from tenacity import RetryError
from numba import njit

# Create project directories
PATH = create_directories()

# @njit
def main():
    from .mailbox import connect_to_mailbox
    from .browser import browsing_session
    from .processing import homolagated_data
    from .email.email_service import set_email_format, send_email

    logging.basicConfig(filename=LOG_NAME, level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logging.info("Robot started.")
    try:
        start = t.time()
        # logging.info("Mailbox module finished.")
        # Execute browsing_session module
        logging.info("Browsing module started.")
        browsing_session()
        logging.info("Browsing module finished.")
        logging.info("Homolated Data module started.")
        homolagated_data()
        logging.info("Homolated Data module started.")
        # Execute process_report module
        
        end = t.time()
        logging.info(f"Excution Robot Time: {end-start}")
        logging.info("Robot finished...")
    except RetryError as e:
        message = set_email_format(f"Error en la ejecución para el cambio de cliente en remesas", f"""
        Ha ocurrido un error al enviar el registro al web service aunque es posible que el cambio de cliente se haya realizado con éxito, por favor verifique el archivo de registro "task.log".

        Mensaje del error: {e}
        """)
        send_email(message)
        print(e)    

    except Exception as e:
        message = set_email_format(f"Error en la ejecución para el cambio de cliente en remesas", f"""
        Ha ocurrido un error durante la ejecución del proceso para el cambio masivo de remesas.

        Mensaje del error: {e}
        """)
        send_email(message)
        logging.error(f"An error occurred: {e}")
        print(e)

    else:
        # Execute email module.
        message = set_email_format()
        send_email(message)
        logging.info("Email module finished.")
        logging.info("Robot finished.")
