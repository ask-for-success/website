from django.core.exceptions import (
    ObjectDoesNotExist,
    ValidationError as DjangoValidationError,
)
from django.db import transaction
from django.urls import reverse
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.models import User
from apps.organization.models import Department, Position

from .models import (
    ApplicationCv,
    ApplicationStatus,
    OfferResponse,
    RecruitmentAnswer,
    RecruitmentApplication,
    RecruitmentForm,
    RecruitmentFormStatus,
    RecruitmentOpportunity,
    RecruitmentQuestion,
    RecruitmentQuestionOption,
    RecruitmentQuestionType,
)
from .operations import (
    change_application_status,
    create_recruitment_application,
    respond_to_application_offer,
    validate_cv_file,
)


def convert_validation_error(error: DjangoValidationError):
    if hasattr(error, "message_dict"):
        return error.message_dict
    return {"non_field_errors": list(error.messages)}


class RecruitmentQuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecruitmentQuestionOption
        fields = ("id", "label", "display_order")
        read_only_fields = ("id",)


class RecruitmentQuestionSerializer(serializers.ModelSerializer):
    options = RecruitmentQuestionOptionSerializer(many=True, required=False)

    class Meta:
        model = RecruitmentQuestion
        fields = (
            "id",
            "label",
            "help_text",
            "question_type",
            "is_required",
            "display_order",
            "options",
        )
        read_only_fields = ("id",)

    def validate(self, data):
        options = data.get("options", [])
        question_type = data.get("question_type")
        supports_options = question_type in {
            RecruitmentQuestionType.SINGLE_CHOICE,
            RecruitmentQuestionType.MULTIPLE_CHOICE,
        }
        if supports_options and len(options) < 2:
            raise serializers.ValidationError(
                {"options": "A choice question requires at least two options."}
            )
        if not supports_options and options:
            raise serializers.ValidationError(
                {"options": "This question type does not accept options."}
            )
        display_orders = [option["display_order"] for option in options]
        if len(display_orders) != len(set(display_orders)):
            raise serializers.ValidationError(
                {"options": "Option display orders must be unique."}
            )
        return data


class RecruitmentFormSerializer(serializers.ModelSerializer):
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.filter(is_active=True),
        source="department",
    )
    position_id = serializers.PrimaryKeyRelatedField(
        queryset=Position.objects.filter(is_active=True),
        source="position",
    )
    department_name = serializers.CharField(
        source="department.name",
        read_only=True,
    )
    position_name = serializers.CharField(
        source="position.name",
        read_only=True,
    )
    questions = RecruitmentQuestionSerializer(many=True, required=False)
    is_locked = serializers.SerializerMethodField()

    class Meta:
        model = RecruitmentForm
        fields = (
            "id",
            "name",
            "description",
            "status",
            "department_id",
            "department_name",
            "position_id",
            "position_name",
            "questions",
            "is_locked",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "is_locked", "created_at", "updated_at")

    @extend_schema_field(serializers.BooleanField())
    def get_is_locked(self, instance):
        return instance.opportunities.filter(applications__isnull=False).exists()

    def validate_questions(self, questions):
        display_orders = [question["display_order"] for question in questions]
        if len(display_orders) != len(set(display_orders)):
            raise serializers.ValidationError(
                "Question display orders must be unique."
            )
        return questions

    def validate(self, data):
        instance = self.instance
        department = data.get(
            "department",
            instance.department if instance else None,
        )
        position = data.get(
            "position",
            instance.position if instance else None,
        )
        if department and position and position.department_id != department.id:
            raise serializers.ValidationError(
                {"position_id": "The position must belong to the department."}
            )
        form_status = data.get(
            "status",
            instance.status if instance else RecruitmentFormStatus.DRAFT,
        )
        submitted_questions = data.get("questions")
        has_questions = (
            bool(submitted_questions)
            if submitted_questions is not None
            else bool(instance and instance.questions.exists())
        )
        if form_status == RecruitmentFormStatus.ACTIVE and not has_questions:
            raise serializers.ValidationError(
                {"questions": "An active form requires at least one question."}
            )
        if instance and self.get_is_locked(instance):
            errors = {}
            if "questions" in data:
                errors["questions"] = (
                    "Questions cannot change after the first application."
                )
            if "department" in data and data["department"] != instance.department:
                errors["department_id"] = (
                    "The department cannot change after the first application."
                )
            if "position" in data and data["position"] != instance.position:
                errors["position_id"] = (
                    "The position cannot change after the first application."
                )
            if errors:
                raise serializers.ValidationError(errors)
        return data

    @staticmethod
    def _create_questions(form, questions):
        for question_data in questions:
            options = question_data.pop("options", [])
            question = RecruitmentQuestion.objects.create(
                form=form,
                **question_data,
            )
            for option_data in options:
                RecruitmentQuestionOption.objects.create(
                    question=question,
                    **option_data,
                )

    @transaction.atomic
    def create(self, validated_data):
        questions = validated_data.pop("questions", [])
        form = RecruitmentForm(
            created_by=self.context["request"].user,
            **validated_data,
        )
        try:
            form.full_clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error
        form.save()
        self._create_questions(form, questions)
        return form

    @transaction.atomic
    def update(self, instance, validated_data):
        questions = validated_data.pop("questions", None)
        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)
        try:
            instance.full_clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error
        instance.save()
        if questions is not None:
            instance.questions.all().delete()
            self._create_questions(instance, questions)
        return instance


