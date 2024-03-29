import getopt
import re

from django.contrib.auth import logout, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.generic import *
from django.views.generic.list import BaseListView
from django.db.models import Q
from django.db import connection

from datetime import date, datetime, timedelta
from django.views.generic.edit import BaseCreateView
from django.views.generic.base import TemplateResponseMixin

from .forms import *
from .utils import *
from .models import *

menu = [{'title': "Animals", 'url_name': 'animals'},
        {'title': "About us", 'url_name': 'about_us'}]


class ShelterHome(DataMixin, ListView):
    template_name = 'shelter/home.html'
    model = Animal
    context_object_name = 'animal'

    def get_queryset(self):
        query = Animal.objects.all()[:3]
        return query

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title="Home page")
        return dict(list(context.items()) + list(c_def.items()))


class AnimalList(DataMixin, ListView):
    model = Animal
    template_name = 'shelter/animal.html'
    context_object_name = 'animal'
    paginate_by = 20

    def get(self, request, *args, **kwargs):
        f_kind = request.GET.get('kind', '')
        f_gender = request.GET.get('gender', '')
        f_age = request.GET.get('age', '')
        self.object_list = Animal.objects.all()

        if f_kind != '':
            if f_kind == 'cat':
                self.object_list = self.object_list.filter(kind='Cat')
            elif f_kind == 'dog':
                self.object_list = self.object_list.filter(kind='Dog')

        if f_gender != '':
            if f_gender == 'female':
                self.object_list = self.object_list.filter(gender='Female')
            elif f_gender == 'male':
                self.object_list = self.object_list.filter(gender='Male')

        if f_age != '':
            if f_age == 'baby':
                self.object_list = self.object_list.filter(age__lte='1')
            elif f_age == 'teen':
                self.object_list = self.object_list.filter(age__gt='1', age__lt='5')
            elif f_age == 'adult':
                self.object_list = self.object_list.filter(age__gte='5')


        context = self.get_context_data(object_list=self.object_list)
        return self.render_to_response(context)

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Animals"
        context['menu'] = menu
        return context


class AnimalProfile(DataMixin, DetailView):
    model = Animal
    template_name = 'shelter/animal_profile.html'
    pk_url_kwarg = 'animalid'
    context_object_name = 'animal'

    # def get(self, request, *args, **kwargs):
    #     to_delete = request.GET.get('delete', '')
    #     a = Animal.objects.get(pk=self.kwargs['animalid'])
    #     if to_delete == '1':
    #         a.delete()
    #
    #     self.object = self.get_object()
    #     context = self.get_context_data(object=self.object)
    #     return self.render_to_response(context)

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = context['animal']
        context['menu'] = menu
        return context


class AnimalDelete(View):
    def get(self, request, *args, **kwargs):
        animal = Animal.objects.get(pk=self.kwargs['animalid'])
        return render(request, 'shelter/animal_delete.html', context={'animal': animal})

    def post(self, request, *args, **kwargs):
        animal = Animal.objects.get(pk=self.kwargs['animalid'])
        animal.delete()
        return redirect(reverse('animals'))

@method_decorator(login_required, name='dispatch')
class EditAnimal(DataMixin, UserPassesTestMixin, UpdateView):
    model = Animal
    template_name = 'shelter/edit_animal_profile.html'
    form_class = EditAnimalForm
    pk_url_kwarg = 'animalid'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title="Edit animal")
        return dict(list(context.items()) + list(c_def.items()))

    def test_func(self):
        if self.request.user.position == "employee":
            return True
        return False

    def get_success_url(self):
        return reverse_lazy('animal', args = [self.kwargs['animalid']])


class ShowAddAnimal(DataMixin, UserPassesTestMixin, CreateView):
    form_class = AddAnimalForm
    template_name = 'shelter/addanimal.html'
    success_url = reverse_lazy('animals')

    def test_func(self):
        if self.request.user.position == "employee":
            return True
        return False

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title="Add animal")
        return dict(list(context.items()) + list(c_def.items()))

def about_us(request):
    context = {
        'menu': menu,
        'title': 'About Us'
    }
    return render(request, 'shelter/about.html', context=context)


