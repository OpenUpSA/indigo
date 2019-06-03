# coding=utf-8
from __future__ import unicode_literals
import json
from itertools import chain
import datetime

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType

from django.core.exceptions import PermissionDenied
from django.http import QueryDict
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import ListView, CreateView, DetailView, UpdateView
from django.views.generic.base import View, TemplateView
from django.views.generic.detail import SingleObjectMixin
from django_comments.models import Comment
from django.views.generic.edit import BaseFormView
from allauth.account.utils import user_display
from actstream import action
from django_fsm import has_transition_perm

from indigo_api.models import Task, TaskLabel, User, Work, Workflow
from indigo_api.serializers import WorkSerializer, DocumentSerializer

from indigo_app.views.base import AbstractAuthedIndigoView, PlaceViewBase
from indigo_app.forms import TaskCreateForm, TaskEditForm, TaskFilterForm, BulkTaskUpdateForm


class TaskViewBase(PlaceViewBase, AbstractAuthedIndigoView):
    tab = 'tasks'

    def record_workflow_actions(self, task, new_workflows):
        old_workflows = task.workflows.all()

        removed_workflows = set(old_workflows) - set(new_workflows)
        added_workflows = set(new_workflows) - set(old_workflows)

        for workflow in removed_workflows:
            action.send(self.request.user, verb='removed', action_object=task,
                        target=workflow, place_code=task.place.place_code)

        for workflow in added_workflows:
            action.send(self.request.user, verb='added', action_object=task,
                        target=workflow, place_code=task.place.place_code)


