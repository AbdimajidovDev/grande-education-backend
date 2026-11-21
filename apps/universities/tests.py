
import tempfile
from io import BytesIO
from PIL import Image

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.universities.models import (
    University,
    UniversityRevision,
    UniversityTranslation,
    UniversityTranslationRevision,
    UniversityMajor,
    UniversityMajorTranslation,
    UniversityMedia,
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