class Register(DataMixin, UserPassesTestMixin, CreateView):
    form_class = RegisterUserForm
    template_name = 'shelter/register.html'
    success_url = reverse_lazy('login')

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title="Register")
        return dict(list(context.items()) + list(c_def.items()))

    def test_func(self):
        return self.request.user.is_anonymous

class Login(DataMixin, LoginView):
    form_class = AuthenticationForm
    template_name = 'shelter/login.html'

    def post(self, request, *args, **kwargs):
        a = request.POST.get('username', '')
        try:
            a_d = Account.objects.get(username=a).deleted
        except:
            a_d = None
        if (a_d is not None) and (a_d is True):
            context = {
                'menu': menu,
                'title': 'Error',
                'error': "Account has been deleted"
            }
            return render(request, 'shelter/errors.html', context=context)
        self.object = None
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        """Security check complete. Log the user in."""
        login(self.request, form.get_user())
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title="Log in")
        return dict(list(context.items()) + list(c_def.items()))

    def get_success_url(self):
        return reverse_lazy('home')


def logout_user(request):
    logout(request)
    return redirect('login')


@method_decorator(login_required, name='dispatch')
class PasswordChange(DataMixin, PasswordChangeView):
    template_name = 'shelter/change_password.html'
    form_class = ChangePasswdForm

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title="My profile")
        return dict(list(context.items()) + list(c_def.items()))

    def get_success_url(self):
        return reverse_lazy('mypage')


@method_decorator(login_required, name='dispatch')
class EditProfile(DataMixin, generic.UpdateView):
    model = Account
    template_name = 'shelter/edit_profile.html'
    form_class = EditProfileForm

    def get_object(self):
        return self.request.user

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title="Edit profile")
        return dict(list(context.items()) + list(c_def.items()))

    def get_success_url(self):
        return reverse_lazy('mypage')


@method_decorator(login_required, name='dispatch')
class ShowUserPage(UserPassesTestMixin, DetailView):
    model = Account
    template_name = 'shelter/userpage.html'
    context_object_name = 'account'
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get(self, request, *args, **kwargs):
        to_verify = request.GET.get('verify', '')
        to_delete = request.GET.get('delete', '')
        edit_user = Account.objects.get(username=self.kwargs['username'])
        if to_verify != '':
            if edit_user.position == 'unverified' and to_verify == '1':
                edit_user.position = 'verified'
                edit_user.save()
            elif edit_user.position == 'verified' and to_verify == '0':
                unverify_user(edit_user.pk)
        if to_delete == '1':
            delete_user(edit_user.pk)
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def test_func(self):
        if self.request.user.position == "employee" or self.request.user.position == "admin":
            return True
        return False

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "User page"
        context['menu'] = menu
        return context


@method_decorator(login_required, name='dispatch')
class UserEdit(DataMixin, UserPassesTestMixin, generic.UpdateView):
    model = Account
    template_name = 'shelter/edit_profile.html'
    form_class = EditUserForm
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title="User edit")
        return dict(list(context.items()) + list(c_def.items()))

    def get_success_url(self):
        return reverse_lazy('show_user', args = [self.kwargs['username']])

    def test_func(self):
        if self.request.user.position == "admin":
            return True
        return False


@method_decorator(login_required, name='dispatch')
class AddUser(DataMixin, UserPassesTestMixin, CreateView):
    model = Account
    template_name = 'shelter/edit_profile.html'
    form_class = AdminAddUserForm

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title="Add user")
        return dict(list(context.items()) + list(c_def.items()))

    def get_success_url(self):
        return reverse_lazy('users')

    def test_func(self):
        if self.request.user.position == "admin":
            return True
        return False


