from django.core.files.storage import default_storage


class FileDoesNotExistError(Exception):
    pass


def move_file(path: str, target_path: str) -> str:
    if default_storage.exists(path):
        default_storage.save(target_path, default_storage.open(path))
        default_storage.delete(path)
        return target_path
    else:
        raise FileDoesNotExistError("File does not exist.")
