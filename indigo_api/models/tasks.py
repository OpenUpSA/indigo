# coding=utf-8
import datetime
from itertools import groupby

from actstream import action
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models import signals, Prefetch
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.utils import timezone
from allauth.account.utils import user_display
from django_fsm import FSMField, has_transition_perm, transition
from django_fsm.signals import post_transition

from indigo.custom_tasks import tasks
from indigo.documents import ResolvedAnchor
from indigo_api.signals import task_closed


class TaskQuerySet(models.QuerySet):
    def unclosed(self):
        return self.filter(state__in=Task.OPEN_STATES)

    def closed(self):
        return self.filter(state__in=Task.CLOSED_STATES)


class TaskManager(models.Manager):
    use_for_related_fields = True

    def get_queryset(self):
        from .works import Work
        from .documents import Document

        return super(TaskManager, self).get_queryset() \
            .select_related('created_by_user', 'assigned_to') \
            .prefetch_related(Prefetch('work', queryset=Work.objects.filter())) \
            .prefetch_related(Prefetch('document', queryset=Document.objects.no_xml())) \
            .prefetch_related('labels')


class Task(models.Model):
    OPEN = 'open'
    PENDING_REVIEW = 'pending_review'
    CANCELLED = 'cancelled'
    DONE = 'done'

    STATES = (OPEN, PENDING_REVIEW, CANCELLED, DONE)

    CLOSED_STATES = (CANCELLED, DONE)
    OPEN_STATES = (OPEN, PENDING_REVIEW)

    VERBS = {
        'submit': 'submitted',
        'cancel': 'cancelled',
        'reopen': 'reopened',
        'unsubmit': 'requested changes to',
        'close': 'approved',
    }

    class Meta:
        permissions = (
            ('submit_task', 'Can submit an open task for review'),
            ('cancel_task', 'Can cancel a task that is open or has been submitted for review'),
            ('reopen_task', 'Can reopen a task that is closed or cancelled'),
            ('unsubmit_task', 'Can unsubmit a task that has been submitted for review'),
            ('close_task', 'Can close a task that has been submitted for review'),
        )

    objects = TaskManager.from_queryset(TaskQuerySet)()

    title = models.CharField(max_length=256, null=False, blank=False)
    description = models.TextField(null=True, blank=True)

    country = models.ForeignKey('indigo_api.Country', related_name='tasks', null=False, blank=False, on_delete=models.CASCADE)
    locality = models.ForeignKey('indigo_api.Locality', related_name='tasks', null=True, blank=True, on_delete=models.CASCADE)
    work = models.ForeignKey('indigo_api.Work', related_name='tasks', null=True, blank=True, on_delete=models.CASCADE)
    document = models.ForeignKey('indigo_api.Document', related_name='tasks', null=True, blank=True, on_delete=models.CASCADE)

    # cf indigo_api.models.Annotation
    anchor_id = models.CharField(max_length=128, null=True, blank=True)

    state = FSMField(default=OPEN)

    # internal task code
    code = models.CharField(max_length=100, null=True, blank=True)

    assigned_to = models.ForeignKey(User, related_name='assigned_tasks', null=True, blank=True, on_delete=models.SET_NULL)
    submitted_by_user = models.ForeignKey(User, related_name='submitted_tasks', null=True, blank=True, on_delete=models.SET_NULL)
    reviewed_by_user = models.ForeignKey(User, related_name='reviewed_tasks', null=True, on_delete=models.SET_NULL)
    closed_at = models.DateTimeField(help_text="When the task was marked as done or cancelled.", null=True)

    changes_requested = models.BooleanField(default=False, help_text="Have changes been requested on this task?")

    created_by_user = models.ForeignKey(User, related_name='+', null=True, on_delete=models.SET_NULL)
    updated_by_user = models.ForeignKey(User, related_name='+', null=True, on_delete=models.SET_NULL)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    labels = models.ManyToManyField('TaskLabel', related_name='+')

    extra_data = JSONField(null=True, blank=True)

    @property
    def place(self):
        return self.locality or self.country

    @property
    def is_closed(self):
        return self.state in self.CLOSED_STATES

    @property
    def is_open(self):
        return self.state in self.OPEN_STATES

    def clean(self):
        # enforce that any work and/or document are for the correct place
        if self.document and self.document.work != self.work:
            self.document = None

        if self.work and (self.work.country != self.country or self.work.locality != self.locality):
            self.work = None

    def can_assign_to(self, user):
        """ Can this task be assigned to this user?
        """
        return user.editor.permitted_countries.filter(pk=self.country.pk).exists()

    def assign_to(self, assignee, assigned_by):
        """ Assign this task to assignee (may be None)
        """
        self.assigned_to = assignee
        self.save()
        if assigned_by == self.assigned_to:
            action.send(self.assigned_to, verb='picked up', action_object=self,
                        place_code=self.place.place_code)
        elif assignee:
            action.send(assigned_by, verb='assigned', action_object=self,
                        target=self.assigned_to,
                        place_code=self.place.place_code)
        else:
            action.send(assigned_by, verb='unassigned', action_object=self,
                        place_code=self.place.place_code)

    @classmethod
    def decorate_potential_assignees(cls, tasks, country):
        permitted_users = User.objects \
            .filter(editor__permitted_countries=country) \
            .order_by('first_name', 'last_name') \
            .all()
        potential_assignees = [u for u in permitted_users if u.has_perm('indigo_api.submit_task')]
        potential_reviewers = [u for u in permitted_users if u.has_perm('indigo_api.close_task')]

        for task in tasks:
            if task.state == 'open':
                task.potential_assignees = [u for u in potential_assignees if task.assigned_to_id != u.id]
            elif task.state == 'pending_review':
                task.potential_assignees = [u for u in potential_reviewers if task.assigned_to_id != u.id and task.submitted_by_user_id != u.id]

        return tasks

    @classmethod
    def decorate_permissions(cls, tasks, view):
        for task in tasks:
            task.change_task_permission = view.request.user.has_perm('indigo_api.change_task')
            task.submit_task_permission = has_transition_perm(task.submit, view)
            task.reopen_task_permission = has_transition_perm(task.reopen, view)
            task.unsubmit_task_permission = has_transition_perm(task.unsubmit, view)
            task.close_task_permission = has_transition_perm(task.close, view)

        return tasks

    @classmethod
    def decorate_submission_message(cls, tasks, view):
        for task in tasks:
            submission_message = 'Are you sure you want to submit this task for review?'
            if task.assigned_to and not task.assigned_to == view.request.user:
                submission_message = 'Are you sure you want to submit this task for review on behalf of {}?' \
                    .format(user_display(task.assigned_to))
            task.submission_message = submission_message

        return tasks

    # submit for review
    def may_submit(self, view):
        user = view.request.user

        if user.has_perm('indigo_api.close_task'):
            senior_or_assignee = True
        else:
            senior_or_assignee = user == self.assigned_to

        return senior_or_assignee and \
               user.is_authenticated and \
               user.editor.has_country_permission(view.country) and \
               user.has_perm('indigo_api.submit_task')

    @transition(field=state, source=['open'], target='pending_review', permission=may_submit)
    def submit(self, user):
        if not self.assigned_to:
            self.assign_to(user, user)
        self.submitted_by_user = self.assigned_to
        self.assigned_to = self.reviewed_by_user

    # cancel
    def may_cancel(self, view):
        return view.request.user.is_authenticated and \
               view.request.user.editor.has_country_permission(view.country) and view.request.user.has_perm('indigo_api.cancel_task')

    @transition(field=state, source=['open', 'pending_review'], target='cancelled', permission=may_cancel)
    def cancel(self, user):
        self.changes_requested = False
        self.assigned_to = None
        self.closed_at = timezone.now()

    # reopen – moves back to 'open'
    def may_reopen(self, view):
        return view.request.user.is_authenticated and \
               view.request.user.editor.has_country_permission(view.country) and view.request.user.has_perm('indigo_api.reopen_task')

    @transition(field=state, source=['cancelled', 'done'], target='open', permission=may_reopen)
    def reopen(self, user):
        self.reviewed_by_user = None
        self.closed_at = None

    # unsubmit – moves back to 'open'
    def may_unsubmit(self, view):
        return view.request.user.is_authenticated and \
               view.request.user.editor.has_country_permission(view.country) and \
               view.request.user.has_perm('indigo_api.unsubmit_task') and \
               (view.request.user == self.assigned_to or not self.assigned_to)

    @transition(field=state, source=['pending_review'], target='open', permission=may_unsubmit)
    def unsubmit(self, user):
        if not self.assigned_to or self.assigned_to != user:
            self.assign_to(user, user)
        self.reviewed_by_user = self.assigned_to
        self.assigned_to = self.submitted_by_user
        self.changes_requested = True

    # close
    def may_close(self, view):
        return view.request.user.is_authenticated and \
               view.request.user.editor.has_country_permission(view.country) and \
               view.request.user.has_perm('indigo_api.close_task') and \
               (view.request.user == self.assigned_to or not self.assigned_to)

    @transition(field=state, source=['pending_review'], target='done', permission=may_close)
    def close(self, user):
        if not self.assigned_to or self.assigned_to != user:
            self.assign_to(user, user)
        self.reviewed_by_user = self.assigned_to
        self.closed_at = timezone.now()
        self.changes_requested = False
        self.assigned_to = None

        # send task_closed signal
        task_closed.send(sender=self.__class__, task=self)

    def anchor(self):
        return {'id': self.anchor_id}

    def resolve_anchor(self):
        if not self.anchor_id or not self.document:
            return None

        return ResolvedAnchor(anchor=self.anchor(), document=self.document)

    @property
    def customised(self):
        """ If this task is customised, return a new object describing the customisation.
        """
        if self.code:
            if not hasattr(self, '_customised'):
                plugin = tasks.for_locale(self.code, country=self.country, locality=self.locality)
                self._customised = plugin
                if plugin:
                    self._customised.setup(self)
            return self._customised

    @classmethod
    def task_columns(cls, required_groups, tasks):
        def grouper(task):
            if task.state == 'open' and task.assigned_to:
                return 'assigned'
            else:
                return task.state

        tasks = sorted(tasks, key=grouper)
        tasks = {state: list(group) for state, group in groupby(tasks, key=grouper)}

        # base columns on the requested task states
        groups = {}
        for key in required_groups:
            groups[key] = {
                'title': key.replace('_', ' ').capitalize(),
                'badge': key,
            }

        for key, group in tasks.items():
            if key not in groups:
                groups[key] = {
                    'title': key.replace('_', ' ').capitalize(),
                    'badge': key,
                }
            groups[key]['tasks'] = group

        # enforce column ordering
        return [groups.get(g) for g in ['open', 'assigned', 'pending_review', 'done', 'cancelled'] if g in groups]

    def get_extra_data(self):
        if self.extra_data is None:
            self.extra_data = {}
        return self.extra_data

    @property
    def friendly_state(self):
        return self.state.replace('_', ' ')


