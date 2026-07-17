class StorageError(Exception):
    """Base error for private object storage operations."""


class StorageNotConfiguredError(StorageError):
    pass


class StorageUploadNotFoundError(StorageError):
    pass


class StorageUploadExpiredError(StorageError):
    pass


class StorageUploadAlreadyCompletedError(StorageError):
    pass


class StorageObjectNotFoundError(StorageError):
    pass


class StorageObjectSizeMismatchError(StorageError):
    pass


class StorageObjectTypeMismatchError(StorageError):
    pass


class StorageUploadFailedError(StorageError):
    pass


class StorageAccessDeniedError(StorageError):
    pass


class StorageServiceUnavailableError(StorageError):
    pass