@method_decorator(login_required, name='dispatch')
class ShowUsers(UserPassesTestMixin, ListView):
    paginate_by = 5
    model = Account
    template_name = 'shelter/users.html'
    context_object_name = 'accounts'
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get(self, request, *args, **kwargs):
        position = request.GET.get('position', '')
        self.object_list = Account.objects.filter(deleted=False)
        if position != '':
            self.object_list = self.object_list.filter(position=position)
        allow_empty = self.get_allow_empty()

        if not allow_empty:
            if self.get_paginate_by(self.object_list) is not None and hasattr(
                    self.object_list, "exists"
            ):
                is_empty = not self.object_list.exists()
            else:
                is_empty = not self.object_list
            if is_empty:
                raise Http404("Empty list and “%(class_name)s.allow_empty” is False.")
        context = self.get_context_data()
        return self.render_to_response(context)

    def test_func(self):
        if self.request.user.position == "employee" or self.request.user.position == "admin":
            return True
        return False

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Users"
        context['menu'] = menu
        return context


class ManageAnimalWalks(DataMixin, UserPassesTestMixin, BaseListView, TemplateResponseMixin):
    model = Walk
    template_name = 'shelter/manage_walks.html'
    context_object_name = 'walks'
    pk_url_kwarg = 'animalid'
    paginate_by = 15

    def post(self, request, *args, **kwargs):
        try:
            a = Animal.objects.get(pk=self.kwargs['animalid'])
        except:
            raise Http404

        start = request.POST.get('starting', '')
        end = request.POST.get('ending', '')

        if not (re.fullmatch(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}', start) and
                re.fullmatch(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}', end)):
            self.object_list = self.get_queryset()
            context = self.get_context_data(object_list=self.object_list, error="Bad date", pk=self.kwargs['animalid'])
            return self.render_to_response(context)

        start_d = datetime.strptime(start, '%Y-%m-%dT%H:%M')
        end_d = datetime.strptime(end, '%Y-%m-%dT%H:%M')

        if start_d >= end_d or start_d < datetime.today():
            self.object_list = self.get_queryset()
            context = self.get_context_data(object_list=self.object_list, error="Bad date", pk=self.kwargs['animalid'])
            return self.render_to_response(context)

        b = Walk.objects.filter(starting__lte=start_d).filter(ending__gte=start_d).filter(starting__lte=end_d).filter(
            ending__gte=end_d).filter(animal_id=self.kwargs['animalid'])
        tasks = Task.objects.filter(task_start__lte=start_d).filter(task_end__gte=start_d).filter(
            task_start__lte=end_d).filter(task_end__gte=end_d).filter(animal_id=self.kwargs['animalid'])
        d = Walk.objects.all()[:1]
        e = Task.objects.all()[:1]
        if (b.exists() and d.exists()) or (e.exists and (tasks.exists())):
            self.object_list = self.get_queryset()
            context = self.get_context_data(object_list=self.object_list, error="overlap with another event",
                                            pk=self.kwargs['animalid'])
            return self.render_to_response(context)
        Walk.objects.create(animal=a, starting=start_d, ending=end_d)
        self.object_list = self.get_queryset()
        context = self.get_context_data(object_list=self.object_list, pk=self.kwargs['animalid'])
        return self.render_to_response(context)

    def get(self, request, *args, **kwargs):
        walk_id = request.GET.get('walk', '')
        if walk_id != '':
            to_delete = request.GET.get('delete', '')
            to_confirm = request.GET.get('confirm', '')
            try:
                walk = Walk.objects.get(pk=int(walk_id))
            except Walk.DoesNotExist:
                walk = None
            if walk is not None:
                if to_delete != '' and walk.status == "free" and to_delete.isdecimal():
                    walk.delete()
                elif to_confirm == '1' and walk.status == "not confirmed":
                    walk.status = "confirmed"
                    walk.save()
                elif to_confirm == '0' and (walk.status == "confirmed" or walk.status == "confirmed"):
                    walk.status = "free"
                    walk.walker_id = None
                    walk.save()

        self.object_list = self.get_queryset()
        allow_empty = self.get_allow_empty()

        if not allow_empty:
            if self.get_paginate_by(self.object_list) is not None and hasattr(
                    self.object_list, "exists"
            ):
                is_empty = not self.object_list.exists()
            else:
                is_empty = not self.object_list
            if is_empty:
                raise Http404("Empty list and “%(class_name)s.allow_empty” is False.")
        context = self.get_context_data(pk=self.kwargs['animalid'])
        return self.render_to_response(context)

    def get_queryset(self):
        queryset = Walk.objects.filter(animal_id=self.kwargs['animalid']).select_related('walker')
        return queryset

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title="Create Walk")
        return dict(list(context.items()) + list(c_def.items()))

    def test_func(self):
        if self.request.user.position == "employee":
            return True
        return False


