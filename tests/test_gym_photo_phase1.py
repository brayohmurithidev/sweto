from uuid import uuid4

from app.modules.gyms.models import GymPhoto
from app.modules.gyms.photo_upload import GymPhotoUploadPurpose
from app.storage.enums import UploadPurpose, UploadStatus
from app.storage.keys import build_gym_photo_key


def test_gym_photo_persistence_shape() -> None:
    photo = GymPhoto(
        gym_id=uuid4(),
        storage_key="gyms/gym/photos/photo.jpg",
        original_filename="photo.jpg",
        mime_type="image/jpeg",
        file_size=1024,
        display_order=0,
        is_cover=True,
    )
    assert photo.gym_id is not None
    assert photo.storage_key.endswith("photo.jpg")
    assert photo.is_cover is True


def test_photo_upload_purpose_is_separate_from_verification() -> None:
    assert GymPhotoUploadPurpose.GYM_PHOTO.value == "gym_photo"
    assert UploadPurpose.GYM_VERIFICATION_DOCUMENT.value == (
        "gym_verification_document"
    )
    assert UploadStatus.PENDING.value == "pending"


def test_gym_photo_storage_key_is_server_controlled() -> None:
    gym_id = uuid4()
    upload_id = uuid4()
    key = build_gym_photo_key(
        gym_id=gym_id,
        upload_id=upload_id,
        mime_type="image/jpeg",
    )
    assert key == f"gyms/{gym_id}/photos/{upload_id}.jpg"
