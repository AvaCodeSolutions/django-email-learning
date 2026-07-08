import enum


class PlatformFeature(enum.StrEnum):
    CREATE_COURSE = "create_course"
    CAN_ADD_MEMBER = "can_add_member"
    AI_EDIT = "ai_edit"
    GOOGLE_WORKSPACE_ENROLL = "google_workspace_enroll"
    NEWSLETTERS = "newsletters"
    CREATE_NEWSLETTER = "create_newsletter"
