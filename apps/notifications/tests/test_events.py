"""Biznes service'lari ↔ notification integratsiyasi testlari."""

import uuid

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.models import Group, Permission
from django.test import TestCase

from apps.admissions.models import Admission
from apps.admissions.services import admission_service
from apps.inquiries.models import Inquiry, InquiryCategory
from apps.inquiries.services import inquiry_service
from apps.notifications.models import Notification
from apps.notifications.realtime import user_group_name
from apps.notifications.tests.base import (
    make_superuser,
    make_user,
    notification_test_settings,
)
from apps.rbac.services.role_service import RoleService
from apps.universities.services.faq_service import FAQService
from apps.universities.services.faq_translation_service import FAQTranslationService
from apps.universities.services.university_revision_service import (
    UniversityRevisionService,
)
from apps.universities.services.university_service import UniversityService
from apps.users.services.employee_service import EmployeeService

Type = Notification.Type


def notifications_for(user):
    return list(Notification.objects.filter(recipient=user).order_by("created_at"))


def types_for(user):
    return [n.type for n in notifications_for(user)]


class ChannelSpyMixin:
    def listen(self, user):
        layer = get_channel_layer()
        channel = async_to_sync(layer.new_channel)()
        async_to_sync(layer.group_add)(user_group_name(user.pk), channel)
        return channel

    def drain(self, channel):
        layer = get_channel_layer()
        messages = []
        queue = layer.channels.get(channel)
        while queue is not None and not queue.empty():
            messages.append(async_to_sync(layer.receive)(channel))
        return messages


# ============================================================================
# Inquiries
# ============================================================================