class TaskListView(TaskViewBase, ListView):
    context_object_name = 'tasks'
    model = Task
    js_view = 'TaskListView TaskBulkUpdateView'

    def get(self, request, *args, **kwargs):
        # allows us to set defaults on the form
        params = QueryDict(mutable=True)
        params.update(request.GET)

        # initial state
        if not params.get('state'):
            params.setlist('state', ['open', 'assigned', 'pending_review'])
        params.setdefault('format', 'columns')

        self.form = TaskFilterForm(self.country, params)
        self.form.is_valid()

        return super(TaskListView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        tasks = Task.objects\
            .filter(country=self.country, locality=self.locality)\
            .select_related('document__language', 'document__language__language') \
            .defer('document__document_xml', 'document__search_text', 'document__search_vector')\
            .order_by('-updated_at')
        return self.form.filter_queryset(tasks)

    def get_context_data(self, **kwargs):
        context = super(TaskListView, self).get_context_data(**kwargs)
        context['task_labels'] = TaskLabel.objects.all()
        context['form'] = self.form
        context['frbr_uri'] = self.request.GET.get('frbr_uri')
        context['task_groups'] = Task.task_columns(self.form.cleaned_data['state'], context['tasks'])

        Task.decorate_potential_assignees(context['tasks'], self.country)
        Task.decorate_permissions(context['tasks'], self)

        return context


class TaskDetailView(TaskViewBase, DetailView):
    context_object_name = 'task'
    model = Task

    def get_context_data(self, **kwargs):
        context = super(TaskDetailView, self).get_context_data(**kwargs)
        task = self.object

        # merge actions and comments
        actions = task.action_object_actions.all()
        task_content_type = ContentType.objects.get_for_model(self.model)
        comments = Comment.objects\
            .filter(content_type=task_content_type, object_pk=task.id)\
            .select_related('user')
        context['task_timeline'] = sorted(
            chain(comments, actions),
            key=lambda x: x.submit_date if hasattr(x, 'comment') else x.timestamp)

        context['possible_workflows'] = Workflow.objects.unclosed().filter(country=task.country, locality=task.locality).all()

        Task.decorate_potential_assignees([task], self.country)
        Task.decorate_permissions([task], self)

        return context


class TaskCreateView(TaskViewBase, CreateView):
    # permissions
    permission_required = ('indigo_api.add_task',)

    js_view = 'TaskEditView'

    context_object_name = 'task'
    form_class = TaskCreateForm
    model = Task

    def form_valid(self, form):
        response_object = super(TaskCreateView, self).form_valid(form)
        task = self.object
        task.workflows = form.cleaned_data.get('workflows')
        for workflow in task.workflows.all():
            action.send(self.request.user, verb='added', action_object=task, target=workflow,
                        place_code=task.place.place_code)
        return response_object

    def get_form_kwargs(self):
        kwargs = super(TaskCreateView, self).get_form_kwargs()

        task = Task()
        task.country = self.country
        task.locality = self.locality
        task.created_by_user = self.request.user

        if self.request.GET.get('frbr_uri'):
            # pre-load a work
            try:
                work = Work.objects.get(frbr_uri=self.request.GET['frbr_uri'])
                if task.country == work.country and task.locality == work.locality:
                    task.work = work
            except Work.DoesNotExist:
                pass

        kwargs['instance'] = task

        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super(TaskCreateView, self).get_context_data(**kwargs)
        task = context['form'].instance

        work = None
        if task.work:
            work = json.dumps(WorkSerializer(instance=task.work, context={'request': self.request}).data)
        context['work_json'] = work

        document = None
        if task.document:
            document = json.dumps(DocumentSerializer(instance=task.document, context={'request': self.request}).data)
        context['document_json'] = document

        context['task_labels'] = TaskLabel.objects.all()

        context['place_workflows'] = self.place.workflows.filter(closed=False)

        return context

    def get_success_url(self):
        return reverse('task_detail', kwargs={'place': self.kwargs['place'], 'pk': self.object.pk})


class TaskEditView(TaskViewBase, UpdateView):
    # permissions
    permission_required = ('indigo_api.change_task',)

    context_object_name = 'task'
    form_class = TaskEditForm
    model = Task

    def form_valid(self, form):
        task = self.object
        task.updated_by_user = self.request.user

        # action signals
        # first, was something changed other than workflows?
        if form.changed_data:
            action.send(self.request.user, verb='updated', action_object=task,
                        place_code=task.place.place_code)

        new_workflows = form.cleaned_data.get('workflows')
        self.record_workflow_actions(task, new_workflows)
        task.workflows = new_workflows

        return super(TaskEditView, self).form_valid(form)

    def get_form(self, form_class=None):
        form = super(TaskEditView, self).get_form(form_class)
        form.initial['workflows'] = self.object.workflows.all()
        return form

    def get_success_url(self):
        return reverse('task_detail', kwargs={'place': self.kwargs['place'], 'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super(TaskEditView, self).get_context_data(**kwargs)

        work = None
        task = self.object
        if task.work:
            work = json.dumps(WorkSerializer(instance=task.work, context={'request': self.request}).data)
        context['work_json'] = work

        document = None
        if task.document:
            document = json.dumps(DocumentSerializer(instance=task.document, context={'request': self.request}).data)
        context['document_json'] = document

        context['task_labels'] = TaskLabel.objects.all()
        context['place_workflows'] = self.place.workflows.filter(closed=False)

        if has_transition_perm(task.cancel, self):
            context['cancel_task_permission'] = True

        return context


class TaskChangeStateView(TaskViewBase, View, SingleObjectMixin):
    # permissions
    permission_required = ('indigo_api.change_task',)

    change = None
    http_method_names = [u'post']
    model = Task

    def post(self, request, *args, **kwargs):
        task = self.get_object()
        user = self.request.user
        task.updated_by_user = user

        for change, verb in Task.VERBS.iteritems():
            if self.change == change:
                state_change = getattr(task, change)
                if not has_transition_perm(state_change, self):
                    raise PermissionDenied

                state_change(user)

                if change == 'submit':
                    verb = 'submitted for review'
                if change == 'unsubmit':
                    verb = 'returned with changes requested'
                messages.success(request, u"Task '%s' has been %s" % (task.title, verb))

        task.save()

        return redirect(self.get_redirect_url())

    def get_redirect_url(self):
        if self.request.GET.get('next'):
            return self.request.GET.get('next')
        return reverse('task_detail', kwargs={'place': self.kwargs['place'], 'pk': self.kwargs['pk']})


class TaskAssignView(TaskViewBase, View, SingleObjectMixin):
    # permissions
    permission_required = ('indigo_api.change_task',)

    unassign = False
    http_method_names = [u'post']
    model = Task

    def post(self, request, *args, **kwargs):
        task = self.get_object()
        user = self.request.user

        if self.unassign:
            task.assign_to(None, user)
            messages.success(request, u"Task '%s' has been unassigned" % task.title)
        else:
            assignee = User.objects.get(id=self.request.POST.get('user_id'))
            if not task.can_assign_to(assignee):
                raise PermissionDenied
            task.assign_to(assignee, user)
            if user == assignee:
                messages.success(request, u"You have picked up the task '%s'" % task.title)
            else:
                messages.success(request, u"Task '%s' has been assigned" % task.title)

        task.updated_by_user = user
        task.save()

        return redirect(self.get_redirect_url())

    def get_redirect_url(self):
        if self.request.GET.get('next'):
            return self.request.GET.get('next')
        return reverse('task_detail', kwargs={'place': self.kwargs['place'], 'pk': self.kwargs['pk']})


class TaskChangeWorkflowsView(TaskViewBase, View, SingleObjectMixin):
    # permissions
    permission_required = ('indigo_api.change_task',)

    http_method_names = [u'post']
    model = Task

    def post(self, request, *args, **kwargs):
        task = self.get_object()
        user = self.request.user
        task.updated_by_user = user
        ids = self.request.POST.getlist('workflows')

        if ids:
            workflows = Workflow.objects.filter(country=task.country, locality=task.locality, id__in=ids).all()
        else:
            workflows = []

        self.record_workflow_actions(task, workflows)
        task.workflows = workflows

        return redirect(self.get_redirect_url())

    def get_redirect_url(self):
        if self.request.GET.get('next'):
            return self.request.GET.get('next')
        return reverse('task_detail', kwargs={'place': self.kwargs['place'], 'pk': self.kwargs['pk']})


class TaskBulkUpdateView(TaskViewBase, BaseFormView):
    """ Bulk update a set of tasks.
    """
    http_method_names = ['post']
    form_class = BulkTaskUpdateForm
    permission_required = ('indigo_api.change_task',)

    def get_form_kwargs(self):
        kwargs = super(TaskBulkUpdateView, self).get_form_kwargs()
        kwargs['country'] = self.country
        return kwargs

    def form_valid(self, form):
        assignee = form.cleaned_data.get('assigned_to')
        tasks = form.cleaned_data['tasks']
        count = 0

        for task in tasks:
            if task.is_open:
                if form.unassign or (assignee and task.can_assign_to(assignee)):
                    if task.assigned_to != assignee:
                        task.assign_to(assignee, self.request.user)
                        task.updated_by_user = self.request.user
                        task.save()
                        count += 1

        if count > 0:
            plural = 's' if count > 1 else ''
            if form.unassign:
                messages.success(self.request, "Unassigned {} task{}".format(count, plural))
            elif assignee:
                messages.success(self.request, "Assigned {} task{} to {}".format(count, plural, user_display(assignee)))

        return redirect(self.get_redirect_url())

    def form_invalid(self, form):
        messages.error(self.request, "Computer says no.")
        return redirect(self.get_redirect_url())

    def get_redirect_url(self):
        if self.request.GET.get('next'):
            return self.request.GET.get('next')
        return reverse('tasks', kwargs={'place': self.kwargs['place']})


class MyTasksView(AbstractAuthedIndigoView, TemplateView):
    authentication_required = True
    template_name = 'indigo_app/tasks/my_tasks.html'
    tab='my_tasks'

    def get_context_data(self, **kwargs):
        context = super(MyTasksView, self).get_context_data(**kwargs)

        # open tasks assigned to this user
        context['open_assigned_tasks'] = Task.objects \
            .filter(assigned_to=self.request.user, state='open') \
            .all()

        # tasks previously assigned to this user and now pending approval
        context['tasks_pending_approval'] = Task.objects \
            .filter(last_assigned_to=self.request.user, state='pending_review') \
            .all()

        # tasks recently approved
        threshold = datetime.date.today() - datetime.timedelta(days=7)
        context['tasks_recently_approved'] = Task.objects \
            .filter(last_assigned_to=self.request.user, state='done') \
            .filter(updated_at__gte=threshold) \
            .all()[:50]

        return context


class AvailableTasksView(AbstractAuthedIndigoView, ListView):
    authentication_required = True
    template_name = 'indigo_app/tasks/available_tasks.html'
    context_object_name = 'tasks'
    paginate_by = 50
    paginate_orphans = 4
    tab = 'available_tasks'

    def get_queryset(self):
        return Task.objects \
            .filter(assigned_to=None, state__in=Task.OPEN_STATES)\
            .defer('document__document_xml', 'document__search_text', 'document__search_vector') \
            .order_by('-updated_at')
