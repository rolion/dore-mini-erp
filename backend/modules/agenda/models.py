from django.db import models


class Schedule(models.Model):
    company_id = models.UUIDField()
    professional_id = models.UUIDField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('company_id', 'professional_id'), name='agenda_schedule_company_professional'
            ),
        ]


class Shift(models.Model):
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    day = models.PositiveSmallIntegerField()
    starts = models.TimeField()
    ends = models.TimeField()
    valid_from = models.DateField()
    valid_until = models.DateField()
    breaks = models.JSONField(default=list)


class Absence(models.Model):
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    starts = models.DateTimeField()
    ends = models.DateTimeField()
    reason = models.CharField(max_length=250)
