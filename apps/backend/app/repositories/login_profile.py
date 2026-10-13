from sqlalchemy import select
from app.models import LoginProfileVersion

def find_version(db, profile_id, version):
    return db.scalar(select(LoginProfileVersion).where(LoginProfileVersion.profile_id == profile_id, LoginProfileVersion.version == version))
