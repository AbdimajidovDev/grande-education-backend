from apps.universities.models import UniversityAuditLog


class AuditLogService:
    """DELETE va ARCHIVE operatsiyalari uchun atomik audit log yozuvlarini yaratadi."""

    @staticmethod
    def _resolve_actor_identifier(actor) -> str:
        if actor is None:
            return "system"

        username = getattr(actor, "username", "")
        if username:
            return str(username)[:255]

        pk = getattr(actor, "pk", None)
        return str(pk)[:255] if pk is not None else "unknown"

    @staticmethod
    def log_action(
        *,
        actor,
        action: str,
        entries: list[dict],
    ) -> list[UniversityAuditLog]:
        """Bir yoki bir nechta obyektlar uchun audit log yozadi."""

        if not entries:
            return []

        actor_obj = actor if getattr(actor, "pk", None) else None
        actor_identifier = AuditLogService._resolve_actor_identifier(actor)

        logs = [
            UniversityAuditLog(
                actor=actor_obj,
                actor_identifier=actor_identifier,
                action=action,
                object_type=entry["object_type"],
                object_id=str(entry["object_id"]),
                object_repr=str(entry["object_repr"])[:255],
                metadata=entry.get("metadata") or {},
            )
            for entry in entries
        ]

        return UniversityAuditLog.objects.bulk_create(logs)

    @staticmethod
    def log_deletes(*, actor, entries: list[dict]) -> list[UniversityAuditLog]:
        """O'chirilgan obyektlar uchun DELETE audit log yozadi."""

        return AuditLogService.log_action(
            actor=actor,
            action=UniversityAuditLog.Action.DELETE,
            entries=entries,
        )

    @staticmethod
    def log_archives(*, actor, entries: list[dict]) -> list[UniversityAuditLog]:
        """Arxivlangan obyektlar uchun ARCHIVE audit log yozadi."""

        return AuditLogService.log_action(
            actor=actor,
            action=UniversityAuditLog.Action.ARCHIVE,
            entries=entries,
        )