@notification_test_settings
class InquiryNotificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = make_superuser("ev_inq_super")
        cls.manager = make_user(
            "ev_inq_manager",
            "inquiries.view_inquiry",
            "inquiries.view_all_inquiries",
            "inquiries.add_inquiry",
            "inquiries.assign_inquiry",
            "inquiries.change_inquiry",
        )
        cls.inactive_manager = make_user(
            "ev_inq_inactive",
            "inquiries.view_all_inquiries",
            is_active=False,
        )
        cls.agent = make_user("ev_inq_agent", "inquiries.view_inquiry", "inquiries.change_inquiry")
        cls.agent2 = make_user("ev_inq_agent2", "inquiries.view_inquiry")
        cls.no_perm_user = make_user("ev_inq_noperm")
        cls.category = InquiryCategory.objects.create(slug="ev-cat", is_active=True)

    def _public_payload(self, **overrides):
        data = {
            "full_name": "Ali Valiyev",
            "phone_number": "+998901234567",
            "email": "",
            "category": self.category,
            "university": None,
            "contact_method": Inquiry.ContactMethod.PHONE,
            "message": "",
            "consent_accepted": True,
            "consent_version": "v1",
            "locale": "uz",
            "idempotency_key": uuid.uuid4(),
        }
        data.update(overrides)
        return data

    def _inquiry(self, *, assignee=None):
        return Inquiry.objects.create(
            category=self.category,
            full_name="Mijoz Ismi",
            phone_number="+998900000000",
            contact_method=Inquiry.ContactMethod.PHONE,
            consent_accepted=True,
            consent_version="v1",
            idempotency_key=uuid.uuid4(),
            assignee=assignee,
        )

    def test_public_inquiry_notifies_view_all_users_and_superusers_only(self):
        payload = self._public_payload()
        inquiry, created = inquiry_service.create_inquiry(payload)
        self.assertTrue(created)

        recipients = set(
            Notification.objects
            .filter(type=Type.INQUIRY_CREATED, entity_id=str(inquiry.pk))
            .values_list("recipient_id", flat=True)
        )
        self.assertEqual(recipients, {self.manager.pk, self.superuser.pk})

        # Idempotent takroriy so'rov yangi notification yaratmaydi.
        inquiry_service.create_inquiry(payload)
        self.assertEqual(
            Notification.objects.filter(type=Type.INQUIRY_CREATED).count(), 2
        )

    def test_public_inquiry_query_count_does_not_grow_with_recipients(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as few:
            inquiry_service.create_inquiry(self._public_payload())

        for index in range(5):
            make_user(f"ev_inq_extra_{index}", "inquiries.view_all_inquiries")

        with CaptureQueriesContext(connection) as many:
            inquiry_service.create_inquiry(self._public_payload())

        # Recipient'lar bitta SELECT bilan olinadi va bitta bulk INSERT bilan yoziladi.
        self.assertEqual(len(few), len(many))
        self.assertEqual(
            Notification.objects.filter(type=Type.INQUIRY_CREATED).count(),
            2 + 7,
        )

    def test_admin_created_inquiry_notifies_assignee_not_actor(self):
        inquiry = inquiry_service.create_admin_inquiry(
            validated_data={
                "full_name": "Lead",
                "phone_number": "+998901111111",
                "category": self.category,
                "assignee": self.agent,
            },
            actor=self.manager,
        )

        self.assertEqual(types_for(self.agent), [Type.INQUIRY_ASSIGNED])
        self.assertEqual(notifications_for(self.agent)[0].entity_id, str(inquiry.pk))
        self.assertEqual(types_for(self.manager), [])

    def test_reassignment_notifies_new_and_previous_assignee_without_leaking_pii(self):
        inquiry = self._inquiry(assignee=self.agent)

        inquiry_service.assign_inquiry(
            inquiry_id=inquiry.pk,
            assignee=self.agent2,
            actor=self.manager,
        )

        new_note = notifications_for(self.agent2)
        self.assertEqual([n.type for n in new_note], [Type.INQUIRY_ASSIGNED])
        self.assertIn("Mijoz Ismi", new_note[0].message)

        old_note = notifications_for(self.agent)
        self.assertEqual([n.type for n in old_note], [Type.INQUIRY_UNASSIGNED])
        # Eski mas'ul endi arizani ko'ra olmaydi → ism/telefon yuborilmaydi.
        self.assertNotIn("Mijoz Ismi", old_note[0].message)
        self.assertEqual(old_note[0].data, {})

    def test_assignee_without_view_permission_gets_nothing(self):
        inquiry = self._inquiry()
        inquiry_service.assign_inquiry(
            inquiry_id=inquiry.pk,
            assignee=self.no_perm_user,
            actor=self.manager,
        )
        self.assertEqual(types_for(self.no_perm_user), [])

    def test_status_change_notifies_assignee_unless_self(self):
        inquiry = self._inquiry(assignee=self.agent)

        inquiry_service.update_inquiry_status(
            inquiry_id=inquiry.pk,
            status=Inquiry.Status.IN_PROGRESS,
            actor=self.manager,
        )
        notes = notifications_for(self.agent)
        self.assertEqual([n.type for n in notes], [Type.INQUIRY_STATUS_CHANGED])
        self.assertEqual(
            notes[0].data,
            {"old_status": "new", "new_status": "in_progress"},
        )

        inquiry_service.update_inquiry_status(
            inquiry_id=inquiry.pk,
            status=Inquiry.Status.CONTACTED,
            actor=self.agent,
        )
        self.assertEqual(len(notifications_for(self.agent)), 1)

    def test_comment_notifies_assignee_unless_author(self):
        inquiry = self._inquiry(assignee=self.agent)

        inquiry_service.add_inquiry_comment(
            inquiry_id=inquiry.pk, actor=self.manager, note="Qayta qo'ng'iroq qiling"
        )
        inquiry_service.add_inquiry_comment(
            inquiry_id=inquiry.pk, actor=self.agent, note="O'zim yozdim"
        )

        notes = notifications_for(self.agent)
        self.assertEqual([n.type for n in notes], [Type.INQUIRY_COMMENT_ADDED])
        self.assertIn("Qayta qo'ng'iroq qiling", notes[0].message)

    def test_update_notifies_only_on_important_fields(self):
        inquiry = self._inquiry(assignee=self.agent)

        inquiry_service.update_inquiry(
            inquiry_id=inquiry.pk,
            validated_data={"message": "Ichki eslatma", "locale": "ru"},
            actor=self.manager,
        )
        self.assertEqual(types_for(self.agent), [])

        inquiry_service.update_inquiry(
            inquiry_id=inquiry.pk,
            validated_data={"phone_number": "+998977777777", "message": "x"},
            actor=self.manager,
        )
        notes = notifications_for(self.agent)
        self.assertEqual([n.type for n in notes], [Type.INQUIRY_UPDATED])
        self.assertEqual(notes[0].data, {"changed_fields": ["phone_number"]})


# ============================================================================
# Admissions
# ============================================================================

@notification_test_settings
class AdmissionNotificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = make_user(
            "ev_adm_manager",
            "admissions.view_admission",
            "admissions.view_all_admissions",
        )
        cls.curator = make_user("ev_adm_curator", "admissions.view_admission")
        cls.curator2 = make_user("ev_adm_curator2", "admissions.view_admission")
        cls.inquiry_agent = make_user("ev_adm_agent", "inquiries.view_inquiry")
        cls.inquiry_agent_all = make_user(
            "ev_adm_agent_all",
            "inquiries.view_inquiry",
            "admissions.view_all_admissions",
        )
        cls.category = InquiryCategory.objects.create(slug="ev-adm-cat", is_active=True)

    def _inquiry(self, assignee):
        return Inquiry.objects.create(
            category=self.category,
            full_name="Talaba",
            phone_number="+998900000001",
            contact_method=Inquiry.ContactMethod.PHONE,
            consent_accepted=True,
            consent_version="v1",
            idempotency_key=uuid.uuid4(),
            assignee=assignee,
        )

    def _admission(self, *, curator=None, inquiry=None):
        return Admission.objects.create(
            full_name="Talaba Ismi",
            phone_number="+998900000002",
            curator=curator,
            inquiry=inquiry,
        )

    def test_create_notifies_curator_and_inquiry_assignee_only_if_visible(self):
        admission = admission_service.create_admission(
            validated_data={
                "full_name": "Talaba Ismi",
                "phone_number": "+998900000002",
                "curator": self.curator,
                "inquiry": self._inquiry(self.inquiry_agent),
            },
            actor=self.manager,
        )
        self.assertEqual(types_for(self.curator), [Type.ADMISSION_CREATED])
        self.assertEqual(notifications_for(self.curator)[0].entity_id, str(admission.pk))
        # Inquiry mas'uli admissionni ko'ra olmaydi (curator scope) → yuborilmaydi.
        self.assertEqual(types_for(self.inquiry_agent), [])

        second = admission_service.create_admission(
            validated_data={
                "full_name": "Ikkinchi",
                "phone_number": "+998900000003",
                "curator": self.curator,
                "inquiry": self._inquiry(self.inquiry_agent_all),
            },
            actor=self.manager,
        )
        notes = notifications_for(self.inquiry_agent_all)
        self.assertEqual([n.type for n in notes], [Type.ADMISSION_CREATED])
        self.assertEqual(notes[0].entity_id, str(second.pk))
        self.assertIn("inquiry_id", notes[0].data)

    def test_curator_change_notifies_new_and_previous(self):
        admission = self._admission(curator=self.curator)

        admission_service.assign_admission_curator(
            admission_id=admission.pk,
            curator=self.curator2,
            actor=self.manager,
        )

        self.assertEqual(types_for(self.curator2), [Type.ADMISSION_CURATOR_ASSIGNED])
        old = notifications_for(self.curator)
        self.assertEqual([n.type for n in old], [Type.ADMISSION_CURATOR_UNASSIGNED])
        self.assertNotIn("Talaba Ismi", old[0].message)

    def test_stage_change_cancel_and_restore_notify_curator(self):
        admission = self._admission(curator=self.curator)

        admission_service.update_admission_stage(
            admission_id=admission.pk,
            stage=Admission.Stage.SELECTION,
            actor=self.manager,
        )
        admission_service.cancel_admission(
            admission_id=admission.pk,
            actor=self.manager,
            note="Talaba voz kechdi",
        )
        admission_service.restore_admission(
            admission_id=admission.pk,
            actor=self.manager,
        )

        self.assertEqual(
            types_for(self.curator),
            [
                Type.ADMISSION_STAGE_CHANGED,
                Type.ADMISSION_CANCELLED,
                Type.ADMISSION_RESTORED,
            ],
        )
        self.assertEqual(
            notifications_for(self.curator)[0].data,
            {"old_stage": "CONSULTATION", "new_stage": "SELECTION"},
        )

    def test_rejected_stage_transition_sends_no_notification(self):
        from django.core.exceptions import PermissionDenied

        admission = self._admission(curator=self.curator)

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            with self.assertRaises(PermissionDenied):
                admission_service.update_admission_stage(
                    admission_id=admission.pk,
                    stage=Admission.Stage.ARRIVAL,  # bosqich tashlab o'tish
                    actor=self.manager,
                )

        self.assertEqual(callbacks, [])
        self.assertEqual(types_for(self.curator), [])

    def test_comment_notifies_curator_unless_author(self):
        admission = self._admission(curator=self.curator)

        admission_service.add_admission_comment(
            admission_id=admission.pk, actor=self.curator, note="O'zim"
        )
        self.assertEqual(types_for(self.curator), [])

        admission_service.add_admission_comment(
            admission_id=admission.pk, actor=self.manager, note="Hujjatlarni tekshiring"
        )
        self.assertEqual(types_for(self.curator), [Type.ADMISSION_COMMENT_ADDED])


# ============================================================================
# CMS moderation
# ============================================================================

@notification_test_settings
class ModerationNotificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = make_superuser("ev_cms_super")
        cls.faq_author = make_user(
            "ev_faq_author",
            "universities.view_faq",
            "universities.add_faq",
            "universities.change_faq",
            "universities.submit_review_faq",
        )
        cls.faq_approver = make_user(
            "ev_faq_approver",
            "universities.approve_faq",
            "universities.reject_faq",
            "universities.publish_faq",
        )
        cls.faq_viewer = make_user("ev_faq_viewer", "universities.view_faq")

        cls.uni_author = make_user(
            "ev_uni_author",
            "universities.view_university",
            "universities.add_university",
            "universities.change_university",
            "universities.submit_review_university",
        )
        cls.uni_approver = make_user(
            "ev_uni_approver",
            "universities.view_university",
            "universities.approve_university",
            "universities.reject_university",
        )
        # approve bor, lekin universitetni ko'rish huquqi yo'q → yuborilmaydi.
        cls.uni_blind_approver = make_user(
            "ev_uni_blind", "universities.approve_university"
        )

    def _faq_revision(self, language_code="uz"):
        faq = FAQService.create_faq(actor=self.faq_author)
        translation = FAQTranslationService.create_translation(
            actor=self.faq_author,
            faq_id=faq.pk,
            language_code=language_code,
            question="Savol?",
            answer="Javob.",
        )
        return translation.revisions.get()

    def test_faq_submit_approve_publish_flow(self):
        revision = self._faq_revision()

        FAQTranslationService.submit_for_review(
            actor=self.faq_author, revision_id=revision.pk
        )
        submitted = Notification.objects.filter(type=Type.REVISION_SUBMITTED)
        self.assertEqual(
            set(submitted.values_list("recipient_id", flat=True)),
            {self.faq_approver.pk, self.superuser.pk},
        )
        self.assertEqual(submitted.first().entity_type, "faq_revision")
        self.assertEqual(submitted.first().data["language_code"], "uz")

        FAQTranslationService.approve_revision(
            actor=self.faq_approver, revision_id=revision.pk
        )
        FAQTranslationService.publish_translation_revision(
            actor=self.faq_approver, revision_id=revision.pk
        )

        self.assertEqual(
            types_for(self.faq_author),
            [Type.REVISION_APPROVED, Type.REVISION_PUBLISHED],
        )
        self.assertEqual(types_for(self.faq_viewer), [])

    def test_faq_reject_includes_reason(self):
        revision = self._faq_revision(language_code="ru")
        FAQTranslationService.submit_for_review(
            actor=self.faq_author, revision_id=revision.pk
        )
        FAQTranslationService.reject_revision(
            actor=self.faq_approver,
            revision_id=revision.pk,
            reason="Javob to'liq emas",
        )

        notes = notifications_for(self.faq_author)
        self.assertEqual([n.type for n in notes], [Type.REVISION_REJECTED])
        self.assertEqual(notes[0].data["reason"], "Javob to'liq emas")
        self.assertIn("Javob to'liq emas", notes[0].message)

    def test_university_submit_requires_approve_and_view_permissions(self):
        university = UniversityService.create_university(
            actor=self.uni_author, city="Pekin", country="Xitoy"
        )
        revision = university.revisions.get()

        UniversityRevisionService.submit_for_review(
            actor=self.uni_author, revision_id=revision.pk
        )

        recipients = set(
            Notification.objects
            .filter(type=Type.REVISION_SUBMITTED)
            .values_list("recipient_id", flat=True)
        )
        self.assertEqual(recipients, {self.uni_approver.pk, self.superuser.pk})

        UniversityRevisionService.approve_revision(
            actor=self.uni_approver, revision_id=revision.pk
        )
        self.assertEqual(types_for(self.uni_author), [Type.REVISION_APPROVED])
        self.assertEqual(
            notifications_for(self.uni_author)[0].data,
            {"university_id": str(university.pk), "revision_number": 1},
        )

    def test_university_reject_notifies_author(self):
        university = UniversityService.create_university(
            actor=self.uni_author, city="Shanxay", country="Xitoy"
        )
        revision = university.revisions.get()
        UniversityRevisionService.submit_for_review(
            actor=self.uni_author, revision_id=revision.pk
        )
        UniversityRevisionService.reject_revision(
            actor=self.uni_approver, revision_id=revision.pk, reason="Rasm yo'q"
        )

        notes = notifications_for(self.uni_author)
        self.assertEqual([n.type for n in notes], [Type.REVISION_REJECTED])
        self.assertEqual(notes[0].data["reason"], "Rasm yo'q")


# ============================================================================
# RBAC / Employees
# ============================================================================

@notification_test_settings
class RbacRealtimeEventTests(ChannelSpyMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = make_superuser("ev_rbac_super")
        cls.member = make_user("ev_rbac_member")
        cls.other = make_user("ev_rbac_other")
        cls.role = Group.objects.create(name="Call center")
        cls.member.groups.add(cls.role)
        cls.hr = make_user("ev_rbac_hr", "users.change_user", "users.assign_roles")

    def test_role_permission_change_notifies_role_members(self):
        member_channel = self.listen(self.member)
        other_channel = self.listen(self.other)
        permission = Permission.objects.get(
            content_type__app_label="inquiries", codename="view_inquiry"
        )

        with self.captureOnCommitCallbacks(execute=True):
            RoleService.assign_permissions(
                role_id=self.role.pk,
                permission_ids=[permission.pk],
                actor=self.superuser,
            )

        self.assertEqual(
            self.drain(member_channel), [{"type": "permissions.changed"}]
        )
        self.assertEqual(self.drain(other_channel), [])

        with self.captureOnCommitCallbacks(execute=True):
            RoleService.remove_permissions(
                role_id=self.role.pk,
                permission_ids=[permission.pk],
                actor=self.superuser,
            )
        self.assertEqual(
            self.drain(member_channel), [{"type": "permissions.changed"}]
        )

    def test_assigning_employee_role_notifies_employee_once(self):
        channel = self.listen(self.other)
        new_role = Group.objects.create(name="Bo'sh rol")

        with self.captureOnCommitCallbacks(execute=True):
            RoleService.assign_employee_to_roles(
                role_ids=[new_role.pk],
                employee=self.other,
                actor=self.hr,
            )
        self.assertEqual(self.drain(channel), [{"type": "permissions.changed"}])

        # Qayta biriktirish hech narsani o'zgartirmaydi → event yo'q.
        with self.captureOnCommitCallbacks(execute=True):
            RoleService.assign_employee_to_roles(
                role_ids=[new_role.pk],
                employee=self.other,
                actor=self.hr,
            )
        self.assertEqual(self.drain(channel), [])

    def test_denied_role_assignment_sends_no_event(self):
        from django.core.exceptions import PermissionDenied

        channel = self.listen(self.other)
        privileged = Group.objects.create(name="Imtiyozli")
        privileged.permissions.add(
            Permission.objects.get(content_type__app_label="inquiries", codename="delete_inquiry")
        )

        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(PermissionDenied):
                RoleService.assign_employee_to_roles(
                    role_ids=[privileged.pk],
                    employee=self.other,
                    actor=self.hr,
                )

        self.assertEqual(self.drain(channel), [])

    def test_removing_employee_role_notifies_employee(self):
        channel = self.listen(self.member)

        with self.captureOnCommitCallbacks(execute=True):
            RoleService.remove_employee_from_roles(
                role_ids=[self.role.pk],
                employee=self.member,
                actor=self.hr,
            )

        self.assertEqual(self.drain(channel), [{"type": "permissions.changed"}])

    def test_deactivation_terminates_websocket_sessions(self):
        channel = self.listen(self.other)

        with self.captureOnCommitCallbacks(execute=True):
            EmployeeService.deactivate_employee(
                actor=self.hr, employee_id=self.other.pk
            )

        self.assertEqual(self.drain(channel), [{"type": "session.terminate"}])

    def test_failed_business_operation_sends_no_event(self):
        channel = self.listen(self.member)

        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(Exception):
                # O'zini deaktivatsiya qilish taqiqlangan → ValidationError.
                EmployeeService.deactivate_employee(
                    actor=self.hr, employee_id=self.hr.pk
                )

        self.assertEqual(self.drain(channel), [])