@method_decorator(login_required, name='dispatch')
class UserWalks(DataMixin, UserPassesTestMixin, BaseListView, TemplateResponseMixin):
    model = Walk
    template_name = 'shelter/user_walks.html'
    context_object_name = 'walks'
    pk_url_kwarg = 'animalid'
    paginate_by = 15

    def get(self, request, *args, **kwargs):
        walk_id = request.GET.get('walk', '')
        if walk_id != '':
            to_register = request.GET.get('register', '')
            walk = Walk.objects.get(pk=int(walk_id))
            if to_register == '1' and walk.status == "free":
                walk.walker_id = request.user.pk
                walk.status = "not confirmed"
                walk.save()
            elif to_register == '0' and (
                    walk.status == "confirmed" or walk.status == "not confirmed") and walk.walker_id == request.user.pk:
                walk.status = "free"
                walk.walker_id = None
                walk.save()

        self.object_list = self.get_queryset()
        allow_empty = self.get_allow_empty()

        if not allow_empty:
            if self.get_paginate_by(self.object_list) is not None and hasattr(
                    self.object_list, "exists"
            ):
                is_empty = not self.object_list.exists()
            else:
                is_empty = not self.object_list
            if is_empty:
                raise Http404("Empty list and “%(class_name)s.allow_empty” is False.")
        context = self.get_context_data(pk=self.kwargs['animalid'])
        return self.render_to_response(context)

    def get_queryset(self):
        queryset = Walk.objects.filter(animal_id=self.kwargs['animalid']).filter(
            starting__gte=date.today()).select_related('walker').filter(Q(walker_id=None) | Q(walker_id=self.request.user.pk))
        return queryset

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title="Walks")
        return dict(list(context.items()) + list(c_def.items()))

    def test_func(self):
        if self.request.user.position == "verified":
            return True
        return False


@method_decorator(login_required, name='dispatch')
class UserProfileWalks(DataMixin, BaseListView, TemplateResponseMixin):
    model = Walk
    template_name = 'shelter/mypage.html'
    context_object_name = 'walks'
    paginate_by = 10

    def get(self, request, *args, **kwargs):
        if request.user.position == "verified":
            walk_id = request.GET.get('walk', '')
            if walk_id != '':
                to_register = request.GET.get('register', '')
                walk = Walk.objects.get(pk=int(walk_id))
                if to_register == '0' and (
                        walk.status == "confirmed" or walk.status == "not confirmed") and walk.walker_id == request.user.pk:
                    walk.status = "not confirmed"
                    walk.walker_id = None
                    walk.save()

        self.object_list = self.get_queryset(request)
        allow_empty = self.get_allow_empty()

        if not allow_empty:
            if self.get_paginate_by(self.object_list) is not None and hasattr(
                    self.object_list, "exists"
            ):
                is_empty = not self.object_list.exists()
            else:
                is_empty = not self.object_list
            if is_empty:
                raise Http404("Empty list and “%(class_name)s.allow_empty” is False.")
        context = self.get_context_data()
        return self.render_to_response(context)

    def get_queryset(self, request):
        queryset = Walk.objects.filter(walker_id=request.user.pk).select_related('walker')
        return queryset

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title="Walks")
        return dict(list(context.items()) + list(c_def.items()))


