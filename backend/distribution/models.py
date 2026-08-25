from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models


class Profile(models.Model):
    ROLE_CHOICES = [("admin", "Admin"), ("user", "User")]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="user")
    full_name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    avatar_initials = models.CharField(max_length=4, blank=True)


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): return self.name


class Product(models.Model):
    sku = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=160)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    unit = models.CharField(max_length=30, default="pcs")
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    minimum_stock = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Warehouse(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    location = models.CharField(max_length=200)
    city = models.CharField(max_length=80, blank=True)
    capacity = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)


class WarehouseStock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="stocks")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="stocks")
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["product", "warehouse"], name="unique_product_warehouse")]


class StockTransaction(models.Model):
    TYPES = [("in", "Masuk"), ("out", "Keluar"), ("adjust", "Penyesuaian")]
    stock = models.ForeignKey(WarehouseStock, on_delete=models.PROTECT, related_name="transactions")
    transaction_type = models.CharField(max_length=8, choices=TYPES)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    balance_after = models.PositiveIntegerField(default=0)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)


class Recipient(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField()
    city = models.CharField(max_length=80)
    province = models.CharField(max_length=80)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Vehicle(models.Model):
    STATUS = [("available", "Tersedia"), ("in_use", "Digunakan"), ("maintenance", "Perawatan")]
    plate_number = models.CharField(max_length=20, unique=True)
    vehicle_type = models.CharField(max_length=50)
    brand = models.CharField(max_length=80, blank=True)
    capacity = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=15, choices=STATUS, default="available")
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ItemRequest(models.Model):
    STATUSES = [(x, x) for x in ["pending", "processed", "approved", "prepared", "shipped", "in_transit", "arrived", "completed", "rejected"]]
    number = models.CharField(max_length=30, unique=True)
    requester = models.ForeignKey(User, on_delete=models.PROTECT, related_name="item_requests")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    recipient = models.ForeignKey(Recipient, on_delete=models.PROTECT)
    destination = models.TextField()
    needed_date = models.DateField(null=True, blank=True)
    note = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default="pending")
    rejection_reason = models.TextField(blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_requests")
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class RequestItem(models.Model):
    request = models.ForeignKey(ItemRequest, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])


class Distribution(models.Model):
    STATUSES = [(x, x) for x in ["prepared", "in_transit", "arrived", "completed"]]
    number = models.CharField(max_length=30, unique=True)
    request = models.OneToOneField(ItemRequest, on_delete=models.PROTECT, related_name="distribution")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name="distributions")
    destination = models.TextField()
    delivery_number = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default="prepared")
    shipped_at = models.DateTimeField(null=True, blank=True)
    estimated_arrival = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    arrival_photo = models.TextField(blank=True, help_text="Data URL (base64) atau URL bukti kirim")
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_distributions")
    created_at = models.DateTimeField(auto_now_add=True)


class DistributionStatusHistory(models.Model):
    distribution = models.ForeignKey(Distribution, on_delete=models.CASCADE, related_name="history")
    status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.PROTECT)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=160)
    message = models.TextField()
    kind = models.CharField(max_length=30, default="info")
    link = models.CharField(max_length=200, blank=True)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="activities")
    action = models.CharField(max_length=80)
    entity = models.CharField(max_length=80, blank=True)
    entity_id = models.CharField(max_length=40, blank=True)
    detail = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ReportSchedule(models.Model):
    FREQUENCIES = [("daily", "Harian"), ("weekly", "Mingguan"), ("monthly", "Bulanan")]
    KINDS = [("stock", "Stok"), ("requests", "Permintaan"),
             ("distributions", "Distribusi"), ("stock_transactions", "Mutasi Stok")]
    FORMATS = [("csv", "CSV"), ("excel", "Excel"), ("pdf", "PDF")]
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=30, choices=KINDS)
    format = models.CharField(max_length=10, choices=FORMATS, default="pdf")
    frequency = models.CharField(max_length=10, choices=FREQUENCIES, default="monthly")
    day_of_month = models.PositiveSmallIntegerField(default=1)
    day_of_week = models.PositiveSmallIntegerField(default=0)
    active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="report_schedules")
    last_run_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)


class GeneratedReport(models.Model):
    schedule = models.ForeignKey(ReportSchedule, on_delete=models.SET_NULL, null=True, blank=True, related_name="reports")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="inbox_reports")
    kind = models.CharField(max_length=30)
    format = models.CharField(max_length=10)
    filename = models.CharField(max_length=160)
    content_type = models.CharField(max_length=80)
    content_b64 = models.TextField()
    size = models.PositiveIntegerField(default=0)
    downloaded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
