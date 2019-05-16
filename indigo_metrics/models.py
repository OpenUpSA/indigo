import datetime

from django.db import connection, models, transaction

from indigo_api.models import PublicationDocument


class WorkMetrics(models.Model):
    work = models.OneToOneField('indigo_api.work', on_delete=models.CASCADE, null=False, related_name='metrics')

    # Depth completeness - expected vs actual expressions
    n_languages = models.IntegerField(null=True, help_text="Number of languages in published documents")
    n_expressions = models.IntegerField(null=True, help_text="Number of published documents")
    n_points_in_time = models.IntegerField(null=True, help_text="Number of recorded points in time")
    n_expected_expressions = models.IntegerField(null=True, help_text="Expected number of published documents")
    p_depth_complete = models.IntegerField(null=True, help_text="Percentage depth complete")

    # Breadth completeness - basic completeness
    p_breadth_complete = models.IntegerField(null=True, help_text="Percentage breadth complete")

    # total percentage complete, a combination of breadth and depth completeness
    p_complete = models.IntegerField(null=True, help_text="Percentage complete")

    # weight lent to depth completeness when calculating total completeness
    DEPTH_WEIGHT = 0.50

    @classmethod
    def calculate(cls, work):
        metrics = WorkMetrics()
        metrics.n_points_in_time = len(work.points_in_time())
        metrics.n_languages = work.document_set.published().values('language').distinct().count() or 1
        # non-stubs should always have at least one expression
        metrics.n_expected_expressions = 0 if work.stub else max(1, metrics.n_points_in_time * metrics.n_languages)
        metrics.n_expressions = work.document_set.published().count()

        # sum up factors towards breadth completeness
        points = [
            # one for existing, so we don't get zero
            1,
            # at least one published expression?
            1 if (work.stub or metrics.n_expressions > 0) else 0
        ]
        # publication document?
        try:
            if work.publication_document:
                points.append(1)
        except PublicationDocument.DoesNotExist:
            points.append(0)
        metrics.p_breadth_complete = int(100.0 * sum(points) / len(points))

        if work.stub:
            metrics.p_depth_complete = 100
        else:
            # TODO: take into account some measure of completeness for the expressions that do exist
            metrics.p_depth_complete = int(100.0 * metrics.n_expressions / metrics.n_expected_expressions)

        metrics.p_complete = int(metrics.p_depth_complete * cls.DEPTH_WEIGHT +
                                 metrics.p_breadth_complete * (1.0 - cls.DEPTH_WEIGHT))

        return metrics

    @classmethod
    def create_or_update(cls, work):
        metrics = cls.calculate(work)

        try:
            existing = cls.objects.get(work=work)
            if existing:
                metrics.id = existing.id
        except cls.DoesNotExist:
            pass

        work.metrics = metrics
        metrics.save()

        return metrics


class DailyWorkMetrics(models.Model):
    """ Daily summarised work metrics.
    """
    date = models.DateField(null=False, db_index=True)
    place_code = models.CharField(null=False, db_index=True, max_length=20)
    country = models.CharField(null=False, max_length=20)
    locality = models.CharField(null=True, max_length=20)

    n_works = models.IntegerField(null=False)
    n_expressions = models.IntegerField(null=True)
    n_points_in_time = models.IntegerField(null=True)
    n_expected_expressions = models.IntegerField(null=True)
    # number of works for which expressions == expected expressions
    n_complete_works = models.IntegerField(null=True)

    p_depth_complete = models.IntegerField(null=True)
    p_breadth_complete = models.IntegerField(null=True)
    p_complete = models.IntegerField(null=True)

    class Meta:
        db_table = 'indigo_metrics_daily_workmetrics'
        unique_together = (("date", "place_code"),)

    @classmethod
    def create_or_update(cls, date=None):
        date = date or datetime.date.today()

        with transaction.atomic():
            cls.objects.filter(date=date).delete()
            cls.insert(date)

    @classmethod
    def insert(cls, date):
        with connection.cursor() as cursor:
            cursor.execute("""
INSERT INTO
  indigo_metrics_daily_workmetrics(
    date, place_code, country, locality,
    n_works, n_expressions, n_expected_expressions, n_points_in_time, n_complete_works,
    p_depth_complete, p_breadth_complete, p_complete
  )
SELECT
  %s AS date,
  frbr_uri_parts[2] AS place_code,
  SUBSTRING(frbr_uri_parts[2] FROM 1 FOR 2) AS country,
  SUBSTRING(frbr_uri_parts[2] FROM 4) AS locality,
  COUNT(1) AS n_works,
  SUM(n_expressions) AS n_expressions,
  SUM(n_expected_expressions) AS n_expected_expressions,
  SUM(n_points_in_time) AS n_points_in_time,
  SUM(CASE WHEN n_expected_expressions = n_expressions THEN 1 ELSE 0 END) as n_complete_works,
  AVG(p_depth_complete) AS p_depth_complete,
  AVG(p_breadth_complete) AS p_breadth_complete,
  AVG(p_complete) AS p_complete
FROM (
  SELECT
    frbr_uri,
    REGEXP_SPLIT_TO_ARRAY(FRBR_URI, '/') AS frbr_uri_parts,
    n_expressions,
    n_expected_expressions,
    n_points_in_time,
    p_depth_complete,
    p_breadth_complete,
    p_complete
  FROM indigo_metrics_workmetrics wm
  INNER JOIN indigo_api_work w ON w.id = wm.work_id
) AS x
GROUP BY
  date, place_code, country, locality
""", [date])