@method_decorator(login_required, name='dispatch')
class TodayWalks(DataMixin, UserPassesTestMixin, BaseListView, TemplateResponseMixin):
    model = Walk
    template_name = 'shelter/today_walks.html'
    context_object_name = 'walks'
    paginate_by = 15

    def get(self, request, *args, **kwargs):
        walk_id = request.GET.get('walk', '')
        if walk_id != '':
            start = request.GET.get('start', '')
            end = request.GET.get('end', '')
            walk = Walk.objects.get(pk=int(walk_id))
            if start == '1' and walk.status == "confirmed":
                walk.status = "started"
                walk.save()
            if end == '1' and walk.status == "started":
                walk.status = "end"
                walk.save()

        filter_date = self.request.GET.get('date', '')
        filter_status = self.request.GET.get('status', '')

        if not (re.fullmatch(r'^\d{4}-\d{2}-\d{2}', filter_date)) and filter_date != '':
            self.object_list = Walk.objects.none()
            context = self.get_context_data(error="Bad date")
            return self.render_to_response(context)

        self.object_list = Walk.objects.all()

        if filter_date != '':
            filter_date = datetime.strptime(filter_date, "%Y-%m-%d")
            self.object_list = self.object_list.filter(Q(starting__gte=filter_date) & Q(starting__lte=(filter_date + timedelta(days=1))))
        if not(filter_status == 'all' or filter_status == ''):
            self.object_list = self.object_list.filter(status=filter_status)

        allow_empty = self.get_allow_empty()

        if not allow_empty:
            if self.get_paginate_by(self.object_list) is not None and hasattr(
                    self.object_list, "exists"
            ):
                is_empty = not self.object_list.exists()
            else:
                is_empty = not self.object_list
            if is_empty:
                raise Http404("Empty list and “%(class_name)s.allow_empty” is False.")
        context = self.get_context_data()
        return self.render_to_response(context)

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title="Walks")
        return dict(list(context.items()) + list(c_def.items()))

    def test_func(self):
        if self.request.user.position == "employee":
            return True
        return False


@method_decorator(login_required, name='dispatch')
class EditHealth(DataMixin, UserPassesTestMixin, UpdateView):
    model = Animal
    template_name = 'shelter/edit_health.html'
    form_class = EditAnimalHealthForm
    pk_url_kwarg = 'animalid'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title="Health")
        return dict(list(context.items()) + list(c_def.items()))

    def test_func(self):
        if self.request.user.position == "vet":
            return True
        return False

    def get_success_url(self):
        return reverse_lazy('animal', args = [self.kwargs['animalid']])




class ManageTasksForVet(DataMixin, UserPassesTestMixin, BaseListView, TemplateResponseMixin):
    model = Task
    template_name = 'shelter/manage_tasks.html'
    context_object_name = 'tasks'
    pk_url_kwarg = 'animalid'
    paginate_by = 15

    def post(self, request, *args, **kwargs):
        try:
            a = Animal.objects.get(pk=self.kwargs['animalid'])
        except:
            raise Http404

        if request.user.position == 'employee':
            description = request.POST.get('description', '')
            Task.objects.create(animal=a, description=description, created=datetime.today())
        self.object_list = self.get_queryset()
        context = self.get_context_data(object_list=self.object_list, pk=self.kwargs['animalid'])
        return self.render_to_response(context)

    def get(self, request, *args, **kwargs):
        task_id = request.GET.get('task', '')
        if task_id != '':
            to_delete = request.GET.get('delete', '')
            try:
                task = Task.objects.get(pk=int(task_id))
            except Task.DoesNotExist:
                task = None
            if task is not None:
                if to_delete == '1' and (task.status == "created" or task.status == "scheduled"):
                    task.delete()

        self.object_list = self.get_queryset()
        allow_empty = self.get_allow_empty()

        if not allow_empty:
            if self.get_paginate_by(self.object_list) is not None and hasattr(
                    self.object_list, "exists"
            ):
                is_empty = not self.object_list.exists()
            else:
                is_empty = not self.object_list
            if is_empty:
                raise Http404("Empty list and “%(class_name)s.allow_empty” is False.")
        context = self.get_context_data(pk=self.kwargs['animalid'])
        return self.render_to_response(context)

    def get_queryset(self):
        queryset = Task.objects.filter(animal_id=self.kwargs['animalid']).select_related('vet')
        return queryset

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title="Manage Tasks")
        return dict(list(context.items()) + list(c_def.items()))

    def test_func(self):
        if self.request.user.position == "employee" or self.request.user.position == "vet":
            return True
        return False


