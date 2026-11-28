from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import SimpleTestCase, TestCase

from apps.admissions.models import Admission, AdmissionActivity
from apps.admissions.services.admission_service import (
    cancel_admission,
    restore_admission,
    update_admission_stage,
    validate_stage_transition,
)

User = get_user_model()
Stage = Admission.Stage


class ValidateStageTransitionTests(SimpleTestCase):
    def test_next_stage_is_allowed(self):
        pairs = [
            (Stage.CONSULTATION, Stage.SELECTION),
            (Stage.SELECTION, Stage.EXAMS),
            (Stage.EXAMS, Stage.DOCUMENTS),
            (Stage.DOCUMENTS, Stage.ARRIVAL),
        ]
        for current, new in pairs:
            with self.subTest(current=current, new=new):
                validate_stage_transition(current_stage=current, new_stage=new)

    def test_same_stage_is_noop(self):
        for stage in Stage.values:
            validate_stage_transition(current_stage=stage, new_stage=stage)

    def test_cancel_is_allowed_from_any_active_stage(self):
        for stage in (Stage.CONSULTATION, Stage.EXAMS, Stage.ARRIVAL):
            validate_stage_transition(current_stage=stage, new_stage=Stage.CANCELLED)

    def test_skip_or_backward_requires_override(self):
        for current, new in (
            (Stage.CONSULTATION, Stage.EXAMS),
            (Stage.DOCUMENTS, Stage.SELECTION),
            (Stage.ARRIVAL, Stage.CONSULTATION),
        ):
            with self.subTest(current=current, new=new):
                with self.assertRaises(PermissionDenied):
                    validate_stage_transition(current_stage=current, new_stage=new)

    def test_override_requires_note(self):
        with self.assertRaises(ValueError):
            validate_stage_transition(
                current_stage=Stage.CONSULTATION,
                new_stage=Stage.DOCUMENTS,
                can_override=True,
                note="   ",
            )

        validate_stage_transition(
            current_stage=Stage.CONSULTATION,
            new_stage=Stage.DOCUMENTS,
            can_override=True,
            note="HSK sertifikati oldindan mavjud",
        )

    def test_leaving_cancelled_only_via_restore(self):
        for new in (Stage.CONSULTATION, Stage.SELECTION):
            with self.assertRaises(ValueError):
                validate_stage_transition(
                    current_stage=Stage.CANCELLED,
                    new_stage=new,
                    can_override=True,
                    note="sabab",
                )

    def test_unknown_stage_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_stage_transition(current_stage=Stage.CONSULTATION, new_stage="UNKNOWN")


class AdmissionStageServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor = User.objects.create_user(username="adm_stage_actor", password="Password123!")

    def _admission(self, stage=Stage.CONSULTATION):
        return Admission.objects.create(
            full_name="Talaba",
            phone_number="+998900000000",
            stage=stage,
        )

    def test_update_stage_saves_and_logs_activity(self):
        admission = self._admission()

        updated = update_admission_stage(
            admission_id=admission.pk,
            stage=Stage.SELECTION,
            actor=self.actor,
        )

        self.assertEqual(updated.stage, Stage.SELECTION)
        activity = AdmissionActivity.objects.get(
            admission=admission,
            action=AdmissionActivity.Action.STAGE_CHANGED,
        )
        self.assertEqual(activity.old_value, Stage.CONSULTATION)
        self.assertEqual(activity.new_value, Stage.SELECTION)

    def test_invalid_transition_changes_nothing(self):
        admission = self._admission()

        with self.assertRaises(PermissionDenied):
            update_admission_stage(
                admission_id=admission.pk,
                stage=Stage.ARRIVAL,
                actor=self.actor,
            )

        admission.refresh_from_db()
        self.assertEqual(admission.stage, Stage.CONSULTATION)
        self.assertFalse(AdmissionActivity.objects.filter(admission=admission).exists())

    def test_override_transition_with_note(self):
        admission = self._admission()

        update_admission_stage(
            admission_id=admission.pk,
            stage=Stage.DOCUMENTS,
            actor=self.actor,
            note="Imtihonlardan ozod",
            can_override=True,
        )

        admission.refresh_from_db()
        self.assertEqual(admission.stage, Stage.DOCUMENTS)

    def test_cancel_and_restore_roundtrip(self):
        admission = self._admission(stage=Stage.EXAMS)

        cancel_admission(admission_id=admission.pk, actor=self.actor, note="Voz kechdi")
        admission.refresh_from_db()
        self.assertEqual(admission.stage, Stage.CANCELLED)

        # Bekor qilinganni qayta bekor qilish — no-op, yangi activity yozilmaydi.
        before = AdmissionActivity.objects.filter(admission=admission).count()
        cancel_admission(admission_id=admission.pk, actor=self.actor)
        self.assertEqual(AdmissionActivity.objects.filter(admission=admission).count(), before)

        # CANCELLED dan oddiy stage update bilan chiqib bo'lmaydi.
        with self.assertRaises(ValueError):
            update_admission_stage(
                admission_id=admission.pk,
                stage=Stage.EXAMS,
                actor=self.actor,
            )

        restore_admission(admission_id=admission.pk, actor=self.actor)
        admission.refresh_from_db()
        self.assertEqual(admission.stage, Stage.EXAMS)