class RecruitmentFormReferenceSerializer(serializers.ModelSerializer):
    department_id = serializers.UUIDField(source="department.id")
    department_name = serializers.CharField(source="department.name")
    position_id = serializers.UUIDField(source="position.id")
    position_name = serializers.CharField(source="position.name")
    questions = RecruitmentQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = RecruitmentForm
        fields = (
            "id",
            "name",
            "department_id",
            "department_name",
            "position_id",
            "position_name",
            "questions",
        )


class RecruitmentOpportunitySerializer(serializers.ModelSerializer):
    form_id = serializers.PrimaryKeyRelatedField(
        queryset=RecruitmentForm.objects.all(),
        source="form",
    )
    application_form = RecruitmentFormReferenceSerializer(
        source="form",
        read_only=True,
    )
    accepts_applications = serializers.SerializerMethodField()

    class Meta:
        model = RecruitmentOpportunity
        fields = (
            "id",
            "form_id",
            "application_form",
            "title",
            "slug",
            "summary",
            "description_markdown",
            "status",
            "opens_at",
            "closes_at",
            "accepts_applications",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "accepts_applications",
            "created_at",
            "updated_at",
        )

    @extend_schema_field(serializers.BooleanField())
    def get_accepts_applications(self, instance):
        return instance.accepts_applications()

    def validate_slug(self, value):
        return value.strip().lower()

    def validate(self, data):
        instance = self.instance
        form = data.get("form", instance.form if instance else None)
        opportunity_status = data.get(
            "status",
            instance.status if instance else None,
        )
        if (
            opportunity_status == "published"
            and form
            and form.status != RecruitmentFormStatus.ACTIVE
        ):
            raise serializers.ValidationError(
                {"form_id": "A published opportunity requires an active form."}
            )
        if (
            instance
            and instance.applications.exists()
            and "form" in data
            and data["form"] != instance.form
        ):
            raise serializers.ValidationError(
                {"form_id": "The form cannot change after an application exists."}
            )
        temporary = RecruitmentOpportunity(
            title=data.get("title", instance.title if instance else ""),
            slug=data.get("slug", instance.slug if instance else ""),
            summary=data.get("summary", instance.summary if instance else ""),
            description_markdown=data.get(
                "description_markdown",
                instance.description_markdown if instance else "",
            ),
            form=form,
            opens_at=data.get(
                "opens_at",
                instance.opens_at if instance else None,
            ),
            closes_at=data.get(
                "closes_at",
                instance.closes_at if instance else None,
            ),
        )
        try:
            temporary.clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error
        return data

    def create(self, validated_data):
        opportunity = RecruitmentOpportunity(
            created_by=self.context["request"].user,
            **validated_data,
        )
        try:
            opportunity.full_clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error
        opportunity.save()
        return opportunity

    def update(self, instance, validated_data):
        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)
        try:
            instance.full_clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error
        instance.save()
        return instance


class RecruitmentApplicationCreateSerializer(serializers.Serializer):
    answers = serializers.JSONField(
        help_text=(
            "JSON list containing question_id and value objects. In a multipart "
            "request, send this field as a JSON string."
        )
    )
    cv = serializers.FileField(
        help_text="One PDF CV no larger than 10 MB."
    )

    def validate_cv(self, value):
        try:
            validate_cv_file(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages) from error
        return value

    def create(self, validated_data):
        try:
            return create_recruitment_application(
                opportunity=self.context["opportunity"],
                applicant=self.context["request"].user,
                cv_file=validated_data["cv"],
                answers=validated_data["answers"],
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error


class ApplicantReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
        )


class OpportunityReferenceSerializer(serializers.ModelSerializer):
    department_id = serializers.UUIDField(source="form.department.id")
    department_name = serializers.CharField(source="form.department.name")
    position_id = serializers.UUIDField(source="form.position.id")
    position_name = serializers.CharField(source="form.position.name")

    class Meta:
        model = RecruitmentOpportunity
        fields = (
            "id",
            "title",
            "slug",
            "department_id",
            "department_name",
            "position_id",
            "position_name",
        )