@method_decorator(login_required, name='dispatch')
class ShowTask(UserPassesTestMixin, DetailView):
    model = Task
    template_name = 'shelter/vet_task.html'
    context_object_name = 'task'
    pk_url_kwarg = 'taskid'

    def get(self, request, *args, **kwargs):
        cancel = request.GET.get('cancel', '')
        end = request.GET.get('end', '')
        try:
            obj = Task.objects.get(pk=self.kwargs['taskid'])
        except:
            raise Http404
        if request.user.pk == obj.vet_id:
            if obj.status == 'scheduled' and cancel == '1':
                obj.status = 'created'
                obj.vet = None
                obj.task_start = None
                obj.task_end = None
                obj.save()
            elif obj.status == 'scheduled' and end == '1':
                obj.status = 'ended'
                obj.save()

        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        take = request.POST.get('take', '')
        start = request.POST.get('starting', '')
        end = request.POST.get('ending', '')
        if take != '1' or request.user.position != 'vet':
            self.object = self.get_object()
            context = self.get_context_data(object=self.object, error="Bad form input, or no permissions",
                                            pk=self.kwargs['taskid'])
            return self.render_to_response(context)

        if not (re.fullmatch(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}', start) and
                re.fullmatch(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}', end)):
            self.object = self.get_object()
            context = self.get_context_data(object=self.object, error="Bad date", pk=self.kwargs['taskid'])
            return self.render_to_response(context)

        start_d = datetime.strptime(start, '%Y-%m-%dT%H:%M')
        end_d = datetime.strptime(end, '%Y-%m-%dT%H:%M')

        if start_d >= end_d or start_d < datetime.today():
            self.object = self.get_object()
            context = self.get_context_data(object=self.object, error="Bad date", pk=self.kwargs['taskid'])
            return self.render_to_response(context)
        try:
            obj = Task.objects.get(pk=self.kwargs['taskid'])
        except:
            raise Http404
        b = Task.objects.filter(task_start__lte=start_d).filter(task_end__gte=start_d).filter(
            task_start__lte=end_d).filter(
            task_end__gte=end_d).filter(animal_id=obj.animal_id)
        walk = Walk.objects.filter(starting__lte=start_d).filter(ending__gte=start_d).filter(
            starting__lte=end_d).filter(
            ending__gte=end_d).filter(animal_id=obj.animal_id)
        vet_tasks = Task.objects.filter(task_start__lte=start_d).filter(task_end__gte=start_d).filter(
            task_start__lte=end_d).filter(
            task_end__gte=end_d).filter(vet_id=obj.vet_id)
        d = Task.objects.all()[:1]
        e = Walk.objects.all()[:1]
        if (b.exists() and d.exists()) or (e.exists and (walk.exists())):
            self.object = self.get_object()
            context = self.get_context_data(object=self.object, error="overlap with another task or walk",
                                            pk=self.kwargs['taskid'])
            return self.render_to_response(context)
        if (vet_tasks.exists() and d.exists()):
            self.object = self.get_object()
            context = self.get_context_data(object=self.object, error="overlap with another your task",
                                            pk=self.kwargs['taskid'])
            return self.render_to_response(context)
        if take == '1' and obj.status == 'created':
            obj.vet = request.user
            obj.task_start = start_d
            obj.task_end = end_d
            obj.status = "scheduled"
            obj.save()

        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def test_func(self):
        if self.request.user.position == "employee" or self.request.user.position == "vet":
            return True
        return False

    def get_object(self, queryset=None):
        try:
            context = Task.objects.select_related('animal').select_related('vet').get(pk=self.kwargs['taskid'])
        except:
            raise Http404
        return context

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Task page"
        context['menu'] = menu
        return context


@method_decorator(login_required, name='dispatch')
class NewTasks(DataMixin, UserPassesTestMixin, BaseListView, TemplateResponseMixin):
    model = Task
    template_name = 'shelter/task_list.html'
    context_object_name = 'tasks'
    paginate_by = 7
    title = "New Tasks"
    def get_queryset(self):
        queryset = Task.objects.filter(status='created')
        return queryset

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title=self.title)
        return dict(list(context.items()) + list(c_def.items()))

    def test_func(self):
        if self.request.user.position == "vet":
            return True
        return False


class MyTasks(NewTasks):
    title = "My Tasks"
    def get_queryset(self):
        queryset = Task.objects.filter(vet_id=self.request.user.pk)
        return queryset
