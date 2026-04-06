from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
import json

from django.utils import timezone
from django.db.models import Count
from datetime import timedelta

from .models import Habit, HabitHistory


# ---------------- HOME PAGES ---------------- #

def index(request):
    return render(request, "home.html")


def about(request):
    return render(request, "about.html")


def contact(request):
    return render(request, "contact.html")


def overview(request):
    return render(request, "overview.html")


# ---------------- AUTHENTICATION ---------------- #

def get_started(request):
    return redirect("register")


def register(request):

    if request.method == "POST":

        name = request.POST.get("name")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if User.objects.filter(username=email).exists():
            messages.error(request, "Email already exists")
            return redirect("register")

        User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name
        )

        messages.success(request, "Account created successfully")
        return redirect("signin")

    return render(request, "register.html")


def signin(request):

    if request.method == "POST":

        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid email or password")
            return redirect("signin")

    return render(request, "signin.html")


def logout_view(request):
    logout(request)
    return redirect("signin")


# ---------------- DASHBOARD ---------------- #

@login_required
def dashboard(request):

    habits = Habit.objects.filter(user=request.user)

    today = timezone.now().date()

    total_habits = habits.count()
    completed_today = habits.filter(last_completed=today).count()

    success_rate = 0
    if total_habits > 0:
        success_rate = int((completed_today / total_habits) * 100)

    # Highest active streak across all habits
    active_streak = habits.order_by("-streak").first()

    # Recent habit activity from history
    recent_activity = HabitHistory.objects.filter(user=request.user).order_by("-date")[:10]

    context = {
        "habits": habits,
        "today": today,
        "total_habits": total_habits,
        "completed_today": completed_today,
        "success_rate": success_rate,
        "active_streak": active_streak.streak if active_streak else 0,
        "recent_activity": recent_activity,
    }

    return render(request, "dashboard.html", context)


# ---------------- HABITS MANAGEMENT ---------------- #

@login_required
def habits(request):

    habits = Habit.objects.filter(user=request.user)
    edit_habit = None
    today = timezone.now().date()

    # COMPLETE HABIT
    if request.GET.get("complete"):

        habit = get_object_or_404(
            Habit,
            id=request.GET.get("complete"),
            user=request.user
        )

        if habit.last_completed != today:

            if habit.last_completed == today - timedelta(days=1):
                habit.streak += 1
            else:
                habit.streak = 1

            habit.total_completed_days += 1
            habit.last_completed = today

            if habit.streak > habit.longest_streak:
                habit.longest_streak = habit.streak

            habit.save()

            # Log history for dashboard recent activity and history page
            HabitHistory.objects.create(user=request.user, habit=habit)

        return redirect("habits")

    # ADD HABIT
    if request.method == "POST":

        if "add_habit" in request.POST:

            Habit.objects.create(
                user=request.user,
                title=request.POST.get("title"),
                description=request.POST.get("description")
            )

            return redirect("habits")

        # UPDATE HABIT
        if "update_habit" in request.POST:

            habit = get_object_or_404(
                Habit,
                id=request.POST.get("habit_id"),
                user=request.user
            )

            habit.title = request.POST.get("title")
            habit.description = request.POST.get("description")
            habit.save()

            return redirect("habits")

    # EDIT MODE
    if request.GET.get("edit"):

        edit_habit = get_object_or_404(
            Habit,
            id=request.GET.get("edit"),
            user=request.user
        )

    # DELETE
    if request.GET.get("delete"):

        habit = get_object_or_404(
            Habit,
            id=request.GET.get("delete"),
            user=request.user
        )

        habit.delete()
        return redirect("habits")

    return render(request, "habits.html", {
        "habits": habits,
        "edit_habit": edit_habit
    })


# ---------------- HISTORY PAGE ---------------- #

@login_required
def history(request):

    filter_type = request.GET.get("filter", "daily")
    today = timezone.now().date()

    # Use a wider window for daily to show some bars even when today's entries are missing.
    if filter_type == "weekly":
        day_window = 28  # 4 weeks
    elif filter_type == "monthly":
        day_window = 90  # ~3 months
    else:
        day_window = 7   # last 7 days for daily view
        filter_type = "daily"

    start_date = today - timedelta(days=day_window - 1)

    history = HabitHistory.objects.filter(
        user=request.user,
        date__gte=start_date
    ).order_by("-date")

    total_entries = history.count()
    unique_habits = history.values("habit").distinct().count()

    # Build chart data for selected filter
    day_count = (today - start_date).days + 1
    chart_labels = []
    chart_data = []

    history_agg = history.values("date").annotate(count=Count("id"))
    history_dict = {item["date"]: item["count"] for item in history_agg}

    for i in range(day_count):
        current_day = start_date + timedelta(days=i)
        chart_labels.append(current_day.strftime("%Y-%m-%d"))
        chart_data.append(history_dict.get(current_day, 0))

    # JSON-serializable for template JS
    chart_labels_json = json.dumps(chart_labels)
    chart_data_json = json.dumps(chart_data)

    return render(request, "history.html", {
        "history": history,
        "filter_type": filter_type,
        "total_entries": total_entries,
        "unique_habits": unique_habits,
        "chart_labels_json": chart_labels_json,
        "chart_data_json": chart_data_json,
    })


# ---------------- STREAKS PAGE ---------------- #

@login_required
def streaks(request):

    habits = Habit.objects.filter(user=request.user)

    if request.method == "POST":
        habit_id = request.POST.get("habit_id")
        habit = Habit.objects.get(id=habit_id, user=request.user)

        today = timezone.now().date()

        if habit.last_completed != today:

            if habit.last_completed == today - timedelta(days=1):
                habit.streak += 1
            else:
                habit.streak = 1

            habit.total_completed_days += 1
            habit.last_completed = today

            if habit.streak > habit.longest_streak:
                habit.longest_streak = habit.streak

            habit.save()

    habits = Habit.objects.filter(user=request.user)

    return render(request, "streaks.html", {"habits": habits})

# ---------------- CHARTS PAGE ---------------- #

@login_required
def charts(request):

    habits = Habit.objects.filter(user=request.user)

    total_habits = habits.count()
    total_completed = sum(h.total_completed_days for h in habits)
    highest_streak = max([h.streak for h in habits], default=0)

    return render(request, "charts.html", {
        "habits": habits,
        "total_habits": total_habits,
        "total_completed": total_completed,
        "highest_streak": highest_streak,
    })


# ---------------- MARK COMPLETE ---------------- #

@login_required
def mark_complete(request, habit_id):

    habit = get_object_or_404(Habit, id=habit_id, user=request.user)

    today = timezone.now().date()

    if habit.last_completed != today:

        if habit.last_completed == today - timedelta(days=1):
            habit.streak += 1
        else:
            habit.streak = 1

        habit.total_completed_days += 1
        habit.last_completed = today

        if habit.streak > habit.longest_streak:
            habit.longest_streak = habit.streak

        habit.save()

        # Save history for dashboard recent activity
        HabitHistory.objects.create(user=request.user, habit=habit)

    return redirect(request.META.get('HTTP_REFERER'))