@receiver(signals.post_save, sender=Task)
def post_save_task(sender, instance, **kwargs):
    """ Send 'created' action to activity stream if new task
    """
    if kwargs['created']:
        action.send(instance.created_by_user, verb='created', action_object=instance,
                    place_code=instance.place.place_code)


@receiver(post_transition, sender=Task)
def post_task_transition(sender, instance, name, **kwargs):
    """ When tasks transition, store actions.

    Doing this in a signal, rather than in the transition method on the class,
    means that the task's state field is up to date. Our notification system
    is triggered on action signals, and the action objects passed to action
    signals are loaded fresh from the DB - so any objects they reference
    are also loaded from the db. So we ensure that the task is saved to the
    DB (including the updated state field), just before creating the action
    signal.
    """
    if name in instance.VERBS:
        user = kwargs['method_args'][0]
        # ensure the task object changes are in the DB, since action signals
        # load related data objects from the db
        instance.save()

        if name == 'unsubmit':
            action.send(user, verb=instance.VERBS['unsubmit'],
                        action_object=instance,
                        target=instance.assigned_to,
                        place_code=instance.place.place_code)
        else:
            action.send(user, verb=instance.VERBS[name], action_object=instance, place_code=instance.place.place_code)


class WorkflowQuerySet(models.QuerySet):
    def unclosed(self):
        return self.filter(closed=False)

    def closed(self):
        return self.filter(closed=True)


