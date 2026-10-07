"""Gym-owner journey against PostgreSQL: sign in, onboard, verify, approve.

S3 is replaced by an in-memory fake so presigned uploads can be "completed"
without network access; everything else is the real API and database.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.modules.auth.security import hash_password
from app.storage.exceptions import StorageObjectNotFoundError
from app.storage.schemas import ObjectMetadata, PresignedUpload
from tests.integration.conftest import IntegrationAPI

OWNER_PHONE = "0712345678"
ADMIN_EMAIL = "reviewer@example.com"
ADMIN_PASSWORD = "Reviewer-Password-2026!"


@dataclass
class FakeStorage:
    """In-memory stand-in for S3Storage (same async interface)."""

    objects: dict[str, ObjectMetadata] = field(default_factory=dict)
    bucket: str = "sweto-test-bucket"

    def put(self, key: str, *, content_type: str, size: int) -> None:
        self.objects[key] = ObjectMetadata(
            content_type=content_type, content_length=size, etag="etag"
        )

    async def create_upload_url(self, *, key: str, mime_type: str) -> PresignedUpload:
        return PresignedUpload(
            url=f"https://s3.test/{key}",
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )

    async def create_download_url(self, *, key: str) -> PresignedUpload:
        return PresignedUpload(
            url=f"https://s3.test/download/{key}",
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )

    async def head_object(self, *, key: str) -> ObjectMetadata:
        if key not in self.objects:
            raise StorageObjectNotFoundError("The uploaded object was not found.")
        return self.objects[key]

    async def delete_object(self, *, key: str) -> None:
        self.objects.pop(key, None)


@pytest.fixture
def storage(monkeypatch: pytest.MonkeyPatch) -> FakeStorage:
    fake = FakeStorage()
    monkeypatch.setattr("app.modules.gyms.router.S3Storage", lambda _settings: fake)
    return fake


class Owner:
    def __init__(self, api: IntegrationAPI, token: str) -> None:
        self.api = api
        self.headers = {"Authorization": f"Bearer {token}"}

    async def call(self, method: str, path: str, **kwargs: Any) -> Any:
        response = await self.api.client.request(
            method, f"/api/v1{path}", headers=self.headers, **kwargs
        )
        return response


async def sign_in_owner(api: IntegrationAPI, phone: str = OWNER_PHONE) -> Owner:
    requested = await api.client.post(
        "/api/v1/auth/request-otp", json={"phone_number": phone}
    )
    assert requested.status_code == 201, requested.json()
    verified = await api.client.post(
        "/api/v1/auth/verify-otp",
        json={
            "challenge_id": requested.json()["data"]["challenge_id"],
            "code": api.sms.last_code(),
        },
    )
    assert verified.status_code == 200, verified.json()
    owner = Owner(api, verified.json()["data"]["tokens"]["access_token"])
    role = await owner.call("POST", "/account/roles", json={"role": "gym_owner"})
    assert role.status_code in (200, 201), role.json()
    return owner


async def sign_in_admin(api: IntegrationAPI) -> Owner:
    await api.sql(
        "INSERT INTO users (id, email, password_hash, role, status, "
        "is_phone_verified, must_change_password, is_system_protected) "
        "VALUES (gen_random_uuid(), :email, :hash, 'admin', 'active', "
        "false, false, false)",
        email=ADMIN_EMAIL,
        hash=hash_password(ADMIN_PASSWORD),
    )
    response = await api.client.post(
        "/api/v1/auth/password/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.json()
    return Owner(api, response.json()["data"]["tokens"]["access_token"])


WEEK = [
    {"day_of_week": day, "opens_at": "06:00:00", "closes_at": "21:00:00"}
    for day in range(6)
] + [{"day_of_week": 6, "is_closed": True}]

PRICING = {
    "day_passes": [{"name": "Day Pass", "amount": "500.00", "currency": "KES"}],
    "membership_plans": [],
}


async def complete_profile(owner: Owner, storage: FakeStorage) -> str:
    created = await owner.call(
        "POST",
        "/gyms",
        json={"name": "FlexFit Westlands", "phone_number": "0722000000"},
    )
    assert created.status_code == 201, created.json()
    gym_id = created.json()["data"]["gym"]["id"]

    steps = [
        (
            "PATCH",
            "location",
            {
                "address_line": "ABC Place, Waiyaki Way",
                "neighbourhood": "Westlands",
                "city": "Nairobi",
                "latitude": "-1.2676",
                "longitude": "36.8108",
            },
        ),
        (
            "PATCH",
            "business-details",
            {
                "legal_business_name": "FlexFit Wellness Limited",
                "business_type": "limited_company",
                "contact_person_name": "Wanjiru Kamau",
                "contact_person_phone": "0712345678",
            },
        ),
    ]
    for method, step, body in steps:
        response = await owner.call(method, f"/gyms/{gym_id}/{step}", json=body)
        assert response.status_code == 200, (step, response.json())

    amenities = (await owner.call("GET", "/gyms/amenities")).json()["data"]
    amenity_ids = [item["id"] for item in amenities[:2]]
    response = await owner.call(
        "PUT", f"/gyms/{gym_id}/amenities", json={"amenity_ids": amenity_ids}
    )
    assert response.status_code == 200, response.json()

    response = await owner.call(
        "PUT", f"/gyms/{gym_id}/operating-hours", json={"operating_hours": WEEK}
    )
    assert response.status_code == 200, response.json()

    response = await owner.call("PUT", f"/gyms/{gym_id}/pricing", json=PRICING)
    assert response.status_code == 200, response.json()
    return gym_id


async def upload_documents(owner: Owner, storage: FakeStorage, gym_id: str) -> None:
    for document_type in ("business_registration", "owner_identification"):
        base = f"/gyms/{gym_id}/verification/documents/{document_type}/upload"
        intent = await owner.call(
            "POST",
            base,
            json={
                "filename": f"{document_type}.pdf",
                "mime_type": "application/pdf",
                "file_size_bytes": 2048,
            },
        )
        assert intent.status_code in (200, 201), intent.json()
        data = intent.json()["data"]
        storage.put(data["storage_key"], content_type="application/pdf", size=2048)
        done = await owner.call("POST", f"{base}/{data['upload_id']}/complete")
        assert done.status_code in (200, 201), done.json()


async def onboarding(owner: Owner, gym_id: str) -> dict[str, Any]:
    response = await owner.call("GET", f"/gyms/{gym_id}/onboarding")
    assert response.status_code == 200
    return response.json()["data"]


async def test_owner_onboards_is_approved_and_becomes_listed(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id = await complete_profile(owner, storage)
    assert (await onboarding(owner, gym_id))["next_step"] == "verification"

    await upload_documents(owner, storage, gym_id)
    submitted = await owner.call("POST", f"/gyms/{gym_id}/verification/submit")
    assert submitted.status_code == 200, submitted.json()
    state = await onboarding(owner, gym_id)
    assert state["verification_status"] == "pending"
    assert state["limited_access"] is True

    admin = await sign_in_admin(api)
    queue = await admin.call("GET", "/admin/gym-verifications")
    assert [item["gym_id"] for item in queue.json()["data"]["gyms"]] == [gym_id]

    approved = await admin.call(
        "POST",
        f"/admin/gym-verifications/{gym_id}/review",
        json={"decision": "approve"},
    )
    assert approved.status_code == 200, approved.json()

    state = await onboarding(owner, gym_id)
    assert state["verification_status"] == "approved"
    assert state["status"] == "active"
    assert state["onboarding_completed"] is True
    gym = (await owner.call("GET", "/gyms/current")).json()["data"]
    assert gym["is_listed"] is True


async def test_rejected_gym_can_fix_and_resubmit(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id = await complete_profile(owner, storage)
    await upload_documents(owner, storage, gym_id)
    await owner.call("POST", f"/gyms/{gym_id}/verification/submit")
    admin = await sign_in_admin(api)

    missing_reason = await admin.call(
        "POST", f"/admin/gym-verifications/{gym_id}/review", json={"decision": "reject"}
    )
    assert missing_reason.status_code == 422

    rejected = await admin.call(
        "POST",
        f"/admin/gym-verifications/{gym_id}/review",
        json={"decision": "reject", "rejection_reason": "ID document is blurry."},
    )
    assert rejected.status_code == 200
    state = await onboarding(owner, gym_id)
    assert state["verification_status"] == "rejected"
    assert state["verification_rejection_reason"] == "ID document is blurry."
    gym = (await owner.call("GET", "/gyms/current")).json()["data"]
    assert gym["is_listed"] is False

    await upload_documents(owner, storage, gym_id)
    resubmitted = await owner.call("POST", f"/gyms/{gym_id}/verification/submit")
    assert resubmitted.status_code == 200, resubmitted.json()


async def test_verification_cannot_be_submitted_before_the_profile_is_complete(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    created = await owner.call("POST", "/gyms", json={"name": "Half Done Gym"})
    gym_id = created.json()["data"]["gym"]["id"]
    await upload_documents(owner, storage, gym_id)

    response = await owner.call("POST", f"/gyms/{gym_id}/verification/submit")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "GYM_PROFILE_INCOMPLETE"
    assert response.json()["error"]["details"]["next_step"] == "location"


async def test_submit_with_missing_documents_lists_them(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id = await complete_profile(owner, storage)

    response = await owner.call("POST", f"/gyms/{gym_id}/verification/submit")

    assert response.status_code == 422
    assert response.json()["error"]["details"]["missing_document_types"] == [
        "business_registration",
        "owner_identification",
    ]


async def test_double_submit_is_rejected(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id = await complete_profile(owner, storage)
    await upload_documents(owner, storage, gym_id)
    assert (
        await owner.call("POST", f"/gyms/{gym_id}/verification/submit")
    ).status_code == 200

    again = await owner.call("POST", f"/gyms/{gym_id}/verification/submit")

    assert again.status_code == 409


async def test_upload_completion_fails_when_the_object_was_never_uploaded(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id = await complete_profile(owner, storage)
    base = f"/gyms/{gym_id}/verification/documents/owner_identification/upload"
    intent = await owner.call(
        "POST",
        base,
        json={
            "filename": "id.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 2048,
        },
    )
    upload_id = intent.json()["data"]["upload_id"]

    response = await owner.call("POST", f"{base}/{upload_id}/complete")

    assert response.status_code >= 400


async def test_another_owner_cannot_touch_my_gym(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id = await complete_profile(owner, storage)
    await api.sql("UPDATE otp_challenges SET created_at = now() - interval '2 minutes'")
    intruder = await sign_in_owner(api, phone="0798765432")

    for method, path, body in [
        ("GET", f"/gyms/{gym_id}/onboarding", None),
        ("PUT", f"/gyms/{gym_id}/pricing", PRICING),
        ("POST", f"/gyms/{gym_id}/verification/submit", None),
    ]:
        response = await intruder.call(method, path, json=body)
        assert response.status_code in (403, 404), (path, response.status_code)


async def test_owner_cannot_create_a_second_gym(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    await complete_profile(owner, storage)

    second = await owner.call("POST", "/gyms", json={"name": "Second Gym"})

    assert second.status_code == 409


async def test_pricing_rejects_invalid_amounts(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id = await complete_profile(owner, storage)

    for day_pass in [
        {"name": "Free", "amount": "0"},
        {"name": "Negative", "amount": "-100"},
    ]:
        response = await owner.call(
            "PUT",
            f"/gyms/{gym_id}/pricing",
            json={"day_passes": [day_pass], "membership_plans": []},
        )
        assert response.status_code == 422, day_pass


async def upload_photo(
    owner: Owner, storage: FakeStorage, gym_id: str, *, mime: str = "image/jpeg"
) -> Any:
    intent = await owner.call(
        "POST",
        f"/gyms/{gym_id}/photos/upload",
        json={"filename": "front.jpg", "mime_type": mime, "file_size": 4096},
    )
    if intent.status_code != 201:
        return intent
    data = intent.json()["data"]
    storage.put(data["storage_key"], content_type=mime, size=4096)
    return await owner.call(
        "POST", f"/gyms/{gym_id}/photos/upload/{data['upload_id']}/complete"
    )


async def test_photos_upload_list_cover_and_delete(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id = await complete_profile(owner, storage)

    first = await upload_photo(owner, storage, gym_id)
    assert first.status_code == 200, first.json()
    assert first.json()["data"]["photo"]["is_cover"] is True
    second = await upload_photo(owner, storage, gym_id)
    assert second.json()["data"]["photo"]["is_cover"] is False

    listed = await owner.call("GET", f"/gyms/{gym_id}/photos")
    assert listed.status_code == 200
    photo_id = first.json()["data"]["photo"]["id"]

    deleted = await owner.call("DELETE", f"/gyms/{gym_id}/photos/{photo_id}")
    assert deleted.status_code == 200, deleted.json()
    remaining = (await owner.call("GET", f"/gyms/{gym_id}/photos")).json()["data"]
    assert len(remaining["photos"]) == 1


async def test_photo_limit_is_a_client_error_not_a_crash(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id = await complete_profile(owner, storage)
    for _ in range(5):
        assert (await upload_photo(owner, storage, gym_id)).status_code == 200

    sixth = await upload_photo(owner, storage, gym_id)

    assert sixth.status_code == 409
    assert sixth.json()["error"]["code"] == "GYM_PHOTO_LIMIT_REACHED"


async def test_unsupported_photo_type_is_a_client_error(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id = await complete_profile(owner, storage)

    response = await upload_photo(owner, storage, gym_id, mime="image/gif")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "GYM_PHOTO_INVALID"
