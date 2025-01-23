from os.path import join, exists, isabs
from os import mkdir, listdir


from settings import BASE_DIR, FILES_DIR, DATE


def create_directory(path: str):
    if not exists(path):
        mkdir(path)


def create_directories() -> str:
    # today = dt.datetime.today()

    if isabs(FILES_DIR):
        folder_path = FILES_DIR
    else:
        folder_path = join(BASE_DIR, FILES_DIR)

    # Create directory FILES_DIR
    create_directory(folder_path)

    # Create directory by year.
    folder_path = join(folder_path, f"{DATE.year}-{DATE.month}-{DATE.day}")
    create_directory(folder_path)

    # # Create directory by month
    # folder_path = join(folder_path, str(DATE.month))
    # create_directory(folder_path)

    # # Create directory by day
    # folder_path = join(folder_path, str(DATE.day))
    # create_directory(folder_path)

    return folder_path


# def report_downloaded(path: str) -> bool:
#     return any("Checklist" in file and "crdownload" not in file for file in listdir(path))
