from tinydb import Query

from services.app.core.database import profiles_table
from services.app.models.profile import ProfilePublic, ProfileUpdate


class ProfileNotFoundError(LookupError):
    pass


def get_profile_by_user_id(user_id: int) -> ProfilePublic:
    Profile = Query()
    rows = profiles_table.search(Profile.user_id == user_id)
    if not rows:
        raise ProfileNotFoundError(f"Profile for user {user_id} not found")
    doc = rows[0]
    return ProfilePublic(
        id=doc.doc_id,
        user_id=doc["user_id"],
        name=doc.get("name"),
        phone=doc.get("phone"),
        address=doc.get("address"),
    )


def update_profile_by_user_id(user_id: int, payload: ProfileUpdate) -> ProfilePublic:
    Profile = Query()
    rows = profiles_table.search(Profile.user_id == user_id)
    if not rows:
        raise ProfileNotFoundError(f"Profile for user {user_id} not found")

    doc = rows[0]
    changes = payload.model_dump(exclude_unset=True)
    if changes:
        profiles_table.update(changes, doc_ids=[doc.doc_id])

    return get_profile_by_user_id(user_id)