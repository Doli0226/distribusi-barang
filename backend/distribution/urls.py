from django.urls import path

from . import views

urlpatterns = [
    path("", views.root_api),

    # Auth & profile
    path("auth/login", views.login_api),
    path("auth/logout", views.logout_api),
    path("auth/me", views.me_api),
    path("auth/register", views.register_api),
    path("auth/change-password", views.change_password_api),
    path("auth/reset-password", views.reset_password_api),
    path("auth/profile", views.profile_api),

    # Dashboard
    path("dashboard", views.dashboard_api),

    # Categories
    path("categories", views.categories_api),
    path("categories/<int:pk>", views.category_detail_api),

    # Products
    path("products", views.products_api),
    path("products/<int:pk>", views.product_detail_api),

    # Warehouses
    path("warehouses", views.warehouses_api),
    path("warehouses/<int:pk>", views.warehouse_detail_api),

    # Stock
    path("stocks", views.stocks_api),
    path("stocks/transaction", views.stock_transaction_api),
    path("stocks/transactions", views.stock_transactions_api),

    # Recipients
    path("recipients", views.recipients_api),
    path("recipients/<int:pk>", views.recipient_detail_api),

    # Vehicles
    path("vehicles", views.vehicles_api),
    path("vehicles/<int:pk>", views.vehicle_detail_api),

    # Users (admin)
    path("users", views.users_api),

    # Requests
    path("requests", views.requests_api),
    path("requests/<int:pk>", views.request_detail_api),
    path("requests/<int:pk>/action", views.request_action_api),

    # Distributions
    path("distributions", views.distributions_api),
    path("distributions/<int:pk>", views.distribution_detail_api),
    path("distributions/<int:pk>/status", views.distribution_status_api),

    # Tracking
    path("tracking", views.tracking_api),

    # Notifications
    path("notifications", views.notifications_api),

    # Activity log
    path("activities", views.activity_log_api),

    # Reports
    path("reports/summary", views.reports_summary_api),
    path("reports/<str:kind>/export/<str:fmt>", views.report_export_api),
    path("report-schedules", views.report_schedules_api),
    path("report-schedules/<int:pk>", views.report_schedule_detail_api),
    path("report-schedules/<int:pk>/run", views.report_schedule_run_api),
    path("generated-reports", views.generated_reports_api),
    path("generated-reports/<int:pk>/download", views.generated_report_download_api),
]