class RecruitmentAnswerOutputSerializer(serializers.ModelSerializer):
    question_id = serializers.UUIDField(source="question.id")
    question = serializers.CharField(source="question.label")
    question_type = serializers.CharField(source="question.question_type")

    class Meta:
        model = RecruitmentAnswer
        fields = ("question_id", "question", "question_type", "value")


class ApplicationCvSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationCv
        fields = (
            "original_filename",
            "content_type",
            "size",
            "sha256",
            "uploaded_at",
            "download_url",
        )

    @extend_schema_field(serializers.URLField())
    def get_download_url(self, instance):
        path = reverse(
            "recruitment:application_cv",
            kwargs={"application_id": instance.application_id},
        )
        request = self.context.get("request")
        return request.build_absolute_uri(path) if request else path


class DecisionActorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name")


def application_requires_department_transfer(instance) -> bool:
    if instance.status != ApplicationStatus.ACCEPTED:
        return False
    try:
        membership = instance.applicant.membership
    except ObjectDoesNotExist:
        return False
    assignment = next(
        (
            item
            for item in membership.assignments.all()
            if item.ends_at is None
        ),
        None,
    )
    if assignment is None:
        return False
    form = instance.opportunity.form
    return bool(
        assignment.department_id != form.department_id
        or assignment.position_id != form.position_id
    )


class RecruitmentApplicationListSerializer(serializers.ModelSerializer):
    applicant = ApplicantReferenceSerializer(read_only=True)
    opportunity = OpportunityReferenceSerializer(read_only=True)
    requires_department_transfer = serializers.SerializerMethodField()

    class Meta:
        model = RecruitmentApplication
        fields = (
            "id",
            "applicant",
            "opportunity",
            "status",
            "offered_at",
            "offer_responded_at",
            "offer_email_status",
            "submitted_at",
            "decided_at",
            "decision_email_status",
            "requires_department_transfer",
            "updated_at",
        )

    @extend_schema_field(serializers.BooleanField())
    def get_requires_department_transfer(self, instance) -> bool:
        return application_requires_department_transfer(instance)


class RecruitmentApplicationDetailSerializer(
    RecruitmentApplicationListSerializer
):
    answers = RecruitmentAnswerOutputSerializer(many=True, read_only=True)
    cv = ApplicationCvSerializer(read_only=True)
    decision_by = DecisionActorSerializer(read_only=True)
    offer_by = DecisionActorSerializer(read_only=True)

    class Meta(RecruitmentApplicationListSerializer.Meta):
        fields = RecruitmentApplicationListSerializer.Meta.fields + (
            "answers",
            "cv",
            "offer_by",
            "offer_email_sent_at",
            "offer_email_error",
            "decision_by",
            "decision_email_sent_at",
            "decision_email_error",
        )


class CandidateApplicationSerializer(serializers.ModelSerializer):
    opportunity = OpportunityReferenceSerializer(read_only=True)
    cv = ApplicationCvSerializer(read_only=True)
    can_respond_to_offer = serializers.SerializerMethodField()
    requires_department_transfer = serializers.SerializerMethodField()

    class Meta:
        model = RecruitmentApplication
        fields = (
            "id",
            "opportunity",
            "status",
            "offered_at",
            "offer_responded_at",
            "can_respond_to_offer",
            "requires_department_transfer",
            "submitted_at",
            "decided_at",
            "cv",
            "updated_at",
        )

    @extend_schema_field(serializers.BooleanField())
    def get_can_respond_to_offer(self, instance) -> bool:
        return instance.status == ApplicationStatus.OFFER_PENDING

    @extend_schema_field(serializers.BooleanField())
    def get_requires_department_transfer(self, instance) -> bool:
        return application_requires_department_transfer(instance)


class ApplicationStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=(
            ApplicationStatus.UNDER_REVIEW,
            ApplicationStatus.CONTACTED,
            ApplicationStatus.INTERVIEW,
            ApplicationStatus.OFFER_PENDING,
            ApplicationStatus.REJECTED,
        )
    )

    def create(self, validated_data):
        try:
            return change_application_status(
                application=self.context["application"],
                new_status=validated_data["status"],
                changed_by=self.context["request"].user,
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error


class ApplicationOfferResponseSerializer(serializers.Serializer):
    response = serializers.ChoiceField(choices=OfferResponse.choices)

    def create(self, validated_data):
        try:
            return respond_to_application_offer(
                application=self.context["application"],
                response=validated_data["response"],
                responded_by=self.context["request"].user,
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error
