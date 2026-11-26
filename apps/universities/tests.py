
import tempfile
import uuid
from io import BytesIO
from unittest.mock import patch
from PIL import Image

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.deletion import ProtectedError
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.universities.models import (
    FAQ,
    FAQTranslation,
    FAQTranslationRevision,
    MediaCleanupTask,
    University,
    UniversityAdmissionPeriod,
    UniversityAuditLog,
    UniversityRevision,
    UniversityTranslation,
    UniversityTranslationRevision,
    UniversityMajor,
    UniversityMajorTranslation,
    UniversityMedia,
)
from apps.universities.services.media_lifecycle_service import (
    MediaLifecycleService,
)
from apps.universities.services.university_revision_service import (
    UniversityRevisionService,
)
from apps.universities.services.university_translation_service import (
    UniversityTranslationService,
)
from apps.universities.services.university_major_service import (
    UniversityMajorService,
)
from apps.universities.services.university_media_service import (
    UniversityMediaService,
)
from apps.universities.api.public.serializers.public_serializers import (
    PublicUniversityDetailSerializer,
)

User = get_user_model()


def create_dummy_image():
    """Testlar uchun kichik dummy rasm hosil qiladi."""
    file = BytesIO()
    image = Image.new("RGB", (100, 100), color="blue")
    image.save(file, format="JPEG")
    file.seek(0)
    return SimpleUploadedFile("test.jpg", file.read(), content_type="image/jpeg")


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.InMemoryStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
)
class UniversityEnhancementsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Superuser
        cls.superuser = User.objects.create_superuser(
            username="superadmin",
            email="superadmin@example.com",
            password="Password123!",
        )

        # Editor with change_university
        cls.university_editor = User.objects.create_user(
            username="editor",
            email="editor@example.com",
            password="Password123!",
        )
        editor_group = Group.objects.create(name="University Editor")
        perm_change_univ = Permission.objects.get(
            content_type__app_label="universities",
            codename="change_university",
        )
        perm_view_univ = Permission.objects.get(
            content_type__app_label="universities",
            codename="view_university",
        )
        editor_group.permissions.add(perm_change_univ, perm_view_univ)
        cls.university_editor.groups.add(editor_group)

        # Granular major viewer
        cls.major_viewer = User.objects.create_user(
            username="major_viewer",
            email="major_viewer@example.com",
            password="Password123!",
        )
        major_view_group = Group.objects.create(name="Major Viewer")
        perm_view_major = Permission.objects.get(
            content_type__app_label="universities",
            codename="view_universitymajor",
        )
        major_view_group.permissions.add(perm_view_major)
        cls.major_viewer.groups.add(major_view_group)

        # Granular major creator
        cls.major_creator = User.objects.create_user(
            username="major_creator",
            email="major_creator@example.com",
            password="Password123!",
        )
        major_create_group = Group.objects.create(name="Major Creator")
        perm_add_major = Permission.objects.get(
            content_type__app_label="universities",
            codename="add_universitymajor",
        )
        major_create_group.permissions.add(perm_view_major, perm_add_major)
        cls.major_creator.groups.add(major_create_group)

        # User without any permissions
        cls.unauthorized_user = User.objects.create_user(
            username="no_perms",
            email="no_perms@example.com",
            password="Password123!",
        )

        # Universitet va dastlabki revision
        cls.university = University.objects.create(
            status=University.Status.DRAFT,
            created_by=cls.superuser,
        )
        cls.revision = UniversityRevision.objects.create(
            university=cls.university,
            revision_number=1,
            city="Hangzhou",
            country="China",
            city_native="Hangzhou, Zhejiang",
            chinese_name="浙江大学",
            established_year=1897,
            students_count=54000,
            international_students_count=7000,
            status=UniversityRevision.Status.DRAFT,
            created_by=cls.superuser,
        )

        # Tarjima va uning revisioni
        cls.translation = UniversityTranslation.objects.create(
            university=cls.university,
            language_code="uz",
            slug="zhejiang-university",
        )
        cls.trans_revision = UniversityTranslationRevision.objects.create(
            translation=cls.translation,
            revision_number=1,
            name="Zhejiang Universiteti",
            slug="zhejiang-university",
            subtitle="Xitoyning nufuzli C9 League a'zosi bo'lgan top universiteti",
            description="Universitet haqida batafsil ma'lumot...",
            features=["C9 League", "Top 50 QS", "Katta kampus"],
            accommodation_info="1-2 kishilik qulay xonalar, konditsioner, oshxona.",
            admission_note="IELTS 6.0 yoki HSK 4 talab qilinadi.",
            status=UniversityTranslationRevision.Status.DRAFT,
            created_by=cls.superuser,
        )

    def setUp(self):
        self.client = APIClient()

    def test_university_revision_service_fields(self):
        """Revision yaratish va tahrirlashda yangi maydonlar saqlanishini tekshirish."""
        # Yangi revision yaratish
        new_rev = UniversityRevisionService.create_revision(
            actor=self.university_editor,
            university_id=self.university.pk,
            city="Shanghai",
            country="China",
            city_native="Shanghai, China",
            chinese_name="复旦大学",
            established_year=1905,
            students_count=36000,
            international_students_count=3000,
        )
        self.assertEqual(new_rev.chinese_name, "复旦大学")
        self.assertEqual(new_rev.established_year, 1905)
        self.assertEqual(new_rev.students_count, 36000)
        self.assertEqual(new_rev.international_students_count, 3000)

        # Tahrirlash
        updated_rev = UniversityRevisionService.update_revision(
            actor=self.university_editor,
            revision_id=new_rev.pk,
            city="Shanghai New",
            students_count=38000,
        )
        self.assertEqual(updated_rev.city, "Shanghai New")
        self.assertEqual(updated_rev.students_count, 38000)
        self.assertEqual(updated_rev.chinese_name, "复旦大学")

    def test_university_translation_service_fields(self):
        """Tarjima revision yaratish va tahrirlashda yangi maydonlar saqlanishini tekshirish."""
        rev = UniversityTranslationService.create_revision(
            actor=self.university_editor,
            translation_id=self.translation.pk,
            name="Zhejiang University New",
            slug="zhejiang-university-new",
            subtitle="Top tadqiqot universiteti",
            features=["Grantlar mavjud", "Yotoqxona bepul"],
            accommodation_info="Yotoqxona kampus ichida.",
            admission_note="Ariza topshirish muddati: 30-iyun.",
        )
        self.assertEqual(rev.subtitle, "Top tadqiqot universiteti")
        self.assertEqual(rev.features, ["Grantlar mavjud", "Yotoqxona bepul"])
        self.assertEqual(rev.accommodation_info, "Yotoqxona kampus ichida.")
        self.assertEqual(rev.admission_note, "Ariza topshirish muddati: 30-iyun.")

        # Tahrirlash
        updated = UniversityTranslationService.update_revision(
            actor=self.university_editor,
            revision_id=rev.pk,
            subtitle="Yangilangan subtitle",
            features=["Akkreditatsiyadan o'tgan"],
        )
        self.assertEqual(updated.subtitle, "Yangilangan subtitle")
        self.assertEqual(updated.features, ["Akkreditatsiyadan o'tgan"])

    def test_university_major_service_crud(self):
        """Major service CRUD va tarjimalar ishlashini tekshirish."""
        major = UniversityMajorService.create_major(
            actor=self.university_editor,
            revision_id=self.revision.pk,
            order=1,
            is_active=True,
            translations=[
                {"language_code": "uz", "title": "Dasturiy ta'minot muhandisligi", "description": "IT yo'nalishi"},
                {"language_code": "en", "title": "Software Engineering", "description": "CS field"},
            ],
        )
        self.assertEqual(major.order, 1)
        self.assertEqual(major.translations.count(), 2)

        # Yangilash
        updated_major = UniversityMajorService.update_major(
            actor=self.university_editor,
            major_id=major.pk,
            order=5,
            is_active=False,
        )
        self.assertEqual(updated_major.order, 5)
        self.assertFalse(updated_major.is_active)

        # Tarjima qo'shish / yangilash
        ru_trans = UniversityMajorService.set_major_translation(
            actor=self.university_editor,
            major_id=major.pk,
            language_code="ru",
            title="Программная инженерия",
        )
        self.assertEqual(ru_trans.title, "Программная инженерия")
        self.assertEqual(major.translations.count(), 3)

        # O'chirish
        UniversityMajorService.delete_major(
            actor=self.university_editor,
            major_id=major.pk,
        )
        self.assertFalse(UniversityMajor.objects.filter(pk=major.pk).exists())

    def test_university_media_service_crud(self):
        """Media service CRUD va fayl tozalashni tekshirish."""
        dummy_file = create_dummy_image()
        media = UniversityMediaService.create_media(
            actor=self.university_editor,
            revision_id=self.revision.pk,
            file=dummy_file,
            media_type=UniversityMedia.MediaType.COVER,
            order=1,
            caption="Bosh bino",
        )
        self.assertEqual(media.media_type, "cover")
        self.assertEqual(media.caption, "Bosh bino")

        # Yangilash
        updated_media = UniversityMediaService.update_media(
            actor=self.university_editor,
            media_id=media.pk,
            caption="Yangi bino surati",
            order=2,
        )
        self.assertEqual(updated_media.caption, "Yangi bino surati")
        self.assertEqual(updated_media.order, 2)

        # O'chirish
        UniversityMediaService.delete_media(
            actor=self.university_editor,
            media_id=media.pk,
        )
        self.assertFalse(UniversityMedia.objects.filter(pk=media.pk).exists())

    def test_cms_major_views_dynamic_rbac(self):
        """CMS Major viewlarida dynamic RBAC ruxsatlarini tekshirish."""
        url = f"/api/v1/admin/university-revisions/{self.revision.pk}/majors/"

        # 1. Anonim foydalanuvchi -> 401
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        # 2. Huquqi yo'q foydalanuvchi -> 403
        self.client.force_authenticate(user=self.unauthorized_user)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Faqat view_universitymajor huquqiga ega foydalanuvchi -> GET 200, lekin POST 403
        self.client.force_authenticate(user=self.major_viewer)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        res = self.client.post(url, {"order": 1}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # 4. add_universitymajor huquqiga ega foydalanuvchi -> POST 201
        self.client.force_authenticate(user=self.major_creator)
        post_data = {
            "order": 1,
            "is_active": True,
            "translations": [
                {"language_code": "uz", "title": "Biotibbiyot muhandisligi"},
            ],
        }
        res = self.client.post(url, post_data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        major_id = res.data["id"]

        # 5. change_university huquqiga ega editor -> PATCH 200
        self.client.force_authenticate(user=self.university_editor)
        detail_url = f"/api/v1/admin/majors/{major_id}/"
        res = self.client.patch(detail_url, {"order": 10}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["order"], 10)

        # Tarjima o'rnatish
        trans_url = f"/api/v1/admin/majors/{major_id}/translations/"
        res = self.client.post(
            trans_url,
            {"language_code": "en", "title": "Biomedical Engineering"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # 6. O'chirish -> DELETE 204
        res = self.client.delete(detail_url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_cms_media_views_dynamic_rbac(self):
        """CMS Media viewlarida dynamic RBAC ruxsatlarini tekshirish."""
        url = f"/api/v1/admin/university-revisions/{self.revision.pk}/media/"

        # 1. Huquqsiz foydalanuvchi -> 403
        self.client.force_authenticate(user=self.unauthorized_user)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Superuser or Editor yuklay oladi
        self.client.force_authenticate(user=self.university_editor)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        dummy_file = create_dummy_image()
        res = self.client.post(
            url,
            {
                "file": dummy_file,
                "media_type": "gallery",
                "caption": "Kutubxona",
                "order": 1,
            },
            format="multipart",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        media_id = res.data["id"]

        # Patch
        detail_url = f"/api/v1/admin/media/{media_id}/"
        res = self.client.patch(detail_url, {"caption": "Yangi Kutubxona"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["caption"], "Yangi Kutubxona")

        # Delete
        res = self.client.delete(detail_url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_public_university_detail_serializer_full_data(self):
        """Published universitet ma'lumotlari public serializerda to'liq chiqishini tekshirish."""
        # Universitetni published holatga keltiramiz
        self.revision.status = UniversityRevision.Status.PUBLISHED
        self.revision.save()
        self.trans_revision.status = UniversityTranslationRevision.Status.PUBLISHED
        self.trans_revision.save()
        self.translation.published_revision = self.trans_revision
        self.translation.save()

        self.university.status = University.Status.PUBLISHED
        self.university.published_revision = self.revision
        self.university.save()

        # Logo, cover, gallery qo'shamiz
        UniversityMedia.objects.create(
            university_revision=self.revision,
            file=create_dummy_image(),
            media_type=UniversityMedia.MediaType.LOGO,
            order=1,
            caption="Logo",
        )
        UniversityMedia.objects.create(
            university_revision=self.revision,
            file=create_dummy_image(),
            media_type=UniversityMedia.MediaType.COVER,
            order=1,
            caption="Cover Image",
        )
        UniversityMedia.objects.create(
            university_revision=self.revision,
            file=create_dummy_image(),
            media_type=UniversityMedia.MediaType.GALLERY,
            order=1,
            caption="Gallery photo 1",
        )

        # Major qo'shamiz
        major = UniversityMajor.objects.create(
            university_revision=self.revision,
            order=1,
            is_active=True,
        )
        UniversityMajorTranslation.objects.create(
            major=major,
            language_code="uz",
            title="Dasturiy ta'minot muhandisligi",
            description="Katta dasturchilar tayyorlash kursi",
        )

        # Public serializer test
        self.university.public_translations = [self.translation]
        serializer = PublicUniversityDetailSerializer(
            self.university,
            context={"language_code": "uz"},
        )
        data = serializer.data

        self.assertEqual(data["city_native"], "Hangzhou, Zhejiang")
        self.assertEqual(data["chinese_name"], "浙江大学")
        self.assertEqual(data["established_year"], 1897)
        self.assertEqual(data["students_count"], 54000)
        self.assertEqual(data["international_students_count"], 7000)
        self.assertEqual(data["subtitle"], "Xitoyning nufuzli C9 League a'zosi bo'lgan top universiteti")
        self.assertEqual(data["features"], ["C9 League", "Top 50 QS", "Katta kampus"])
        self.assertEqual(data["accommodation_info"], "1-2 kishilik qulay xonalar, konditsioner, oshxona.")
        self.assertEqual(data["admission_note"], "IELTS 6.0 yoki HSK 4 talab qilinadi.")
        self.assertIsNotNone(data["logo"])
        self.assertIsNotNone(data["cover"])
        self.assertEqual(len(data["gallery"]), 1)
        self.assertEqual(len(data["majors"]), 1)
        self.assertEqual(data["majors"][0]["title"], "Dasturiy ta'minot muhandisligi")


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.InMemoryStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
)
class UniversityDeleteAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="del_superadmin",
            email="del_superadmin@example.com",
            password="Password123!",
        )
        cls.unauthorized_user = User.objects.create_user(
            username="del_no_perms",
            email="del_no_perms@example.com",
            password="Password123!",
        )
        cls.inactive_user = User.objects.create_user(
            username="del_inactive",
            email="del_inactive@example.com",
            password="Password123!",
            is_active=False,
        )

        # Editor with change_university only
        cls.univ_editor = User.objects.create_user(
            username="del_univ_editor",
            email="del_univ_editor@example.com",
            password="Password123!",
        )
        editor_group = Group.objects.create(name="Delete Test Univ Editor")
        editor_group.permissions.add(
            Permission.objects.get(
                content_type__app_label="universities",
                codename="view_university",
            ),
            Permission.objects.get(
                content_type__app_label="universities",
                codename="change_university",
            ),
        )
        cls.univ_editor.groups.add(editor_group)

        # Granular university delete role
        cls.univ_deleter = User.objects.create_user(
            username="del_univ_deleter",
            email="del_univ_deleter@example.com",
            password="Password123!",
        )
        univ_del_group = Group.objects.create(name="Delete Test Univ Deleter")
        univ_del_group.permissions.add(
            Permission.objects.get(
                content_type__app_label="universities",
                codename="delete_university",
            ),
            Permission.objects.get(
                content_type__app_label="universities",
                codename="delete_universityrevision",
            ),
            Permission.objects.get(
                content_type__app_label="universities",
                codename="view_universitytranslation",
            ),
            Permission.objects.get(
                content_type__app_label="universities",
                codename="delete_universitytranslation",
            ),
            Permission.objects.get(
                content_type__app_label="universities",
                codename="delete_universitytranslationrevision",
            ),
        )
        cls.univ_deleter.groups.add(univ_del_group)

        # Inactive user also gets full delete group to verify is_active check
        cls.inactive_user.groups.add(univ_del_group)

        # FAQ editor (change_faq) & FAQ deleter (delete_faq + granular)
        cls.faq_editor = User.objects.create_user(
            username="del_faq_editor",
            email="del_faq_editor@example.com",
            password="Password123!",
        )
        faq_editor_group = Group.objects.create(name="Delete Test FAQ Editor")
        faq_editor_group.permissions.add(
            Permission.objects.get(
                content_type__app_label="universities",
                codename="change_faq",
            ),
            Permission.objects.get(
                content_type__app_label="universities",
                codename="view_faq",
            ),
        )
        cls.faq_editor.groups.add(faq_editor_group)

        cls.faq_deleter = User.objects.create_user(
            username="del_faq_deleter",
            email="del_faq_deleter@example.com",
            password="Password123!",
        )
        faq_del_group = Group.objects.create(name="Delete Test FAQ Deleter")
        faq_del_group.permissions.add(
            Permission.objects.get(
                content_type__app_label="universities",
                codename="delete_faq",
            ),
            Permission.objects.get(
                content_type__app_label="universities",
                codename="view_faqtranslation",
            ),
            Permission.objects.get(
                content_type__app_label="universities",
                codename="delete_faqtranslation",
            ),
            Permission.objects.get(
                content_type__app_label="universities",
                codename="delete_faqtranslationrevision",
            ),
        )
        cls.faq_deleter.groups.add(faq_del_group)
        cls.inactive_user.groups.add(faq_del_group)

    def setUp(self):
        self.client = APIClient()

    def _create_university_bundle(
        self,
        *,
        univ_status=University.Status.ARCHIVED,
        rev_status=UniversityRevision.Status.ARCHIVED,
        trans_rev_status=UniversityTranslationRevision.Status.ARCHIVED,
        set_published_pointers=False,
    ):
        university = University.objects.create(
            status=univ_status,
            created_by=self.superuser,
        )
        rev1 = UniversityRevision.objects.create(
            university=university,
            revision_number=1,
            city="Beijing",
            country="China",
            status=rev_status,
            created_by=self.superuser,
        )
        period = UniversityAdmissionPeriod.objects.create(
            university_revision=rev1,
            name="Fall 2027",
            application_start_date="2027-01-01",
            application_end_date="2027-06-01",
        )
        major = UniversityMajor.objects.create(
            university_revision=rev1,
            order=1,
            is_active=True,
        )
        UniversityMajorTranslation.objects.create(
            major=major,
            language_code="uz",
            title="Kompyuter ilmlari",
        )
        media = UniversityMedia.objects.create(
            university_revision=rev1,
            file=create_dummy_image(),
            media_type=UniversityMedia.MediaType.LOGO,
        )
        uz_trans = UniversityTranslation.objects.create(
            university=university,
            language_code="uz",
        )
        uz_rev = UniversityTranslationRevision.objects.create(
            translation=uz_trans,
            revision_number=1,
            name="Pekin Universiteti",
            slug=f"pekin-{university.pk}",
            status=trans_rev_status,
            created_by=self.superuser,
        )
        en_trans = UniversityTranslation.objects.create(
            university=university,
            language_code="en",
        )
        en_rev = UniversityTranslationRevision.objects.create(
            translation=en_trans,
            revision_number=1,
            name="Peking University",
            slug=f"peking-{university.pk}",
            status=trans_rev_status,
            created_by=self.superuser,
        )

        if set_published_pointers:
            uz_trans.published_revision = uz_rev
            uz_trans.slug = uz_rev.slug
            uz_trans.save()
            en_trans.published_revision = en_rev
            en_trans.slug = en_rev.slug
            en_trans.save()
            university.published_revision = rev1
            university.save()

        return {
            "university": university,
            "revision": rev1,
            "period": period,
            "major": major,
            "media": media,
            "uz_trans": uz_trans,
            "uz_rev": uz_rev,
            "en_trans": en_trans,
            "en_rev": en_rev,
        }

    def test_auth_and_rbac_across_all_delete_endpoints(self):
        bundle = self._create_university_bundle()
        faq = FAQ.objects.create(order=1, is_active=False)
        faq_trans = FAQTranslation.objects.create(faq=faq, language_code="uz")
        faq_rev = FAQTranslationRevision.objects.create(
            translation=faq_trans,
            revision_number=1,
            question="Savol?",
            answer="Javob.",
            status=FAQTranslationRevision.Status.ARCHIVED,
            created_by=self.superuser,
        )

        univ_endpoints = [
            f"/api/v1/admin/universities/{bundle['university'].pk}/",
            f"/api/v1/admin/university-revisions/{bundle['revision'].pk}/",
            f"/api/v1/admin/university-translations/{bundle['en_trans'].pk}/",
            f"/api/v1/admin/translation-revisions/{bundle['en_rev'].pk}/",
        ]
        faq_endpoints = [
            f"/api/v1/admin/faqs/{faq.pk}/",
            f"/api/v1/admin/faq-translations/{faq_trans.pk}/",
            f"/api/v1/admin/faq-revisions/{faq_rev.pk}/",
        ]

        # 1. Anonymous -> 401
        for url in univ_endpoints + faq_endpoints:
            self.assertEqual(
                self.client.delete(url).status_code,
                status.HTTP_401_UNAUTHORIZED,
                msg=f"Expected 401 for {url}",
            )

        # 2. Unauthorized -> 403
        self.client.force_authenticate(user=self.unauthorized_user)
        for url in univ_endpoints + faq_endpoints:
            self.assertEqual(
                self.client.delete(url).status_code,
                status.HTTP_403_FORBIDDEN,
                msg=f"Expected 403 for {url}",
            )

        # 3. Inactive user -> 403 (even with delete permissions)
        self.client.force_authenticate(user=self.inactive_user)
        for url in univ_endpoints + faq_endpoints:
            self.assertEqual(
                self.client.delete(url).status_code,
                status.HTTP_403_FORBIDDEN,
                msg=f"Expected 403 for inactive user on {url}",
            )

        # 4. change_university ONLY -> 403 on all university delete endpoints (F-01)
        self.client.force_authenticate(user=self.univ_editor)
        for url in univ_endpoints:
            self.assertEqual(
                self.client.delete(url).status_code,
                status.HTTP_403_FORBIDDEN,
                msg=f"Expected 403 for change_university on {url}",
            )

        # 5. change_faq ONLY -> 403 on all FAQ delete endpoints (F-01)
        self.client.force_authenticate(user=self.faq_editor)
        for url in faq_endpoints:
            self.assertEqual(
                self.client.delete(url).status_code,
                status.HTTP_403_FORBIDDEN,
                msg=f"Expected 403 for change_faq on {url}",
            )

        # 6. Invalid UUID & missing UUID -> 404
        self.client.force_authenticate(user=self.superuser)
        for prefix in [
            "universities",
            "university-revisions",
            "university-translations",
            "translation-revisions",
            "faqs",
            "faq-translations",
            "faq-revisions",
        ]:
            self.assertEqual(
                self.client.delete(f"/api/v1/admin/{prefix}/not-a-uuid/").status_code,
                status.HTTP_404_NOT_FOUND,
            )
            self.assertEqual(
                self.client.delete(f"/api/v1/admin/{prefix}/{uuid.uuid4()}/").status_code,
                status.HTTP_404_NOT_FOUND,
            )

    def test_delete_university_archived_policy_integrity_and_audit_log(self):
        from apps.admissions.models import Admission
        from apps.inquiries.models import Inquiry, InquiryCategory

        # 1. PUBLISHED, REVIEW, DRAFT universities blocked -> 422
        for forbidden_status in (
            University.Status.PUBLISHED,
            University.Status.REVIEW,
            University.Status.DRAFT,
        ):
            b = self._create_university_bundle(univ_status=forbidden_status)
            self.client.force_authenticate(user=self.univ_deleter)
            res = self.client.delete(f"/api/v1/admin/universities/{b['university'].pk}/")
            self.assertEqual(res.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
            self.assertTrue(University.objects.filter(pk=b["university"].pk).exists())

        # 2. ARCHIVED university with PUBLISHED or REVIEW or DRAFT child revision blocked -> 422
        for child_status in (
            UniversityRevision.Status.PUBLISHED,
            UniversityRevision.Status.REVIEW,
            UniversityRevision.Status.DRAFT,
        ):
            b = self._create_university_bundle(
                univ_status=University.Status.ARCHIVED,
                rev_status=child_status,
                set_published_pointers=(child_status == UniversityRevision.Status.PUBLISHED),
            )
            self.client.force_authenticate(user=self.univ_deleter)
            res = self.client.delete(f"/api/v1/admin/universities/{b['university'].pk}/")
            self.assertEqual(res.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
            self.assertTrue(University.objects.filter(pk=b["university"].pk).exists())

        # 3. ARCHIVED university with Admission PROTECT blocked -> 422
        b_prot = self._create_university_bundle()
        Admission.objects.create(
            full_name="Ali Valiyev",
            phone_number="+998901234567",
            university=b_prot["university"],
        )
        self.client.force_authenticate(user=self.univ_deleter)
        res = self.client.delete(f"/api/v1/admin/universities/{b_prot['university'].pk}/")
        self.assertEqual(res.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertTrue(University.objects.filter(pk=b_prot["university"].pk).exists())

        # 4. ARCHIVED university with all ARCHIVED children & Inquiry (SET_NULL) -> 204
        b_ok = self._create_university_bundle()
        category = InquiryCategory.objects.create(slug="audit-cat", is_active=True)
        inquiry = Inquiry.objects.create(
            category=category,
            university=b_ok["university"],
            full_name="Vali Aliyev",
            phone_number="+998909876543",
            contact_method=Inquiry.ContactMethod.PHONE,
            consent_accepted=True,
            consent_version="v1",
            idempotency_key=uuid.uuid4(),
        )
        media_file_name = b_ok["media"].file.name

        with self.captureOnCommitCallbacks(execute=True):
            res = self.client.delete(f"/api/v1/admin/universities/{b_ok['university'].pk}/")

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(res.content, b"")

        # All university tables cleaned up
        self.assertFalse(University.objects.filter(pk=b_ok["university"].pk).exists())
        self.assertFalse(UniversityRevision.objects.filter(pk=b_ok["revision"].pk).exists())
        self.assertFalse(UniversityAdmissionPeriod.objects.filter(pk=b_ok["period"].pk).exists())
        self.assertFalse(UniversityMajor.objects.filter(pk=b_ok["major"].pk).exists())
        self.assertFalse(UniversityMedia.objects.filter(pk=b_ok["media"].pk).exists())
        self.assertFalse(UniversityTranslation.objects.filter(pk=b_ok["uz_trans"].pk).exists())
        self.assertFalse(UniversityTranslationRevision.objects.filter(pk=b_ok["uz_rev"].pk).exists())

        # Inquiry survived with university=NULL
        inquiry.refresh_from_db()
        self.assertIsNone(inquiry.university)

        # Storage file cleaned up after commit
        self.assertFalse(default_storage.exists(media_file_name))
        self.assertEqual(
            MediaCleanupTask.objects.get(file_path=media_file_name).status,
            MediaCleanupTask.Status.COMPLETED,
        )

        # Audit logs created for parent + all child objects without duplicates
        logs = UniversityAuditLog.objects.filter(action=UniversityAuditLog.Action.DELETE)
        self.assertEqual(
            logs.filter(
                object_type=UniversityAuditLog.ObjectType.UNIVERSITY,
                object_id=str(b_ok["university"].pk),
            ).count(),
            1,
        )
        univ_log = logs.get(
            object_type=UniversityAuditLog.ObjectType.UNIVERSITY,
            object_id=str(b_ok["university"].pk),
        )
        self.assertEqual(univ_log.actor, self.univ_deleter)
        self.assertEqual(univ_log.actor_identifier, "del_univ_deleter")
        self.assertTrue(
            logs.filter(
                object_type=UniversityAuditLog.ObjectType.UNIVERSITY_REVISION,
                object_id=str(b_ok["revision"].pk),
            ).exists()
        )
        self.assertTrue(
            logs.filter(
                object_type=UniversityAuditLog.ObjectType.UNIVERSITY_ADMISSION_PERIOD,
                object_id=str(b_ok["period"].pk),
            ).exists()
        )
        self.assertTrue(
            logs.filter(
                object_type=UniversityAuditLog.ObjectType.UNIVERSITY_MAJOR,
                object_id=str(b_ok["major"].pk),
            ).exists()
        )
        self.assertTrue(
            logs.filter(
                object_type=UniversityAuditLog.ObjectType.UNIVERSITY_MEDIA,
                object_id=str(b_ok["media"].pk),
            ).exists()
        )

    def test_delete_university_revision_archived_only_and_audit_log(self):
        b = self._create_university_bundle(
            univ_status=University.Status.PUBLISHED,
            rev_status=UniversityRevision.Status.PUBLISHED,
            trans_rev_status=UniversityTranslationRevision.Status.PUBLISHED,
            set_published_pointers=True,
        )
        review_rev = UniversityRevision.objects.create(
            university=b["university"],
            revision_number=2,
            city="Hangzhou",
            country="China",
            status=UniversityRevision.Status.REVIEW,
            created_by=self.superuser,
        )
        draft_rev = UniversityRevision.objects.create(
            university=b["university"],
            revision_number=3,
            city="Shenzhen",
            country="China",
            status=UniversityRevision.Status.DRAFT,
            created_by=self.superuser,
        )
        archived_rev = UniversityRevision.objects.create(
            university=b["university"],
            revision_number=4,
            city="Shanghai",
            country="China",
            status=UniversityRevision.Status.ARCHIVED,
            created_by=self.superuser,
        )
        period = UniversityAdmissionPeriod.objects.create(
            university_revision=archived_rev,
            name="Spring 2028",
            application_start_date="2028-01-01",
            application_end_date="2028-03-01",
        )
        media = UniversityMedia.objects.create(
            university_revision=archived_rev,
            file=create_dummy_image(),
            media_type=UniversityMedia.MediaType.GALLERY,
        )
        media_name = media.file.name

        self.client.force_authenticate(user=self.univ_deleter)

        # PUBLISHED, REVIEW, DRAFT revisions blocked -> 422
        for bad_rev in (b["revision"], review_rev, draft_rev):
            self.assertEqual(
                self.client.delete(f"/api/v1/admin/university-revisions/{bad_rev.pk}/").status_code,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # ARCHIVED revision succeeds -> 204
        with self.captureOnCommitCallbacks(execute=True):
            res = self.client.delete(f"/api/v1/admin/university-revisions/{archived_rev.pk}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(UniversityRevision.objects.filter(pk=archived_rev.pk).exists())
        self.assertFalse(UniversityAdmissionPeriod.objects.filter(pk=period.pk).exists())
        self.assertFalse(UniversityMedia.objects.filter(pk=media.pk).exists())
        self.assertFalse(default_storage.exists(media_name))
        self.assertEqual(
            UniversityAuditLog.objects.filter(
                object_type=UniversityAuditLog.ObjectType.UNIVERSITY_REVISION,
                object_id=str(archived_rev.pk),
            ).count(),
            1,
        )

    def test_delete_translation_and_translation_revision_archived_only(self):
        b = self._create_university_bundle(
            univ_status=University.Status.PUBLISHED,
            rev_status=UniversityRevision.Status.PUBLISHED,
            trans_rev_status=UniversityTranslationRevision.Status.PUBLISHED,
            set_published_pointers=True,
        )
        en_review_rev = UniversityTranslationRevision.objects.create(
            translation=b["en_trans"],
            revision_number=2,
            name="Peking Review",
            slug=f"peking-rev-{b['university'].pk}",
            status=UniversityTranslationRevision.Status.REVIEW,
            created_by=self.superuser,
        )
        en_draft_rev = UniversityTranslationRevision.objects.create(
            translation=b["en_trans"],
            revision_number=3,
            name="Peking Draft",
            slug=f"peking-draft-{b['university'].pk}",
            status=UniversityTranslationRevision.Status.DRAFT,
            created_by=self.superuser,
        )
        en_archived_rev = UniversityTranslationRevision.objects.create(
            translation=b["en_trans"],
            revision_number=4,
            name="Peking Archived",
            slug=f"peking-arch-{b['university'].pk}",
            status=UniversityTranslationRevision.Status.ARCHIVED,
            created_by=self.superuser,
        )

        # Standalone archived translation
        ru_trans = UniversityTranslation.objects.create(
            university=b["university"],
            language_code="ru",
        )
        ru_archived_rev = UniversityTranslationRevision.objects.create(
            translation=ru_trans,
            revision_number=1,
            name="Пекинский университет",
            slug=f"pekin-ru-{b['university'].pk}",
            status=UniversityTranslationRevision.Status.ARCHIVED,
            created_by=self.superuser,
        )

        self.client.force_authenticate(user=self.univ_deleter)

        # PUBLISHED, REVIEW, DRAFT translation revisions blocked -> 422
        for bad_rev in (b["en_rev"], en_review_rev, en_draft_rev):
            self.assertEqual(
                self.client.delete(f"/api/v1/admin/translation-revisions/{bad_rev.pk}/").status_code,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # ARCHIVED translation revision deleted -> 204
        res = self.client.delete(f"/api/v1/admin/translation-revisions/{en_archived_rev.pk}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(UniversityTranslationRevision.objects.filter(pk=en_archived_rev.pk).exists())

        # PUBLISHED translations (both uz and en) blocked -> 422
        self.assertEqual(
            self.client.delete(f"/api/v1/admin/university-translations/{b['uz_trans'].pk}/").status_code,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
        self.assertEqual(
            self.client.delete(f"/api/v1/admin/university-translations/{b['en_trans'].pk}/").status_code,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

        # ARCHIVED translation (ru) deleted -> 204 with audit log for child + parent
        res = self.client.delete(f"/api/v1/admin/university-translations/{ru_trans.pk}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(UniversityTranslation.objects.filter(pk=ru_trans.pk).exists())
        self.assertFalse(UniversityTranslationRevision.objects.filter(pk=ru_archived_rev.pk).exists())
        self.assertTrue(
            UniversityAuditLog.objects.filter(
                object_type=UniversityAuditLog.ObjectType.UNIVERSITY_TRANSLATION,
                object_id=str(ru_trans.pk),
            ).exists()
        )
        self.assertTrue(
            UniversityAuditLog.objects.filter(
                object_type=UniversityAuditLog.ObjectType.UNIVERSITY_TRANSLATION_REVISION,
                object_id=str(ru_archived_rev.pk),
            ).exists()
        )

    def test_delete_faq_archived_only_and_audit_log_survives_actor_deletion(self):
        # 1. Active FAQ blocked -> 422
        active_faq = FAQ.objects.create(order=1, is_active=True)
        uz_trans = FAQTranslation.objects.create(faq=active_faq, language_code="uz")
        uz_pub_rev = FAQTranslationRevision.objects.create(
            translation=uz_trans,
            revision_number=1,
            question="Savol?",
            answer="Javob.",
            status=FAQTranslationRevision.Status.PUBLISHED,
            created_by=self.superuser,
        )
        uz_trans.published_revision = uz_pub_rev
        uz_trans.save()

        self.client.force_authenticate(user=self.faq_deleter)
        self.assertEqual(
            self.client.delete(f"/api/v1/admin/faqs/{active_faq.pk}/").status_code,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
        self.assertEqual(
            self.client.delete(f"/api/v1/admin/faq-translations/{uz_trans.pk}/").status_code,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
        self.assertEqual(
            self.client.delete(f"/api/v1/admin/faq-revisions/{uz_pub_rev.pk}/").status_code,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

        # 2. Deactivated FAQ with PUBLISHED/REVIEW/DRAFT child revision blocked -> 422
        active_faq.is_active = False
        active_faq.save()
        self.assertEqual(
            self.client.delete(f"/api/v1/admin/faqs/{active_faq.pk}/").status_code,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

        # 3. REVIEW & DRAFT FAQ revisions blocked -> 422; ARCHIVED FAQ revision -> 204
        review_rev = FAQTranslationRevision.objects.create(
            translation=uz_trans,
            revision_number=2,
            question="Review savol?",
            answer="Review javob.",
            status=FAQTranslationRevision.Status.REVIEW,
            created_by=self.superuser,
        )
        draft_rev = FAQTranslationRevision.objects.create(
            translation=uz_trans,
            revision_number=3,
            question="Draft savol?",
            answer="Draft javob.",
            status=FAQTranslationRevision.Status.DRAFT,
            created_by=self.superuser,
        )
        arch_rev = FAQTranslationRevision.objects.create(
            translation=uz_trans,
            revision_number=4,
            question="Archived savol?",
            answer="Archived javob.",
            status=FAQTranslationRevision.Status.ARCHIVED,
            created_by=self.superuser,
        )
        self.assertEqual(
            self.client.delete(f"/api/v1/admin/faq-revisions/{review_rev.pk}/").status_code,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
        self.assertEqual(
            self.client.delete(f"/api/v1/admin/faq-revisions/{draft_rev.pk}/").status_code,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
        self.assertEqual(
            self.client.delete(f"/api/v1/admin/faq-revisions/{arch_rev.pk}/").status_code,
            status.HTTP_204_NO_CONTENT,
        )

        # 4. Archived FAQTranslation -> 204, and archived FAQ -> 204
        arch_faq = FAQ.objects.create(order=2, is_active=False)
        en_trans = FAQTranslation.objects.create(faq=arch_faq, language_code="en")
        en_arch_rev = FAQTranslationRevision.objects.create(
            translation=en_trans,
            revision_number=1,
            question="Old Q?",
            answer="Old A.",
            status=FAQTranslationRevision.Status.ARCHIVED,
            created_by=self.superuser,
        )
        ru_trans = FAQTranslation.objects.create(faq=arch_faq, language_code="ru")
        ru_arch_rev = FAQTranslationRevision.objects.create(
            translation=ru_trans,
            revision_number=1,
            question="Старый вопрос?",
            answer="Старый ответ.",
            status=FAQTranslationRevision.Status.ARCHIVED,
            created_by=self.superuser,
        )

        # Superuser can also delete
        temp_actor = User.objects.create_superuser(
            username="temp_faq_super",
            email="temp_faq_super@example.com",
            password="Password123!",
        )
        self.client.force_authenticate(user=temp_actor)
        self.assertEqual(
            self.client.delete(f"/api/v1/admin/faq-translations/{en_trans.pk}/").status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(FAQTranslation.objects.filter(pk=en_trans.pk).exists())
        self.assertFalse(FAQTranslationRevision.objects.filter(pk=en_arch_rev.pk).exists())

        self.assertEqual(
            self.client.delete(f"/api/v1/admin/faqs/{arch_faq.pk}/").status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(FAQ.objects.filter(pk=arch_faq.pk).exists())
        self.assertFalse(FAQTranslation.objects.filter(pk=ru_trans.pk).exists())
        self.assertFalse(FAQTranslationRevision.objects.filter(pk=ru_arch_rev.pk).exists())

        # Audit logs survive even after actor user is deleted
        temp_actor.delete()
        faq_log = UniversityAuditLog.objects.get(
            object_type=UniversityAuditLog.ObjectType.FAQ,
            object_id=str(arch_faq.pk),
        )
        self.assertIsNone(faq_log.actor)
        self.assertEqual(faq_log.actor_identifier, "temp_faq_super")

    def test_protected_error_and_rollback_preserve_db_and_audit_logs(self):
        b = self._create_university_bundle()
        faq = FAQ.objects.create(order=3, is_active=False)
        faq_trans = FAQTranslation.objects.create(faq=faq, language_code="uz")
        faq_rev = FAQTranslationRevision.objects.create(
            translation=faq_trans,
            revision_number=1,
            question="Q",
            answer="A",
            status=FAQTranslationRevision.Status.ARCHIVED,
            created_by=self.superuser,
        )

        self.client.force_authenticate(user=self.superuser)
        media_name = b["media"].file.name

        # Simulate ProtectedError during University.delete()
        with patch.object(
            University,
            "delete",
            side_effect=ProtectedError("protected", {b["university"]}),
        ):
            res = self.client.delete(f"/api/v1/admin/universities/{b['university'].pk}/")

        self.assertEqual(res.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        # Transaction rolled back: university, children, media, and NO audit logs
        self.assertTrue(University.objects.filter(pk=b["university"].pk).exists())
        self.assertTrue(UniversityRevision.objects.filter(pk=b["revision"].pk).exists())
        self.assertTrue(default_storage.exists(media_name))
        self.assertFalse(
            UniversityAuditLog.objects.filter(object_id=str(b["university"].pk)).exists()
        )
        self.assertFalse(MediaCleanupTask.objects.filter(file_path=media_name).exists())

        # Simulate ProtectedError during FAQ.delete()
        with patch.object(
            FAQ,
            "delete",
            side_effect=ProtectedError("protected", {faq}),
        ):
            res = self.client.delete(f"/api/v1/admin/faqs/{faq.pk}/")

        self.assertEqual(res.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertTrue(FAQ.objects.filter(pk=faq.pk).exists())
        self.assertTrue(FAQTranslation.objects.filter(pk=faq_trans.pk).exists())
        self.assertTrue(FAQTranslationRevision.objects.filter(pk=faq_rev.pk).exists())
        self.assertFalse(
            UniversityAuditLog.objects.filter(object_id=str(faq.pk)).exists()
        )


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.InMemoryStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
)
class UniversityDeleteConcurrencyAndMediaTests(TransactionTestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="tx_superadmin",
            email="tx_superadmin@example.com",
            password="Password123!",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.superuser)

    def test_shared_storage_path_not_deleted_while_referenced_and_cross_model_safe(self):
        from apps.partners.models.partner import Partner

        shared_name = default_storage.save("universities/media/shared_test.jpg", create_dummy_image())
        univ = University.objects.create(
            status=University.Status.ARCHIVED,
            created_by=self.superuser,
        )
        rev = UniversityRevision.objects.create(
            university=univ,
            revision_number=1,
            city="Beijing",
            country="China",
            status=UniversityRevision.Status.ARCHIVED,
            created_by=self.superuser,
        )
        media = UniversityMedia.objects.create(
            university_revision=rev,
            file=shared_name,
            media_type=UniversityMedia.MediaType.LOGO,
        )
        # Cross-model reference to the exact same storage key
        partner = Partner.objects.create(
            name="Shared Logo Partner",
            logo=shared_name,
        )

        res = self.client.delete(f"/api/v1/admin/university-revisions/{rev.pk}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(default_storage.exists(shared_name))

        # Remove partner reference and create + delete a second archived revision sharing it
        partner.delete()
        rev2 = UniversityRevision.objects.create(
            university=univ,
            revision_number=2,
            city="Shanghai",
            country="China",
            status=UniversityRevision.Status.ARCHIVED,
            created_by=self.superuser,
        )
        UniversityMedia.objects.create(
            university_revision=rev2,
            file=shared_name,
            media_type=UniversityMedia.MediaType.LOGO,
        )
        res2 = self.client.delete(f"/api/v1/admin/university-revisions/{rev2.pk}/")
        self.assertEqual(res2.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(default_storage.exists(shared_name))

    def test_storage_exception_logged_and_retried_without_rolling_back_db(self):
        univ = University.objects.create(
            status=University.Status.ARCHIVED,
            created_by=self.superuser,
        )
        rev = UniversityRevision.objects.create(
            university=univ,
            revision_number=1,
            city="Beijing",
            country="China",
            status=UniversityRevision.Status.ARCHIVED,
            created_by=self.superuser,
        )
        media = UniversityMedia.objects.create(
            university_revision=rev,
            file=create_dummy_image(),
            media_type=UniversityMedia.MediaType.LOGO,
        )
        file_path = media.file.name

        with (
            patch.object(default_storage, "delete", side_effect=OSError("Storage down")),
            self.assertLogs("apps.universities.services.media_lifecycle_service", level="ERROR") as logs,
        ):
            res = self.client.delete(f"/api/v1/admin/universities/{univ.pk}/")

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(University.objects.filter(pk=univ.pk).exists())
        self.assertTrue(any("Failed to delete university media file" in m for m in logs.output))

        task = MediaCleanupTask.objects.get(file_path=file_path)
        self.assertEqual(task.status, MediaCleanupTask.Status.FAILED)
        self.assertEqual(task.attempts, 1)
        self.assertEqual(task.last_error, "OSError")

        # Retry succeeds when storage recovers
        retried = MediaLifecycleService.retry_failed_cleanups()
        self.assertEqual(retried, 1)
        task.refresh_from_db()
        self.assertEqual(task.status, MediaCleanupTask.Status.COMPLETED)
        self.assertEqual(task.attempts, 2)
        self.assertFalse(default_storage.exists(file_path))

    def test_register_reference_cancels_pending_cleanup_task(self):
        shared_name = default_storage.save("universities/media/race_file.jpg", create_dummy_image())
        task = MediaCleanupTask.objects.create(
            file_path=shared_name,
            status=MediaCleanupTask.Status.PENDING,
        )
        univ = University.objects.create(
            status=University.Status.DRAFT,
            created_by=self.superuser,
        )
        rev = UniversityRevision.objects.create(
            university=univ,
            revision_number=1,
            city="Beijing",
            country="China",
            status=UniversityRevision.Status.DRAFT,
            created_by=self.superuser,
        )
        UniversityMediaService.create_media(
            actor=self.superuser,
            revision_id=rev.pk,
            file=shared_name,
            media_type=UniversityMedia.MediaType.LOGO,
        )
        task.refresh_from_db()
        self.assertEqual(task.status, MediaCleanupTask.Status.CANCELLED)

        MediaLifecycleService.execute_cleanup_tasks([task.pk])
        self.assertTrue(default_storage.exists(shared_name))

    def test_parallel_delete_second_call_returns_404(self):
        univ = University.objects.create(
            status=University.Status.ARCHIVED,
            created_by=self.superuser,
        )
        url = f"/api/v1/admin/universities/{univ.pk}/"

        # Simulate first DELETE succeeding, second concurrent DELETE hitting empty DB inside transaction
        res1 = self.client.delete(url)
        res2 = self.client.delete(url)

        self.assertEqual(res1.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(res2.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            UniversityAuditLog.objects.filter(
                object_type=UniversityAuditLog.ObjectType.UNIVERSITY,
                object_id=str(univ.pk),
            ).count(),
            1,
        )

    def test_protected_error_on_revision_translation_and_faq_translation_returns_422(self):
        univ = University.objects.create(
            status=University.Status.ARCHIVED,
            created_by=self.superuser,
        )
        rev = UniversityRevision.objects.create(
            university=univ,
            revision_number=1,
            city="Beijing",
            country="China",
            status=UniversityRevision.Status.ARCHIVED,
            created_by=self.superuser,
        )
        trans = UniversityTranslation.objects.create(
            university=univ,
            language_code="en",
        )
        UniversityTranslationRevision.objects.create(
            translation=trans,
            revision_number=1,
            name="Peking",
            slug=f"peking-prot-{univ.pk}",
            status=UniversityTranslationRevision.Status.ARCHIVED,
            created_by=self.superuser,
        )
        faq = FAQ.objects.create(order=1, is_active=False)
        faq_trans = FAQTranslation.objects.create(faq=faq, language_code="en")
        FAQTranslationRevision.objects.create(
            translation=faq_trans,
            revision_number=1,
            question="Q",
            answer="A",
            status=FAQTranslationRevision.Status.ARCHIVED,
            created_by=self.superuser,
        )

        with patch.object(
            UniversityRevision,
            "delete",
            side_effect=ProtectedError("protected", {rev}),
        ):
            res = self.client.delete(f"/api/v1/admin/university-revisions/{rev.pk}/")
        self.assertEqual(res.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertTrue(UniversityRevision.objects.filter(pk=rev.pk).exists())

        with patch.object(
            UniversityTranslation,
            "delete",
            side_effect=ProtectedError("protected", {trans}),
        ):
            res = self.client.delete(f"/api/v1/admin/university-translations/{trans.pk}/")
        self.assertEqual(res.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertTrue(UniversityTranslation.objects.filter(pk=trans.pk).exists())

        with patch.object(
            FAQTranslation,
            "delete",
            side_effect=ProtectedError("protected", {faq_trans}),
        ):
            res = self.client.delete(f"/api/v1/admin/faq-translations/{faq_trans.pk}/")
        self.assertEqual(res.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertTrue(FAQTranslation.objects.filter(pk=faq_trans.pk).exists())

    def test_audit_log_admin_is_readonly_and_create_vs_delete_revision_safe(self):
        from django.contrib.admin.sites import site
        from django.test import RequestFactory

        audit_admin = site._registry[UniversityAuditLog]
        rf = RequestFactory()
        req = rf.get("/admin/")
        req.user = self.superuser
        self.assertFalse(audit_admin.has_add_permission(req))
        self.assertFalse(audit_admin.has_change_permission(req))
        self.assertFalse(audit_admin.has_delete_permission(req))

        # Revision create vs archived revision delete on active university preserves integrity
        univ = University.objects.create(
            status=University.Status.PUBLISHED,
            created_by=self.superuser,
        )
        arch_rev = UniversityRevision.objects.create(
            university=univ,
            revision_number=1,
            city="Beijing",
            country="China",
            status=UniversityRevision.Status.ARCHIVED,
            created_by=self.superuser,
        )
        new_draft = UniversityRevisionService.create_revision(
            actor=self.superuser,
            university_id=univ.pk,
            city="Shanghai",
            country="China",
        )
        self.assertEqual(new_draft.revision_number, 2)
        res = self.client.delete(f"/api/v1/admin/university-revisions/{arch_rev.pk}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(UniversityRevision.objects.filter(pk=new_draft.pk).exists())

    def _create_user_with_perms(self, username, *codenames):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="Password123!",
        )
        if codenames:
            group = Group.objects.create(name=f"Group {username}")
            perms = Permission.objects.filter(codename__in=codenames)
            group.permissions.add(*perms)
            user.groups.add(group)
        return user

    def test_published_archived_delete_workflow_and_rbac(self):
        # 1. Users for RBAC verification
        no_perm_user = self._create_user_with_perms("arch_noperm")
        univ_editor = self._create_user_with_perms("arch_univ_editor", "change_university")
        univ_deleter = self._create_user_with_perms("arch_univ_deleter", "delete_university")
        faq_editor = self._create_user_with_perms("arch_faq_editor", "change_faq")
        faq_deleter = self._create_user_with_perms("arch_faq_deleter", "delete_faq")

        # 2. Setup PUBLISHED university + published child revisions
        univ = University.objects.create(
            status=University.Status.PUBLISHED,
            created_by=self.superuser,
        )
        rev = UniversityRevision.objects.create(
            university=univ,
            revision_number=1,
            city="Beijing",
            country="China",
            status=UniversityRevision.Status.PUBLISHED,
            created_by=self.superuser,
        )
        univ.published_revision = rev
        univ.save(update_fields=["published_revision"])

        uz_trans = UniversityTranslation.objects.create(
            university=univ,
            language_code="uz",
        )
        uz_rev = UniversityTranslationRevision.objects.create(
            translation=uz_trans,
            revision_number=1,
            name="Pekin Universiteti",
            slug=f"pekin-arch-{univ.pk}",
            status=UniversityTranslationRevision.Status.PUBLISHED,
            created_by=self.superuser,
        )
        uz_trans.published_revision = uz_rev
        uz_trans.slug = uz_rev.slug
        uz_trans.save(update_fields=["published_revision", "slug"])

        # Unauthorized -> 403
        self.client.force_authenticate(user=no_perm_user)
        for archive_url in (
            f"/api/v1/admin/universities/{univ.pk}/archive/",
            f"/api/v1/admin/university-revisions/{rev.pk}/archive/",
            f"/api/v1/admin/translation-revisions/{uz_rev.pk}/archive/",
        ):
            self.assertEqual(
                self.client.post(archive_url).status_code,
                status.HTTP_403_FORBIDDEN,
            )

        # Archiving active published revisions while parent university is PUBLISHED -> 422
        self.client.force_authenticate(user=univ_editor)
        self.assertEqual(
            self.client.post(f"/api/v1/admin/university-revisions/{rev.pk}/archive/").status_code,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
        self.assertEqual(
            self.client.post(f"/api/v1/admin/translation-revisions/{uz_rev.pk}/archive/").status_code,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

        # Archive parent university -> 200; children must NOT auto-archive
        res_u_arch = self.client.post(f"/api/v1/admin/universities/{univ.pk}/archive/")
        self.assertEqual(res_u_arch.status_code, status.HTTP_200_OK)
        univ.refresh_from_db()
        rev.refresh_from_db()
        uz_rev.refresh_from_db()
        self.assertEqual(univ.status, University.Status.ARCHIVED)
        self.assertEqual(rev.status, UniversityRevision.Status.PUBLISHED)
        self.assertEqual(uz_rev.status, UniversityTranslationRevision.Status.PUBLISHED)

        # change_university user still cannot DELETE -> 403
        self.assertEqual(
            self.client.delete(f"/api/v1/admin/universities/{univ.pk}/").status_code,
            status.HTTP_403_FORBIDDEN,
        )

        # Deleter still blocked from deleting ARCHIVED university while children are PUBLISHED -> 422
        self.client.force_authenticate(user=univ_deleter)
        self.assertEqual(
            self.client.delete(f"/api/v1/admin/universities/{univ.pk}/").status_code,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

        # Archive child revisions explicitly via API
        self.client.force_authenticate(user=univ_editor)
        self.assertEqual(
            self.client.post(f"/api/v1/admin/university-revisions/{rev.pk}/archive/").status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.post(f"/api/v1/admin/translation-revisions/{uz_rev.pk}/archive/").status_code,
            status.HTTP_200_OK,
        )
        univ.refresh_from_db()
        rev.refresh_from_db()
        uz_trans.refresh_from_db()
        uz_rev.refresh_from_db()
        self.assertIsNone(univ.published_revision)
        self.assertEqual(rev.status, UniversityRevision.Status.ARCHIVED)
        self.assertIsNone(uz_trans.published_revision)
        self.assertIsNone(uz_trans.slug)
        self.assertEqual(uz_rev.status, UniversityTranslationRevision.Status.ARCHIVED)

        # Verify ARCHIVE audit log entries exist
        for obj_type, obj_id in (
            (UniversityAuditLog.ObjectType.UNIVERSITY, str(univ.pk)),
            (UniversityAuditLog.ObjectType.UNIVERSITY_REVISION, str(rev.pk)),
            (UniversityAuditLog.ObjectType.UNIVERSITY_TRANSLATION_REVISION, str(uz_rev.pk)),
        ):
            self.assertTrue(
                UniversityAuditLog.objects.filter(
                    action=UniversityAuditLog.Action.ARCHIVE,
                    object_type=obj_type,
                    object_id=obj_id,
                ).exists()
            )

        # Finally DELETE archived university -> 204
        self.client.force_authenticate(user=univ_deleter)
        self.assertEqual(
            self.client.delete(f"/api/v1/admin/universities/{univ.pk}/").status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(University.objects.filter(pk=univ.pk).exists())

        # 3. FAQ PUBLISHED -> ARCHIVED -> DELETE workflow
        faq = FAQ.objects.create(order=10, is_active=True)
        faq_trans = FAQTranslation.objects.create(faq=faq, language_code="uz")
        faq_rev = FAQTranslationRevision.objects.create(
            translation=faq_trans,
            revision_number=1,
            question="Savol?",
            answer="Javob.",
            status=FAQTranslationRevision.Status.PUBLISHED,
            created_by=self.superuser,
        )
        faq_trans.published_revision = faq_rev
        faq_trans.save(update_fields=["published_revision"])

        self.client.force_authenticate(user=no_perm_user)
        self.assertEqual(
            self.client.post(f"/api/v1/admin/faq-revisions/{faq_rev.pk}/archive/").status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.client.force_authenticate(user=faq_editor)
        # Cannot archive active published_revision while FAQ is active
        self.assertEqual(
            self.client.post(f"/api/v1/admin/faq-revisions/{faq_rev.pk}/archive/").status_code,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
        # Deactivate FAQ via existing PATCH endpoint -> does NOT auto-archive child revisions
        res_faq_patch = self.client.patch(
            f"/api/v1/admin/faqs/{faq.pk}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(res_faq_patch.status_code, status.HTTP_200_OK)
        faq.refresh_from_db()
        faq_rev.refresh_from_db()
        self.assertFalse(faq.is_active)
        self.assertEqual(faq_rev.status, FAQTranslationRevision.Status.PUBLISHED)

        # Delete blocked while child revision is PUBLISHED -> 422
        self.client.force_authenticate(user=faq_deleter)
        self.assertEqual(
            self.client.delete(f"/api/v1/admin/faqs/{faq.pk}/").status_code,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

        # Archive FAQ revision explicitly -> 200
        self.client.force_authenticate(user=faq_editor)
        self.assertEqual(
            self.client.post(f"/api/v1/admin/faq-revisions/{faq_rev.pk}/archive/").status_code,
            status.HTTP_200_OK,
        )
        faq_trans.refresh_from_db()
        faq_rev.refresh_from_db()
        self.assertIsNone(faq_trans.published_revision)
        self.assertEqual(faq_rev.status, FAQTranslationRevision.Status.ARCHIVED)

        self.assertTrue(
            UniversityAuditLog.objects.filter(
                action=UniversityAuditLog.Action.ARCHIVE,
                object_type=UniversityAuditLog.ObjectType.FAQ,
                object_id=str(faq.pk),
            ).exists()
        )
        self.assertTrue(
            UniversityAuditLog.objects.filter(
                action=UniversityAuditLog.Action.ARCHIVE,
                object_type=UniversityAuditLog.ObjectType.FAQ_TRANSLATION_REVISION,
                object_id=str(faq_rev.pk),
            ).exists()
        )

        # Delete deactivated FAQ with all revisions ARCHIVED -> 204
        self.client.force_authenticate(user=faq_deleter)
        self.assertEqual(
            self.client.delete(f"/api/v1/admin/faqs/{faq.pk}/").status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(FAQ.objects.filter(pk=faq.pk).exists())

    def test_media_lifecycle_duplicate_task_missing_key_and_celery_retry(self):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from apps.universities.tasks import retry_failed_university_media_cleanups

        univ = University.objects.create(
            status=University.Status.DRAFT,
            created_by=self.superuser,
        )
        rev = UniversityRevision.objects.create(
            university=univ,
            revision_number=1,
            city="Beijing",
            country="China",
            status=UniversityRevision.Status.DRAFT,
            created_by=self.superuser,
        )

        # 1. Missing storage key rejected before creating dangling UniversityMedia row
        with self.assertRaises(DjangoValidationError):
            UniversityMediaService.create_media(
                actor=self.superuser,
                revision_id=rev.pk,
                file="universities/media/does_not_exist.jpg",
                media_type=UniversityMedia.MediaType.LOGO,
            )
        self.assertEqual(UniversityMedia.objects.filter(university_revision=rev).count(), 0)

        # 2. Duplicate cleanup execution is idempotent
        file_name = default_storage.save("universities/media/dup_cleanup.jpg", create_dummy_image())
        task = MediaCleanupTask.objects.create(
            file_path=file_name,
            status=MediaCleanupTask.Status.PENDING,
        )
        MediaLifecycleService.execute_cleanup_tasks([task.pk, task.pk])
        task.refresh_from_db()
        self.assertEqual(task.status, MediaCleanupTask.Status.COMPLETED)
        self.assertEqual(task.attempts, 1)
        self.assertFalse(default_storage.exists(file_name))

        # 3. Re-referenced path while cleanup is pending cancels task under lock
        shared_name = default_storage.save("universities/media/re_ref.jpg", create_dummy_image())
        pending_task = MediaCleanupTask.objects.create(
            file_path=shared_name,
            status=MediaCleanupTask.Status.PENDING,
        )
        UniversityMedia.objects.create(
            university_revision=rev,
            file=shared_name,
            media_type=UniversityMedia.MediaType.GALLERY,
        )
        MediaLifecycleService.execute_cleanup_tasks([pending_task.pk])
        pending_task.refresh_from_db()
        self.assertEqual(pending_task.status, MediaCleanupTask.Status.CANCELLED)
        self.assertTrue(default_storage.exists(shared_name))

        # 4. Celery retry task retries FAILED cleanup task cleanly
        fail_name = default_storage.save("universities/media/celery_retry.jpg", create_dummy_image())
        failed_task = MediaCleanupTask.objects.create(
            file_path=fail_name,
            status=MediaCleanupTask.Status.FAILED,
            attempts=1,
            last_error="OSError",
        )
        retried_count = retry_failed_university_media_cleanups()
        self.assertEqual(retried_count, 1)
        failed_task.refresh_from_db()
        self.assertEqual(failed_task.status, MediaCleanupTask.Status.COMPLETED)
        self.assertFalse(default_storage.exists(fail_name))

    def test_postgresql_parallel_concurrency_and_locks(self):
        from concurrent.futures import ThreadPoolExecutor
        import unittest
        from django.db import connection, connections
        from apps.universities.services.university_service import UniversityService

        if connection.vendor != "postgresql":
            raise unittest.SkipTest(
                f"PostgreSQL multi-connection concurrency requires postgresql backend (current: {connection.vendor})"
            )

        # 1. Parallel DELETE on the same ARCHIVED university
        univ = University.objects.create(
            status=University.Status.ARCHIVED,
            created_by=self.superuser,
        )

        def worker_delete():
            connections.close_all()
            try:
                client = APIClient()
                client.force_authenticate(user=self.superuser)
                return client.delete(f"/api/v1/admin/universities/{univ.pk}/").status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(worker_delete)
            f2 = pool.submit(worker_delete)
            statuses = sorted([f1.result(), f2.result()])

        self.assertEqual(statuses, [status.HTTP_204_NO_CONTENT, status.HTTP_404_NOT_FOUND])
        self.assertEqual(
            UniversityAuditLog.objects.filter(
                action=UniversityAuditLog.Action.DELETE,
                object_type=UniversityAuditLog.ObjectType.UNIVERSITY,
                object_id=str(univ.pk),
            ).count(),
            1,
        )

        # 2. Parallel media reference creation vs cleanup worker on the same storage key
        draft_univ = University.objects.create(
            status=University.Status.DRAFT,
            created_by=self.superuser,
        )
        draft_rev = UniversityRevision.objects.create(
            university=draft_univ,
            revision_number=1,
            city="Beijing",
            country="China",
            status=UniversityRevision.Status.DRAFT,
            created_by=self.superuser,
        )
        race_name = default_storage.save("universities/media/pg_race.jpg", create_dummy_image())
        cleanup_task = MediaCleanupTask.objects.create(
            file_path=race_name,
            status=MediaCleanupTask.Status.PENDING,
        )

        def worker_create_media():
            connections.close_all()
            try:
                UniversityMediaService.create_media(
                    actor=self.superuser,
                    revision_id=draft_rev.pk,
                    file=race_name,
                    media_type=UniversityMedia.MediaType.LOGO,
                )
                return "created"
            except Exception:
                return "rejected"
            finally:
                connections.close_all()

        def worker_cleanup():
            connections.close_all()
            try:
                MediaLifecycleService.execute_cleanup_tasks([cleanup_task.pk])
                return "cleanup_done"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            fc = pool.submit(worker_create_media)
            fd = pool.submit(worker_cleanup)
            media_outcome = fc.result()
            fd.result()

        # Critical invariant: DB never holds a reference to a deleted storage key
        if media_outcome == "created":
            self.assertTrue(
                UniversityMedia.objects.filter(university_revision=draft_rev, file=race_name).exists()
            )
            self.assertTrue(default_storage.exists(race_name))
        else:
            self.assertFalse(
                UniversityMedia.objects.filter(university_revision=draft_rev, file=race_name).exists()
            )

        # 3. Parallel revision create + archived revision delete on the same university
        arch_rev = UniversityRevision.objects.create(
            university=draft_univ,
            revision_number=2,
            city="Nanjing",
            country="China",
            status=UniversityRevision.Status.ARCHIVED,
            created_by=self.superuser,
        )

        def worker_create_rev():
            connections.close_all()
            try:
                return UniversityRevisionService.create_revision(
                    actor=self.superuser,
                    university_id=draft_univ.pk,
                    city="Shanghai",
                    country="China",
                ).revision_number
            finally:
                connections.close_all()

        def worker_delete_arch_rev():
            connections.close_all()
            try:
                UniversityRevisionService.delete_revision(
                    actor=self.superuser,
                    revision_id=arch_rev.pk,
                )
                return "deleted"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            fr1 = pool.submit(worker_create_rev)
            fr2 = pool.submit(worker_delete_arch_rev)
            new_rev_num = fr1.result()
            del_result = fr2.result()

        self.assertEqual(del_result, "deleted")
        self.assertEqual(new_rev_num, 3)
        self.assertFalse(UniversityRevision.objects.filter(pk=arch_rev.pk).exists())

        # 4. Audit log transaction atomicity on PostgreSQL (rollback vs commit)
        from apps.admissions.models import Admission

        prot_univ = University.objects.create(
            status=University.Status.ARCHIVED,
            created_by=self.superuser,
        )
        Admission.objects.create(
            full_name="Atomicity Test",
            phone_number="+998901112233",
            university=prot_univ,
        )
        client = APIClient()
        client.force_authenticate(user=self.superuser)
        res_prot = client.delete(f"/api/v1/admin/universities/{prot_univ.pk}/")
        self.assertEqual(res_prot.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertTrue(University.objects.filter(pk=prot_univ.pk).exists())
        self.assertEqual(
            UniversityAuditLog.objects.filter(
                object_type=UniversityAuditLog.ObjectType.UNIVERSITY,
                object_id=str(prot_univ.pk),
            ).count(),
            0,
        )

        # 5. Parallel Celery cleanup retry execution on PostgreSQL
        from apps.universities.tasks import retry_failed_university_media_cleanups

        retry_file = default_storage.save("universities/media/pg_parallel_retry.jpg", create_dummy_image())
        retry_task = MediaCleanupTask.objects.create(
            file_path=retry_file,
            status=MediaCleanupTask.Status.FAILED,
            attempts=1,
            last_error="OSError",
        )

        def worker_retry():
            connections.close_all()
            try:
                return retry_failed_university_media_cleanups()
            finally:
                connections.close_all()

        with patch.object(default_storage, "delete", wraps=default_storage.delete) as delete_spy:
            with ThreadPoolExecutor(max_workers=2) as pool:
                r1 = pool.submit(worker_retry)
                r2 = pool.submit(worker_retry)
                r1.result()
                r2.result()
            self.assertEqual(delete_spy.call_count, 1)

        retry_task.refresh_from_db()
        self.assertEqual(retry_task.status, MediaCleanupTask.Status.COMPLETED)
        self.assertEqual(retry_task.attempts, 2)
        self.assertFalse(default_storage.exists(retry_file))

    def test_faq_permissions_strict_isolation_from_university_permissions(self):
        univ_editor = self._create_user_with_perms("faq_iso_univ_editor", "change_university")
        faq_creator = self._create_user_with_perms("faq_iso_creator", "add_faq")
        faq_editor = self._create_user_with_perms("faq_iso_editor", "change_faq")
        faq_submitter = self._create_user_with_perms("faq_iso_submitter", "submit_review_faq")
        faq_approver = self._create_user_with_perms("faq_iso_approver", "approve_faq")
        faq_rejector = self._create_user_with_perms("faq_iso_rejector", "reject_faq")
        faq_publisher = self._create_user_with_perms("faq_iso_publisher", "publish_faq")

        univ = University.objects.create(
            status=University.Status.DRAFT,
            created_by=self.superuser,
        )
        faq = FAQ.objects.create(order=1, is_active=True)
        faq_trans = FAQTranslation.objects.create(faq=faq, language_code="uz")
        faq_rev = FAQTranslationRevision.objects.create(
            translation=faq_trans,
            revision_number=1,
            question="Boshlang'ich savol?",
            answer="Boshlang'ich javob.",
            status=FAQTranslationRevision.Status.DRAFT,
            created_by=self.superuser,
        )

        # 1. change_university ONLY -> 403 across ALL FAQ endpoints
        self.client.force_authenticate(user=univ_editor)
        self.assertEqual(self.client.get("/api/v1/admin/faqs/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            self.client.post("/api/v1/admin/faqs/", {"order": 2}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.get(f"/api/v1/admin/faqs/{faq.pk}/").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.patch(f"/api/v1/admin/faqs/{faq.pk}/", {"order": 5}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(f"/api/v1/admin/faqs/{faq.pk}/").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.get(f"/api/v1/admin/faqs/{faq.pk}/translations/").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.post(
                f"/api/v1/admin/faqs/{faq.pk}/translations/",
                {"language_code": "en", "question": "Q?", "answer": "A."},
                format="json",
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.get(f"/api/v1/admin/faq-translations/{faq_trans.pk}/").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(f"/api/v1/admin/faq-translations/{faq_trans.pk}/").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.get(f"/api/v1/admin/faq-translations/{faq_trans.pk}/revisions/").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.post(
                f"/api/v1/admin/faq-translations/{faq_trans.pk}/revisions/",
                {"question": "Q2?", "answer": "A2."},
                format="json",
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.get(f"/api/v1/admin/faq-revisions/{faq_rev.pk}/").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/v1/admin/faq-revisions/{faq_rev.pk}/",
                {"question": "Updated?"},
                format="json",
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(f"/api/v1/admin/faq-revisions/{faq_rev.pk}/").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        for action in ("submit", "approve", "reject", "publish", "archive"):
            payload = {"reason": "Reject"} if action == "reject" else {}
            self.assertEqual(
                self.client.post(
                    f"/api/v1/admin/faq-revisions/{faq_rev.pk}/{action}/",
                    payload,
                    format="json",
                ).status_code,
                status.HTTP_403_FORBIDDEN,
            )

        # Verify University API itself still works for change_university
        self.assertEqual(
            self.client.post(
                f"/api/v1/admin/universities/{univ.pk}/archive/",
            ).status_code,
            status.HTTP_200_OK,
        )

        # 2. change_faq ONLY -> allowed on FAQ GET/PATCH/revision/archive, blocked on University & FAQ delete/create
        self.client.force_authenticate(user=faq_editor)
        self.assertEqual(self.client.get("/api/v1/admin/faqs/").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(f"/api/v1/admin/faqs/{faq.pk}/").status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.patch(f"/api/v1/admin/faqs/{faq.pk}/", {"order": 3}, format="json").status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.get(f"/api/v1/admin/faqs/{faq.pk}/translations/").status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.get(f"/api/v1/admin/faq-translations/{faq_trans.pk}/").status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.get(f"/api/v1/admin/faq-translations/{faq_trans.pk}/revisions/").status_code,
            status.HTTP_200_OK,
        )
        res_rev_create = self.client.post(
            f"/api/v1/admin/faq-translations/{faq_trans.pk}/revisions/",
            {"question": "Yangi savol?", "answer": "Yangi javob."},
            format="json",
        )
        self.assertEqual(res_rev_create.status_code, status.HTTP_201_CREATED)
        rev2_id = res_rev_create.data["id"]

        self.assertEqual(
            self.client.get(f"/api/v1/admin/faq-revisions/{rev2_id}/").status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/v1/admin/faq-revisions/{rev2_id}/",
                {"question": "Tahrirlangan savol?"},
                format="json",
            ).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.post(f"/api/v1/admin/faq-revisions/{faq_rev.pk}/archive/").status_code,
            status.HTTP_200_OK,
        )
        # change_faq alone must NOT allow University endpoints or FAQ create/delete
        self.assertEqual(
            self.client.post(f"/api/v1/admin/universities/{univ.pk}/archive/").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.post("/api/v1/admin/faqs/", {"order": 9}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(f"/api/v1/admin/faqs/{faq.pk}/").status_code,
            status.HTTP_403_FORBIDDEN,
        )

        # 3. add_faq ONLY -> allowed on POST /faqs/ & POST /faqs/{id}/translations/ without change_university
        self.client.force_authenticate(user=faq_creator)
        res_faq_create = self.client.post("/api/v1/admin/faqs/", {"order": 4}, format="json")
        self.assertEqual(res_faq_create.status_code, status.HTTP_201_CREATED)
        created_faq_id = res_faq_create.data["id"]
        res_tr_create = self.client.post(
            f"/api/v1/admin/faqs/{created_faq_id}/translations/",
            {"language_code": "en", "question": "English Q?", "answer": "English A."},
            format="json",
        )
        self.assertEqual(res_tr_create.status_code, status.HTTP_201_CREATED)

        # 4. Granular FAQ workflow permissions work WITHOUT change_university
        self.client.force_authenticate(user=faq_submitter)
        self.assertEqual(
            self.client.post(f"/api/v1/admin/faq-revisions/{rev2_id}/submit/").status_code,
            status.HTTP_200_OK,
        )
        self.client.force_authenticate(user=faq_rejector)
        self.assertEqual(
            self.client.post(
                f"/api/v1/admin/faq-revisions/{rev2_id}/reject/",
                {"reason": "Aniqlashtiring"},
                format="json",
            ).status_code,
            status.HTTP_200_OK,
        )
        self.client.force_authenticate(user=faq_submitter)
        self.assertEqual(
            self.client.post(f"/api/v1/admin/faq-revisions/{rev2_id}/submit/").status_code,
            status.HTTP_200_OK,
        )
        self.client.force_authenticate(user=faq_approver)
        self.assertEqual(
            self.client.post(f"/api/v1/admin/faq-revisions/{rev2_id}/approve/").status_code,
            status.HTTP_200_OK,
        )
        self.client.force_authenticate(user=faq_publisher)
        self.assertEqual(
            self.client.post(f"/api/v1/admin/faq-revisions/{rev2_id}/publish/").status_code,
            status.HTTP_200_OK,
        )

    def test_celery_beat_schedule_and_duplicate_retry_execution(self):
        from io import StringIO
        from celery.schedules import crontab
        from django.conf import settings
        from django.core.management import call_command
        from core.celery import app as celery_app
        from apps.universities.tasks import retry_failed_university_media_cleanups

        # 1. Beat schedule and registered task verification
        beat_schedule = getattr(settings, "CELERY_BEAT_SCHEDULE", {})
        self.assertIn("retry-failed-university-media-cleanups", beat_schedule)
        entry = beat_schedule["retry-failed-university-media-cleanups"]
        self.assertEqual(
            entry["task"],
            "apps.universities.tasks.retry_failed_university_media_cleanups",
        )
        self.assertIsInstance(entry["schedule"], crontab)
        self.assertIn(
            "apps.universities.tasks.retry_failed_university_media_cleanups",
            celery_app.tasks,
        )

        # 2. Repeated / duplicate retry invocation never deletes storage twice
        ok_file = default_storage.save("universities/media/beat_ok.jpg", create_dummy_image())
        task_ok = MediaCleanupTask.objects.create(
            file_path=ok_file,
            status=MediaCleanupTask.Status.FAILED,
            attempts=1,
            last_error="OSError",
        )
        with patch.object(default_storage, "delete", wraps=default_storage.delete) as delete_spy:
            first_count = retry_failed_university_media_cleanups()
            second_count = retry_failed_university_media_cleanups()
            self.assertEqual(first_count, 1)
            self.assertEqual(second_count, 0)
            self.assertEqual(delete_spy.call_count, 1)

        task_ok.refresh_from_db()
        self.assertEqual(task_ok.status, MediaCleanupTask.Status.COMPLETED)
        self.assertEqual(task_ok.attempts, 2)
        self.assertFalse(default_storage.exists(ok_file))

        # 3. Persistent storage failure logs warning and is visible via stats & management command
        bad_file = default_storage.save("universities/media/beat_fail.jpg", create_dummy_image())
        task_fail = MediaCleanupTask.objects.create(
            file_path=bad_file,
            status=MediaCleanupTask.Status.FAILED,
            attempts=1,
            last_error="OSError",
        )
        with (
            patch.object(default_storage, "delete", side_effect=OSError("Disk offline")),
            self.assertLogs("apps.universities.services.media_lifecycle_service", level="WARNING") as logs,
        ):
            retry_failed_university_media_cleanups()

        self.assertTrue(
            any("remaining_failed_total=1" in msg for msg in logs.output)
        )
        out = StringIO()
        call_command("retry_failed_media_cleanups", "--stats-only", stdout=out)
        self.assertIn("failed=1", out.getvalue())

        # Clean recovery via management command
        out_run = StringIO()
        call_command("retry_failed_media_cleanups", stdout=out_run)
        self.assertIn("Processed cleanup tasks: 1", out_run.getvalue())
        self.assertIn("failed=0", out_run.getvalue())
        task_fail.refresh_from_db()
        self.assertEqual(task_fail.status, MediaCleanupTask.Status.COMPLETED)