class WorkflowManager(models.Manager):
    use_for_related_fields = True

    def get_queryset(self):
        return super(WorkflowManager, self).get_queryset() \
            .select_related('created_by_user')


class Workflow(models.Model):
    class Meta:
        permissions = (
            ('close_workflow', 'Can close a workflow'),
        )
        ordering = ('title',)

    objects = WorkflowManager.from_queryset(WorkflowQuerySet)()

    title = models.CharField(max_length=256, null=False, blank=False)
    description = models.TextField(null=True, blank=True)

    tasks = models.ManyToManyField(Task, related_name='workflows')

    closed = models.BooleanField(default=False)
    due_date = models.DateField(null=True, blank=True)

    country = models.ForeignKey('indigo_api.Country', related_name='workflows', null=False, blank=False, on_delete=models.CASCADE)
    locality = models.ForeignKey('indigo_api.Locality', related_name='workflows', null=True, blank=True, on_delete=models.CASCADE)

    created_by_user = models.ForeignKey(User, related_name='+', null=True, on_delete=models.SET_NULL)
    updated_by_user = models.ForeignKey(User, related_name='+', null=True, on_delete=models.SET_NULL)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def place(self):
        return self.locality or self.country

    @property
    def overdue(self):
        return self.due_date and self.due_date < datetime.date.today()

    def __str__(self):
        return self.title


@receiver(signals.post_save, sender=Workflow)
def post_save_workflow(sender, instance, **kwargs):
    """ Send 'created' action to activity stream if new workflow
    """
    if kwargs['created']:
        action.send(instance.created_by_user, verb='created', action_object=instance,
                    place_code=instance.place.place_code)


class TaskLabel(models.Model):
    title = models.CharField(max_length=30, null=False, unique=True, blank=False)
    slug = models.SlugField(null=False, unique=True, blank=False)
    description = models.CharField(max_length=256, null=True, blank=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.slug
