from django.db import models

class Locations(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Company(models.Model):
    name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to='logos/', default=None)
    location = models.ManyToManyField(Locations)

    def __str__(self):
        return self.name

class VacancyType(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class RequirementTech(models.Model):
    name = models.CharField(max_length=255)

class Vacancy(models.Model):
    name = models.CharField(max_length=255)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    status = models.BooleanField(default=True)
    start_date = models.DateTimeField(default=None, blank=True)
    detail = models.CharField(max_length=255)
    vacancy_type = models.ManyToManyField(VacancyType)
    requirement_tech = models.ManyToManyField(RequirementTech)

    def __str__(self):
        return self.name
