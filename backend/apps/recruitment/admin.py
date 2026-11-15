from django.contrib import admin

from .models import (
    ApplicationCv,
    RecruitmentAnswer,
    RecruitmentApplication,
    RecruitmentForm,
    RecruitmentOpportunity,
    RecruitmentQuestion,
    RecruitmentQuestionOption,
)


admin.site.register(RecruitmentForm)
admin.site.register(RecruitmentQuestion)
admin.site.register(RecruitmentQuestionOption)
admin.site.register(RecruitmentOpportunity)
admin.site.register(RecruitmentApplication)
admin.site.register(RecruitmentAnswer)
admin.site.register(ApplicationCv)
