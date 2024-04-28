from django.contrib import admin
from .models import Company, VacancyType, RequirementTech, Vacancy, Locations
# Register your models here.



admin.site.register(Company)
admin.site.register(VacancyType)
admin.site.register(RequirementTech)
admin.site.register(Vacancy)
admin.site.register(Locations)

