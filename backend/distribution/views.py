import csv
import io
import json
from datetime import date, datetime
from functools import wraps

from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import (ActivityLog, Category, Distribution, DistributionStatusHistory, ItemRequest, Notification,
                     Product, Profile, Recipient, RequestItem, StockTransaction, Vehicle, Warehouse, WarehouseStock)


# ---------- helpers ----------
def payload(request):
    try: return json.loads(request.body or "{}")
    except json.JSONDecodeError: return {}


def next_number(model, prefix, year):
    """Compute next sequence number safely by scanning existing numbers."""
    prefix_full = f"{prefix}-{year}-"
    max_seq = 0
    for n in model.objects.filter(number__startswith=prefix_full).values_list("number", flat=True):
        try: max_seq = max(max_seq, int(n.rsplit("-", 1)[-1]))
        except (ValueError, IndexError): pass
    return f"{prefix_full}{max_seq + 1:04d}"


def get_or_404(model_or_qs, **kwargs):
    """Return object or None (accepts model class or QuerySet)."""
    qs = model_or_qs if hasattr(model_or_qs, "filter") else model_or_qs.objects
    try: return qs.get(**kwargs)
    except Exception: return None


def parse_date(value):
    """Parse ISO date string to date, return None for empty."""
    if not value: return None
    if isinstance(value, date): return value
    try: return date.fromisoformat(str(value)[:10])
    except ValueError: return None


def catch_errors(view):
    """Convert DoesNotExist -> 404 and KeyError -> 400 responses."""
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except (Category.DoesNotExist, Product.DoesNotExist, Warehouse.DoesNotExist,
                WarehouseStock.DoesNotExist, Recipient.DoesNotExist, Vehicle.DoesNotExist,
                ItemRequest.DoesNotExist, Distribution.DoesNotExist, User.DoesNotExist,
                Notification.DoesNotExist):
            return JsonResponse({"detail": "Data tidak ditemukan"}, status=404)
        except KeyError as e:
            return JsonResponse({"detail": f"Field wajib hilang: {e.args[0]}"}, status=400)
        except (ValueError, TypeError) as e:
            return JsonResponse({"detail": f"Nilai tidak valid: {e}"}, status=400)
        except Exception as e:
            import logging
            logging.getLogger("distribution").exception("Unhandled error in %s", view.__name__)
            return JsonResponse({"detail": "Terjadi kesalahan di server. Silakan coba lagi."}, status=500)
    return wrapped


def client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")


def log_activity(request, action, entity="", entity_id="", detail=""):
    ActivityLog.objects.create(user=request.user if request.user.is_authenticated else None,
                               action=action, entity=entity, entity_id=str(entity_id),
                               detail=detail, ip_address=client_ip(request))


def is_admin(user):
    if not user.is_authenticated: return False
    if user.is_superuser or user.is_staff: return True
    return getattr(getattr(user, "profile", None), "role", "") == "admin"


def auth_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated: return JsonResponse({"detail": "Login diperlukan"}, status=401)
        return view(request, *args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated: return JsonResponse({"detail": "Login diperlukan"}, status=401)
        if not is_admin(request.user): return JsonResponse({"detail": "Akses Admin diperlukan"}, status=403)
        return view(request, *args, **kwargs)
    return wrapped


def user_data(user):
    profile = getattr(user, "profile", None)
    return {
        "id": user.id, "username": user.username, "email": user.email,
        "full_name": (profile.full_name if profile else "") or user.get_full_name() or user.username,
        "phone": profile.phone if profile else "",
        "initials": (profile.avatar_initials if profile and profile.avatar_initials else (user.username[:2].upper())),
        "role": "admin" if is_admin(user) else "user",
    }


def notify(user, title, message, kind="info", link=""):
    Notification.objects.create(user=user, title=title, message=message, kind=kind, link=link)


def notify_admins(title, message, kind="info", link="", exclude_user=None):
    qs = User.objects.filter(Q(is_superuser=True) | Q(is_staff=True) | Q(profile__role="admin")).distinct()
    if exclude_user: qs = qs.exclude(pk=exclude_user.pk)
    for u in qs:
        Notification.objects.create(user=u, title=title, message=message, kind=kind, link=link)


def stock_of(product):
    return sum(s.quantity for s in product.stocks.all())


# ---------- AUTH ----------
@csrf_exempt
@require_http_methods(["POST"])
@catch_errors
def login_api(request):
    data = payload(request)
    identifier = data.get("email") or data.get("username", "")
    user = authenticate(username=identifier, password=data.get("password", ""))
    if not user:
        log_activity(request, "login_failed", "auth", detail=identifier)
        return JsonResponse({"detail": "Email atau password salah"}, status=401)
    login(request, user)
    log_activity(request, "login", "auth", entity_id=user.id)
    return JsonResponse({"user": user_data(user), "message": "Login berhasil"})


@csrf_exempt
@require_http_methods(["POST"])
def logout_api(request):
    if request.user.is_authenticated:
        log_activity(request, "logout", "auth", entity_id=request.user.id)
    logout(request)
    return JsonResponse({"message": "Logout berhasil"})


@csrf_exempt
@require_http_methods(["POST"])
@catch_errors
def register_api(request):
    data = payload(request)
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    full_name = data.get("full_name", "").strip()
    if not email or not password: return JsonResponse({"detail": "Email dan password wajib diisi"}, status=400)
    if len(password) < 6: return JsonResponse({"detail": "Password minimal 6 karakter"}, status=400)
    if User.objects.filter(username=email).exists(): return JsonResponse({"detail": "Email sudah terdaftar"}, status=400)
    user = User.objects.create_user(username=email, email=email, password=password, first_name=full_name)
    Profile.objects.create(user=user, role="user", full_name=full_name,
                           avatar_initials="".join(p[0] for p in (full_name or email).split()[:2]).upper() or email[:2].upper())
    log_activity(request, "register", "user", entity_id=user.id, detail=email)
    login(request, user)
    return JsonResponse({"user": user_data(user), "message": "Registrasi berhasil"}, status=201)


@csrf_exempt
@auth_required
@require_http_methods(["POST"])
@catch_errors
def change_password_api(request):
    data = payload(request)
    if not request.user.check_password(data.get("current_password", "")):
        return JsonResponse({"detail": "Password saat ini salah"}, status=400)
    new_pwd = data.get("new_password", "")
    if len(new_pwd) < 6: return JsonResponse({"detail": "Password baru minimal 6 karakter"}, status=400)
    request.user.set_password(new_pwd)
    request.user.save()
    update_session_auth_hash(request, request.user)
    log_activity(request, "change_password", "user", entity_id=request.user.id)
    return JsonResponse({"message": "Password berhasil diubah"})


@csrf_exempt
@require_http_methods(["POST"])
@catch_errors
def reset_password_api(request):
    """Demo reset - set password langsung (tanpa email untuk kesederhanaan demo)."""
    data = payload(request)
    email = data.get("email", "").strip().lower()
    new_pwd = data.get("new_password", "")
    if len(new_pwd) < 6: return JsonResponse({"detail": "Password baru minimal 6 karakter"}, status=400)
    try: user = User.objects.get(username=email)
    except User.DoesNotExist: return JsonResponse({"detail": "Email tidak ditemukan"}, status=404)
    user.set_password(new_pwd); user.save()
    log_activity(request, "reset_password", "user", entity_id=user.id, detail=email)
    return JsonResponse({"message": "Password berhasil direset. Silakan login."})


@auth_required
def me_api(request): return JsonResponse({"user": user_data(request.user)})


@csrf_exempt
@auth_required
@require_http_methods(["POST"])
@catch_errors
def profile_api(request):
    data = payload(request)
    profile, _ = Profile.objects.get_or_create(user=request.user)
    profile.full_name = data.get("full_name", profile.full_name)
    profile.phone = data.get("phone", profile.phone)
    if profile.full_name:
        profile.avatar_initials = "".join(p[0] for p in profile.full_name.split()[:2]).upper()
    profile.save()
    email = data.get("email")
    if email and email != request.user.email:
        request.user.email = email; request.user.username = email; request.user.save()
    log_activity(request, "update_profile", "user", entity_id=request.user.id)
    return JsonResponse({"user": user_data(request.user), "message": "Profil diperbarui"})


# ---------- DASHBOARD ----------
@auth_required
def dashboard_api(request):
    admin = is_admin(request.user)
    products = Product.objects.filter(active=True)
    req_qs = ItemRequest.objects.all() if admin else ItemRequest.objects.filter(requester=request.user)
    dist_qs = Distribution.objects.all() if admin else Distribution.objects.filter(request__requester=request.user)

    total_stock = WarehouseStock.objects.aggregate(t=Sum("quantity"))["t"] or 0
    low_stock_products = [p for p in products.prefetch_related("stocks") if stock_of(p) < p.minimum_stock]

    # 6 months chart
    now = timezone.now()
    months = []
    for i in range(5, -1, -1):
        m = (now.replace(day=1) - timezone.timedelta(days=30 * i))
        month_start = m.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = (month_start + timezone.timedelta(days=32)).replace(day=1)
        count = dist_qs.filter(created_at__gte=month_start, created_at__lt=next_month).count()
        months.append({"name": month_start.strftime("%b"), "total": count})

    # category pie
    cat_counts = (RequestItem.objects.filter(request__in=req_qs)
                  .values("product__category__name").annotate(v=Sum("quantity")).order_by("-v")[:5])
    palette = ["#2563eb", "#14b8a6", "#f59e0b", "#f97316", "#8b5cf6"]
    pie = [{"name": c["product__category__name"] or "Lainnya", "value": c["v"] or 0, "color": palette[i]}
           for i, c in enumerate(cat_counts)]

    # top products
    top_products = (RequestItem.objects.filter(request__in=req_qs)
                    .values("product__name").annotate(total=Sum("quantity")).order_by("-total")[:5])

    return JsonResponse({
        "stats": {
            "total_products": products.count(),
            "total_stock": total_stock,
            "total_users": User.objects.count() if admin else 0,
            "total_requests": req_qs.count(),
            "pending_requests": req_qs.filter(status="pending").count(),
            "approved_requests": req_qs.filter(status="approved").count(),
            "processed_requests": req_qs.filter(status__in=["processed", "prepared"]).count(),
            "total_distributions": dist_qs.count(),
            "active_distributions": dist_qs.exclude(status="completed").count(),
            "completed_distributions": dist_qs.filter(status="completed").count(),
            "low_stock_count": len(low_stock_products),
        },
        "distribution_chart": months,
        "category_chart": pie,
        "top_products": [{"name": t["product__name"], "total": t["total"]} for t in top_products],
        "recent_requests": [{"number": r.number, "requester": r.requester.username,
                              "item": (r.items.first().product.name if r.items.exists() else "-"),
                              "quantity": (r.items.first().quantity if r.items.exists() else 0),
                              "status": r.status, "created_at": r.created_at.strftime("%d %b %Y")}
                             for r in req_qs.order_by("-created_at")[:6]],
        "low_stock": [{"sku": p.sku, "name": p.name, "stock": stock_of(p), "minimum_stock": p.minimum_stock}
                       for p in low_stock_products[:8]],
        "recent_activities": [{"action": a.action, "entity": a.entity, "detail": a.detail,
                                "user": a.user.username if a.user else "Sistem",
                                "created_at": a.created_at.strftime("%d %b %Y %H:%M")}
                               for a in ActivityLog.objects.select_related("user").order_by("-created_at")[:8]] if admin else [],
        "user": user_data(request.user),
    })


# ---------- CATEGORIES ----------
@csrf_exempt
@auth_required
@catch_errors
def categories_api(request):
    if request.method == "GET":
        return JsonResponse({"items": list(Category.objects.values("id", "name", "description", "active"))})
    if not is_admin(request.user): return JsonResponse({"detail": "Akses Admin diperlukan"}, status=403)
    data = payload(request)
    if request.method == "POST":
        cat = Category.objects.create(name=data["name"], description=data.get("description", ""),
                                       active=data.get("active", True))
        log_activity(request, "create", "category", entity_id=cat.id, detail=cat.name)
        return JsonResponse({"id": cat.id, "name": cat.name}, status=201)
    return JsonResponse({"detail": "Method tidak didukung"}, status=405)


@csrf_exempt
@admin_required
@catch_errors
def category_detail_api(request, pk):
    cat = Category.objects.get(pk=pk)
    if request.method == "PUT":
        data = payload(request)
        cat.name = data.get("name", cat.name); cat.description = data.get("description", cat.description)
        cat.active = data.get("active", cat.active); cat.save()
        log_activity(request, "update", "category", entity_id=cat.id, detail=cat.name)
        return JsonResponse({"id": cat.id, "name": cat.name})
    if request.method == "DELETE":
        cat.active = False; cat.save()
        log_activity(request, "deactivate", "category", entity_id=cat.id)
        return JsonResponse({"message": "Kategori dinonaktifkan"})
    return JsonResponse({"detail": "Method tidak didukung"}, status=405)


# ---------- PRODUCTS ----------
def product_json(p):
    stock = stock_of(p)
    return {"id": p.id, "sku": p.sku, "name": p.name, "category": p.category.name,
            "category_id": p.category_id, "unit": p.unit, "description": p.description,
            "image_url": p.image_url, "stock": stock, "minimum_stock": p.minimum_stock,
            "active": p.active, "status": "Aktif" if p.active else "Nonaktif",
            "low_stock": stock < p.minimum_stock,
            "stock_status": "Stok rendah" if stock < p.minimum_stock else ("Aktif" if p.active else "Nonaktif")}


@csrf_exempt
@auth_required
@catch_errors
def products_api(request):
    if request.method == "GET":
        qs = Product.objects.select_related("category").prefetch_related("stocks")
        if not is_admin(request.user):
            qs = qs.filter(active=True)
        q = request.GET.get("q", "").strip()
        if q: qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q))
        cat = request.GET.get("category")
        if cat: qs = qs.filter(category_id=cat)
        return JsonResponse({"items": [product_json(p) for p in qs]})
    if not is_admin(request.user): return JsonResponse({"detail": "Akses Admin diperlukan"}, status=403)
    if request.method == "POST":
        data = payload(request)
        category = Category.objects.get(pk=data["category_id"]) if data.get("category_id") else Category.objects.get_or_create(name=data.get("category", "Umum"))[0]
        p = Product.objects.create(sku=data["sku"], name=data["name"], category=category,
                                    unit=data.get("unit", "pcs"), description=data.get("description", ""),
                                    image_url=data.get("image_url", ""),
                                    minimum_stock=data.get("minimum_stock", 0),
                                    active=data.get("active", True))
        log_activity(request, "create", "product", entity_id=p.id, detail=p.name)
        return JsonResponse(product_json(p), status=201)
    return JsonResponse({"detail": "Method tidak didukung"}, status=405)


@csrf_exempt
@admin_required
@catch_errors
def product_detail_api(request, pk):
    p = Product.objects.select_related("category").prefetch_related("stocks").get(pk=pk)
    if request.method == "GET": return JsonResponse(product_json(p))
    if request.method == "PUT":
        data = payload(request)
        for field in ["name", "sku", "unit", "description", "image_url"]:
            if field in data: setattr(p, field, data[field])
        if "minimum_stock" in data: p.minimum_stock = data["minimum_stock"]
        if "active" in data: p.active = data["active"]
        if "category_id" in data: p.category_id = data["category_id"]
        p.save()
        log_activity(request, "update", "product", entity_id=p.id, detail=p.name)
        return JsonResponse(product_json(p))
    if request.method == "DELETE":
        p.active = False; p.save()
        log_activity(request, "deactivate", "product", entity_id=p.id, detail=p.name)
        return JsonResponse({"message": "Barang dinonaktifkan"})
    return JsonResponse({"detail": "Method tidak didukung"}, status=405)


# ---------- WAREHOUSES ----------
@csrf_exempt
@auth_required
@catch_errors
def warehouses_api(request):
    if request.method == "GET":
        return JsonResponse({"items": list(Warehouse.objects.values("id", "code", "name", "location", "city", "capacity", "active"))})
    if not is_admin(request.user): return JsonResponse({"detail": "Akses Admin diperlukan"}, status=403)
    if request.method == "POST":
        data = payload(request)
        w = Warehouse.objects.create(code=data["code"], name=data["name"], location=data.get("location", ""),
                                      city=data.get("city", ""), capacity=data.get("capacity", 0),
                                      active=data.get("active", True))
        log_activity(request, "create", "warehouse", entity_id=w.id, detail=w.name)
        return JsonResponse({"id": w.id, "name": w.name}, status=201)
    return JsonResponse({"detail": "Method tidak didukung"}, status=405)


@csrf_exempt
@admin_required
@catch_errors
def warehouse_detail_api(request, pk):
    w = Warehouse.objects.get(pk=pk)
    if request.method == "PUT":
        data = payload(request)
        for f in ["code", "name", "location", "city"]:
            if f in data: setattr(w, f, data[f])
        if "capacity" in data: w.capacity = data["capacity"]
        if "active" in data: w.active = data["active"]
        w.save()
        log_activity(request, "update", "warehouse", entity_id=w.id, detail=w.name)
        return JsonResponse({"id": w.id, "name": w.name})
    if request.method == "DELETE":
        w.active = False; w.save()
        log_activity(request, "deactivate", "warehouse", entity_id=w.id, detail=w.name)
        return JsonResponse({"message": "Gudang dinonaktifkan"})
    return JsonResponse({"detail": "Method tidak didukung"}, status=405)


# ---------- STOCK ----------
@csrf_exempt
@auth_required
@catch_errors
def stocks_api(request):
    if request.method == "GET":
        qs = WarehouseStock.objects.select_related("product", "warehouse", "product__category")
        wh = request.GET.get("warehouse")
        if wh: qs = qs.filter(warehouse_id=wh)
        items = [{"id": s.id, "product_id": s.product_id, "product_sku": s.product.sku,
                   "product_name": s.product.name, "category": s.product.category.name,
                   "unit": s.product.unit, "warehouse_id": s.warehouse_id,
                   "warehouse_name": s.warehouse.name, "quantity": s.quantity,
                   "minimum_stock": s.product.minimum_stock,
                   "low_stock": s.quantity < s.product.minimum_stock}
                  for s in qs]
        return JsonResponse({"items": items})
    if not is_admin(request.user): return JsonResponse({"detail": "Akses Admin diperlukan"}, status=403)
    if request.method == "POST":
        data = payload(request)
        stock, _ = WarehouseStock.objects.get_or_create(product_id=data["product_id"], warehouse_id=data["warehouse_id"])
        return JsonResponse({"id": stock.id, "quantity": stock.quantity}, status=201)
    return JsonResponse({"detail": "Method tidak didukung"}, status=405)


@csrf_exempt
@admin_required
@require_http_methods(["POST"])
@catch_errors
def stock_transaction_api(request):
    data = payload(request)
    qty = int(data.get("quantity", 0))
    if qty <= 0: return JsonResponse({"detail": "Jumlah harus lebih dari 0"}, status=400)
    with transaction.atomic():
        stock, _ = WarehouseStock.objects.select_for_update().get_or_create(
            product_id=data["product_id"], warehouse_id=data["warehouse_id"])
        ttype = data.get("type", "in")
        if ttype == "out" and stock.quantity < qty:
            return JsonResponse({"detail": "Stok tidak mencukupi", "available": stock.quantity}, status=400)
        if ttype == "in": stock.quantity += qty
        elif ttype == "out": stock.quantity -= qty
        elif ttype == "adjust": stock.quantity = qty
        stock.save(update_fields=["quantity"])
        tx = StockTransaction.objects.create(stock=stock, transaction_type=ttype, quantity=qty,
                                              balance_after=stock.quantity, note=data.get("note", ""),
                                              created_by=request.user)
        log_activity(request, f"stock_{ttype}", "stock", entity_id=stock.id,
                     detail=f"{stock.product.name} qty={qty}")
        if stock.quantity < stock.product.minimum_stock:
            for admin in User.objects.filter(is_superuser=True):
                notify(admin, "Stok rendah",
                        f"{stock.product.name} di {stock.warehouse.name} tersisa {stock.quantity}", "warning")
    return JsonResponse({"stock_id": stock.id, "quantity": stock.quantity, "transaction_id": tx.id})


@auth_required
def stock_transactions_api(request):
    qs = StockTransaction.objects.select_related("stock__product", "stock__warehouse", "created_by").order_by("-created_at")[:200]
    items = [{"id": t.id, "type": t.transaction_type, "quantity": t.quantity,
               "balance_after": t.balance_after, "note": t.note,
               "product": t.stock.product.name, "sku": t.stock.product.sku,
               "warehouse": t.stock.warehouse.name, "user": t.created_by.username,
               "created_at": t.created_at.strftime("%d %b %Y %H:%M")}
              for t in qs]
    return JsonResponse({"items": items})


# ---------- RECIPIENTS ----------
@csrf_exempt
@auth_required
@catch_errors
def recipients_api(request):
    if request.method == "GET":
        return JsonResponse({"items": list(Recipient.objects.filter(active=True).values(
            "id", "code", "name", "phone", "email", "address", "city", "province", "active"))})
    if not is_admin(request.user): return JsonResponse({"detail": "Akses Admin diperlukan"}, status=403)
    if request.method == "POST":
        data = payload(request)
        r = Recipient.objects.create(code=data["code"], name=data["name"], phone=data.get("phone", ""),
                                      email=data.get("email", ""), address=data.get("address", ""),
                                      city=data.get("city", ""), province=data.get("province", ""),
                                      active=data.get("active", True))
        log_activity(request, "create", "recipient", entity_id=r.id, detail=r.name)
        return JsonResponse({"id": r.id, "name": r.name}, status=201)
    return JsonResponse({"detail": "Method tidak didukung"}, status=405)


@csrf_exempt
@admin_required
@catch_errors
def recipient_detail_api(request, pk):
    r = Recipient.objects.get(pk=pk)
    if request.method == "PUT":
        data = payload(request)
        for f in ["code", "name", "phone", "email", "address", "city", "province"]:
            if f in data: setattr(r, f, data[f])
        if "active" in data: r.active = data["active"]
        r.save()
        log_activity(request, "update", "recipient", entity_id=r.id, detail=r.name)
        return JsonResponse({"id": r.id, "name": r.name})
    if request.method == "DELETE":
        r.active = False; r.save()
        log_activity(request, "deactivate", "recipient", entity_id=r.id)
        return JsonResponse({"message": "Penerima dinonaktifkan"})
    return JsonResponse({"detail": "Method tidak didukung"}, status=405)


# ---------- VEHICLES ----------
@csrf_exempt
@auth_required
@catch_errors
def vehicles_api(request):
    if request.method == "GET":
        return JsonResponse({"items": list(Vehicle.objects.values(
            "id", "plate_number", "vehicle_type", "brand", "capacity", "status", "note"))})
    if not is_admin(request.user): return JsonResponse({"detail": "Akses Admin diperlukan"}, status=403)
    if request.method == "POST":
        data = payload(request)
        v = Vehicle.objects.create(plate_number=data["plate_number"], vehicle_type=data.get("vehicle_type", ""),
                                    brand=data.get("brand", ""), capacity=data.get("capacity", ""),
                                    status=data.get("status", "available"), note=data.get("note", ""))
        log_activity(request, "create", "vehicle", entity_id=v.id, detail=v.plate_number)
        return JsonResponse({"id": v.id, "plate_number": v.plate_number}, status=201)
    return JsonResponse({"detail": "Method tidak didukung"}, status=405)


@csrf_exempt
@admin_required
@catch_errors
def vehicle_detail_api(request, pk):
    v = Vehicle.objects.get(pk=pk)
    if request.method == "PUT":
        data = payload(request)
        for f in ["plate_number", "vehicle_type", "brand", "capacity", "status", "note"]:
            if f in data: setattr(v, f, data[f])
        v.save()
        log_activity(request, "update", "vehicle", entity_id=v.id, detail=v.plate_number)
        return JsonResponse({"id": v.id, "plate_number": v.plate_number})
    if request.method == "DELETE":
        v.delete()
        log_activity(request, "delete", "vehicle", entity_id=pk)
        return JsonResponse({"message": "Kendaraan dihapus"})
    return JsonResponse({"detail": "Method tidak didukung"}, status=405)


# ---------- USERS (Admin) ----------
@csrf_exempt
@admin_required
@catch_errors
def users_api(request):
    if request.method == "GET":
        users = User.objects.select_related("profile").all()
        return JsonResponse({"items": [user_data(u) | {"is_active": u.is_active,
                                                         "date_joined": u.date_joined.strftime("%d %b %Y")}
                                        for u in users]})
    if request.method == "POST":
        data = payload(request)
        email = data["email"].strip().lower()
        if User.objects.filter(username=email).exists():
            return JsonResponse({"detail": "Email sudah terdaftar"}, status=400)
        user = User.objects.create_user(username=email, email=email, password=data["password"],
                                         first_name=data.get("full_name", ""))
        Profile.objects.create(user=user, role=data.get("role", "user"), full_name=data.get("full_name", ""),
                               phone=data.get("phone", ""),
                               avatar_initials="".join(p[0] for p in (data.get("full_name") or email).split()[:2]).upper() or email[:2].upper())
        if data.get("role") == "admin": user.is_staff = True; user.save()
        log_activity(request, "create", "user", entity_id=user.id, detail=email)
        return JsonResponse(user_data(user), status=201)
    return JsonResponse({"detail": "Method tidak didukung"}, status=405)


# ---------- REQUESTS ----------
def request_json(r):
    items = [{"product_id": i.product_id, "product_sku": i.product.sku, "product_name": i.product.name,
              "quantity": i.quantity, "unit": i.product.unit} for i in r.items.select_related("product").all()]
    dist = getattr(r, "distribution", None)
    return {"id": r.id, "number": r.number, "requester": r.requester.username,
            "requester_name": (r.requester.profile.full_name if hasattr(r.requester, "profile") else r.requester.username),
            "warehouse_id": r.warehouse_id, "warehouse_name": r.warehouse.name,
            "recipient_id": r.recipient_id, "recipient_name": r.recipient.name,
            "destination": r.destination, "needed_date": r.needed_date.isoformat() if r.needed_date else "",
            "note": r.note, "status": r.status, "rejection_reason": r.rejection_reason,
            "items": items, "total_quantity": sum(i["quantity"] for i in items),
            "distribution_number": dist.number if dist else None,
            "created_at": r.created_at.strftime("%d %b %Y %H:%M")}


@csrf_exempt
@auth_required
@catch_errors
def requests_api(request):
    if request.method == "GET":
        qs = ItemRequest.objects.select_related("requester", "warehouse", "recipient").prefetch_related("items__product", "distribution")
        if not is_admin(request.user): qs = qs.filter(requester=request.user)
        status = request.GET.get("status")
        if status: qs = qs.filter(status=status)
        q = request.GET.get("q", "").strip()
        if q: qs = qs.filter(Q(number__icontains=q) | Q(destination__icontains=q))
        return JsonResponse({"items": [request_json(r) for r in qs.order_by("-created_at")]})
    if request.method == "POST":
        data = payload(request)
        if not data.get("items"): return JsonResponse({"detail": "Minimal satu barang"}, status=400)
        try:
            with transaction.atomic():
                number = next_number(ItemRequest, "REQ", timezone.now().year)
                req = ItemRequest.objects.create(number=number, requester=request.user,
                                                  warehouse_id=data["warehouse_id"],
                                                  recipient_id=data["recipient_id"],
                                                  destination=data["destination"],
                                                  needed_date=parse_date(data.get("needed_date")),
                                                  note=data.get("note", ""))
                for it in data["items"]:
                    RequestItem.objects.create(request=req, product_id=it["product_id"], quantity=it["quantity"])
                notify(request.user, "Permintaan dibuat", f"{number} berhasil dibuat", "success", f"/permintaan/{req.id}")
                notify_admins("Permintaan baru", f"{request.user.username} membuat {number}", "info", f"/permintaan/{req.id}")
                log_activity(request, "create", "request", entity_id=req.id, detail=number)
        except (KeyError, Warehouse.DoesNotExist, Recipient.DoesNotExist, Product.DoesNotExist) as e:
            return JsonResponse({"detail": f"Data tidak lengkap atau tidak valid: {e}"}, status=400)
        except IntegrityError:
            return JsonResponse({"detail": "Nomor permintaan bentrok, coba lagi"}, status=409)
        return JsonResponse(request_json(req), status=201)
    return JsonResponse({"detail": "Method tidak didukung"}, status=405)


@auth_required
@catch_errors
def request_detail_api(request, pk):
    r = ItemRequest.objects.select_related("requester", "warehouse", "recipient").prefetch_related("items__product", "distribution__history").get(pk=pk)
    if not is_admin(request.user) and r.requester_id != request.user.id:
        return JsonResponse({"detail": "Akses ditolak"}, status=403)
    data = request_json(r)
    # timeline
    timeline = [{"label": "Permintaan dibuat", "status": "done", "at": r.created_at.strftime("%d %b %Y %H:%M")}]
    labels = {"pending": "Menunggu review", "approved": "Disetujui", "prepared": "Disiapkan",
              "shipped": "Dikirim", "in_transit": "Dalam perjalanan", "arrived": "Tiba", "completed": "Selesai",
              "rejected": "Ditolak"}
    order = ["pending", "approved", "prepared", "shipped", "in_transit", "arrived", "completed"]
    if r.status == "rejected":
        timeline.append({"label": labels["rejected"], "status": "done", "at": ""})
    else:
        current_idx = order.index(r.status) if r.status in order else 0
        for i, s in enumerate(order[1:], 1):
            timeline.append({"label": labels[s], "status": "done" if i <= current_idx else "pending", "at": ""})
    dist = getattr(r, "distribution", None)
    if dist:
        for h in dist.history.all():
            timeline.append({"label": f"[Distribusi] {labels.get(h.status, h.status)}",
                              "status": "done", "at": h.created_at.strftime("%d %b %Y %H:%M"),
                              "note": h.note})
    data["timeline"] = timeline
    return JsonResponse(data)


@csrf_exempt
@admin_required
@require_http_methods(["POST"])
@catch_errors
def request_action_api(request, pk):
    data = payload(request)
    action = data.get("action")
    req = ItemRequest.objects.prefetch_related("items__product").get(pk=pk)
    with transaction.atomic():
        if action == "approve":
            if req.status not in ["pending", "processed"]:
                return JsonResponse({"detail": "Status tidak dapat diubah"}, status=400)
            for item in req.items.all():
                stock, _ = WarehouseStock.objects.select_for_update().get_or_create(
                    product=item.product, warehouse=req.warehouse)
                if stock.quantity < item.quantity:
                    return JsonResponse({"detail": f"Stok {item.product.name} tidak cukup",
                                          "available": stock.quantity}, status=400)
            for item in req.items.all():
                stock = WarehouseStock.objects.select_for_update().get(product=item.product, warehouse=req.warehouse)
                stock.quantity -= item.quantity
                stock.save(update_fields=["quantity"])
                StockTransaction.objects.create(stock=stock, transaction_type="out", quantity=item.quantity,
                                                 balance_after=stock.quantity,
                                                 note=f"Approval {req.number}", created_by=request.user)
            req.status = "approved"; req.approved_by = request.user; req.approved_at = timezone.now()
            req.save(update_fields=["status", "approved_by", "approved_at"])
            notify(req.requester, "Permintaan disetujui", f"{req.number} telah disetujui.", "success", f"/permintaan/{req.id}")
            log_activity(request, "approve", "request", entity_id=req.id, detail=req.number)
            message = "Permintaan disetujui"
        elif action == "process":
            req.status = "processed"; req.save(update_fields=["status"])
            notify(req.requester, "Permintaan diproses", f"{req.number} sedang diproses.", "info")
            log_activity(request, "process", "request", entity_id=req.id, detail=req.number)
            message = "Permintaan diproses"
        elif action == "reject":
            req.status = "rejected"; req.rejection_reason = data.get("reason", "Tidak disetujui")
            req.save(update_fields=["status", "rejection_reason"])
            notify(req.requester, "Permintaan ditolak", f"{req.number}: {req.rejection_reason}", "danger")
            log_activity(request, "reject", "request", entity_id=req.id, detail=req.number)
            message = "Permintaan ditolak"
        else:
            return JsonResponse({"detail": "Action harus approve/process/reject"}, status=400)
    return JsonResponse({"number": req.number, "status": req.status, "message": message})


# ---------- DISTRIBUTIONS ----------
def distribution_json(d):
    return {"id": d.id, "number": d.number, "request_number": d.request.number,
            "request_id": d.request_id, "requester": d.request.requester.username,
            "warehouse_name": d.warehouse.name, "destination": d.destination,
            "recipient_name": d.request.recipient.name,
            "vehicle_id": d.vehicle_id, "vehicle_plate": d.vehicle.plate_number if d.vehicle else "",
            "delivery_number": d.delivery_number, "status": d.status,
            "estimated_arrival": d.estimated_arrival.isoformat() if d.estimated_arrival else "",
            "shipped_at": d.shipped_at.strftime("%d %b %Y %H:%M") if d.shipped_at else "",
            "completed_at": d.completed_at.strftime("%d %b %Y %H:%M") if d.completed_at else "",
            "arrival_photo": d.arrival_photo or "",
            "note": d.note, "created_at": d.created_at.strftime("%d %b %Y %H:%M"),
            "items": [{"name": i.product.name, "sku": i.product.sku, "quantity": i.quantity, "unit": i.product.unit}
                      for i in d.request.items.select_related("product").all()],
            "history": [{"status": h.status, "note": h.note, "user": h.changed_by.username,
                          "created_at": h.created_at.strftime("%d %b %Y %H:%M")}
                         for h in d.history.order_by("created_at")]}


@csrf_exempt
@auth_required
@catch_errors
def distributions_api(request):
    if request.method == "GET":
        qs = Distribution.objects.select_related("request__requester", "request__recipient", "warehouse", "vehicle").prefetch_related("history", "request__items__product")
        if not is_admin(request.user): qs = qs.filter(request__requester=request.user)
        status = request.GET.get("status")
        if status: qs = qs.filter(status=status)
        return JsonResponse({"items": [distribution_json(d) for d in qs.order_by("-created_at")]})
    if not is_admin(request.user): return JsonResponse({"detail": "Akses Admin diperlukan"}, status=403)
    data = payload(request)
    req = get_or_404(ItemRequest.objects.select_related("warehouse", "recipient"), pk=data.get("request_id"))
    if not req: return JsonResponse({"detail": "Permintaan tidak ditemukan"}, status=404)
    if req.status != "approved":
        return JsonResponse({"detail": "Permintaan harus disetujui dulu"}, status=400)
    if hasattr(req, "distribution"):
        return JsonResponse({"detail": "Distribusi sudah dibuat"}, status=400)
    try:
        with transaction.atomic():
            number = next_number(Distribution, "DST", timezone.now().year)
            d = Distribution.objects.create(number=number, request=req, warehouse=req.warehouse,
                                             destination=req.destination,
                                             vehicle_id=data.get("vehicle_id") or None,
                                             delivery_number=data.get("delivery_number", ""),
                                             estimated_arrival=parse_date(data.get("estimated_arrival")),
                                             note=data.get("note", ""), created_by=request.user)
            DistributionStatusHistory.objects.create(distribution=d, status="prepared",
                                                      changed_by=request.user, note="Distribusi dibuat")
            req.status = "prepared"; req.save(update_fields=["status"])
            if d.vehicle:
                d.vehicle.status = "in_use"; d.vehicle.save(update_fields=["status"])
            notify(req.requester, "Barang disiapkan", f"{number} dibuat dari {req.number}", "info",
                    f"/distribusi/{d.id}")
            log_activity(request, "create", "distribution", entity_id=d.id, detail=number)
    except IntegrityError:
        return JsonResponse({"detail": "Nomor distribusi bentrok, coba lagi"}, status=409)
    return JsonResponse(distribution_json(d), status=201)


@auth_required
@catch_errors
def distribution_detail_api(request, pk):
    d = Distribution.objects.select_related("request__requester", "request__recipient", "warehouse", "vehicle").prefetch_related("history", "request__items__product").get(pk=pk)
    if not is_admin(request.user) and d.request.requester_id != request.user.id:
        return JsonResponse({"detail": "Akses ditolak"}, status=403)
    return JsonResponse(distribution_json(d))


@csrf_exempt
@admin_required
@require_http_methods(["POST"])
@catch_errors
def distribution_status_api(request, pk):
    data = payload(request)
    d = Distribution.objects.select_related("request__requester", "vehicle").get(pk=pk)
    new_status = data.get("status", "")
    order = ["prepared", "in_transit", "arrived", "completed"]
    if new_status not in order:
        return JsonResponse({"detail": "Status tidak valid"}, status=400)
    if order.index(new_status) < order.index(d.status):
        return JsonResponse({"detail": "Tidak dapat mundur ke status sebelumnya"}, status=400)
    label_map = {"prepared": "Disiapkan", "in_transit": "Dalam perjalanan",
                 "arrived": "Tiba di lokasi", "completed": "Distribusi selesai"}
    with transaction.atomic():
        d.status = new_status
        if new_status == "in_transit" and not d.shipped_at: d.shipped_at = timezone.now()
        if new_status == "arrived" and data.get("photo"):
            d.arrival_photo = data["photo"]
        if new_status == "completed":
            d.completed_at = timezone.now()
            if d.vehicle:
                d.vehicle.status = "available"; d.vehicle.save(update_fields=["status"])
        d.save()
        DistributionStatusHistory.objects.create(distribution=d, status=new_status,
                                                  changed_by=request.user, note=data.get("note", ""))
        req = d.request
        req.status = {"in_transit": "shipped", "arrived": "arrived", "completed": "completed",
                       "prepared": "prepared"}.get(new_status, req.status)
        req.save(update_fields=["status"])
        notify(req.requester, label_map.get(new_status, new_status),
                f"{d.number}: {label_map.get(new_status, new_status)}", "info", f"/distribusi/{d.id}")
        log_activity(request, "update_status", "distribution", entity_id=d.id,
                     detail=f"{d.number}: {new_status}")
    return JsonResponse({"number": d.number, "status": d.status})


# ---------- TRACKING ----------
@auth_required
def tracking_api(request):
    qs = Distribution.objects.select_related("request__requester", "warehouse").prefetch_related("history")
    if not is_admin(request.user): qs = qs.filter(request__requester=request.user)
    items = []
    for d in qs.exclude(status="completed").order_by("-created_at")[:20]:
        progress = {"prepared": 25, "in_transit": 60, "arrived": 90, "completed": 100}.get(d.status, 10)
        items.append({"id": d.id, "number": d.number, "request_number": d.request.number,
                       "origin": d.warehouse.name, "destination": d.destination,
                       "status": d.status, "progress": progress,
                       "items_summary": ", ".join(f"{i.product.name} ({i.quantity} {i.product.unit})"
                                                    for i in d.request.items.select_related("product").all()[:2])})
    return JsonResponse({"items": items})


# ---------- NOTIFICATIONS ----------
@csrf_exempt
@auth_required
@catch_errors
def notifications_api(request):
    if request.method == "GET":
        qs = request.user.notifications.order_by("-created_at")[:50]
        return JsonResponse({"items": [{"id": n.id, "title": n.title, "message": n.message,
                                          "kind": n.kind, "read": n.read, "link": n.link,
                                          "created_at": n.created_at.strftime("%d %b %Y %H:%M")}
                                         for n in qs],
                             "unread": request.user.notifications.filter(read=False).count()})
    if request.method == "POST":
        data = payload(request)
        if data.get("mark_all"):
            request.user.notifications.filter(read=False).update(read=True)
            return JsonResponse({"message": "Semua notifikasi ditandai dibaca"})
        Notification.objects.filter(pk=data["id"], user=request.user).update(read=True)
        return JsonResponse({"message": "Ditandai dibaca"})
    return JsonResponse({"detail": "Method tidak didukung"}, status=405)


# ---------- ACTIVITY LOG ----------
@admin_required
def activity_log_api(request):
    qs = ActivityLog.objects.select_related("user").order_by("-created_at")[:200]
    items = [{"id": a.id, "user": a.user.username if a.user else "Sistem",
               "action": a.action, "entity": a.entity, "entity_id": a.entity_id,
               "detail": a.detail, "ip_address": a.ip_address or "-",
               "created_at": a.created_at.strftime("%d %b %Y %H:%M")}
              for a in qs]
    return JsonResponse({"items": items})


# ---------- REPORTS ----------
@admin_required
@catch_errors
def reports_summary_api(request):
    start = request.GET.get("start"); end = request.GET.get("end")
    req_qs = ItemRequest.objects.all()
    dist_qs = Distribution.objects.all()
    tx_qs = StockTransaction.objects.all()
    if start:
        req_qs = req_qs.filter(created_at__date__gte=start)
        dist_qs = dist_qs.filter(created_at__date__gte=start)
        tx_qs = tx_qs.filter(created_at__date__gte=start)
    if end:
        req_qs = req_qs.filter(created_at__date__lte=end)
        dist_qs = dist_qs.filter(created_at__date__lte=end)
        tx_qs = tx_qs.filter(created_at__date__lte=end)
    top = (RequestItem.objects.filter(request__in=req_qs)
           .values("product__sku", "product__name").annotate(total=Sum("quantity")).order_by("-total")[:10])
    return JsonResponse({
        "requests_total": req_qs.count(),
        "requests_approved": req_qs.filter(status="approved").count(),
        "requests_rejected": req_qs.filter(status="rejected").count(),
        "distributions_total": dist_qs.count(),
        "distributions_completed": dist_qs.filter(status="completed").count(),
        "stock_in": sum(t.quantity for t in tx_qs.filter(transaction_type="in")),
        "stock_out": sum(t.quantity for t in tx_qs.filter(transaction_type="out")),
        "top_products": [{"sku": t["product__sku"], "name": t["product__name"], "total": t["total"]} for t in top],
    })


def _dataset(kind, ids=None):
    """Return (title, rows). ids: optional iterable of primary keys to filter (None = all, [] = none)."""
    def apply_ids(qs):
        return qs.filter(id__in=ids) if ids is not None else qs
    if kind == "stock":
        rows = [["Gudang", "SKU", "Nama Barang", "Kategori", "Stok", "Minimum"]]
        for s in apply_ids(WarehouseStock.objects.select_related("product__category", "warehouse")):
            rows.append([s.warehouse.name, s.product.sku, s.product.name, s.product.category.name,
                          s.quantity, s.product.minimum_stock])
        return "Laporan Stok", rows
    if kind == "requests":
        rows = [["Nomor", "Pemohon", "Gudang", "Tujuan", "Status", "Tanggal"]]
        for r in apply_ids(ItemRequest.objects.select_related("requester", "warehouse")):
            rows.append([r.number, r.requester.username, r.warehouse.name, r.destination,
                          r.status, r.created_at.strftime("%Y-%m-%d %H:%M")])
        return "Laporan Permintaan", rows
    if kind == "distributions":
        rows = [["Nomor", "Permintaan", "Gudang", "Tujuan", "Kendaraan", "Status", "Tanggal"]]
        for d in apply_ids(Distribution.objects.select_related("request", "warehouse", "vehicle")):
            rows.append([d.number, d.request.number, d.warehouse.name, d.destination,
                          d.vehicle.plate_number if d.vehicle else "-", d.status,
                          d.created_at.strftime("%Y-%m-%d %H:%M")])
        return "Laporan Distribusi", rows
    if kind == "stock_transactions":
        rows = [["Tanggal", "Tipe", "SKU", "Barang", "Gudang", "Jumlah", "Saldo", "User", "Catatan"]]
        for t in apply_ids(StockTransaction.objects.select_related("stock__product", "stock__warehouse", "created_by")):
            rows.append([t.created_at.strftime("%Y-%m-%d %H:%M"), t.transaction_type,
                          t.stock.product.sku, t.stock.product.name, t.stock.warehouse.name,
                          t.quantity, t.balance_after, t.created_by.username, t.note])
        return "Laporan Transaksi Stok", rows
    return "Laporan", [["Data"]]


@admin_required
@catch_errors
def report_export_api(request, kind, fmt):
    ids_param = request.GET.get("ids")
    if ids_param is None:
        ids = None
    else:
        ids = [int(x) for x in ids_param.split(",") if x.strip().isdigit()]
    title, rows = _dataset(kind, ids=ids)
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf); w.writerows(rows)
        resp = HttpResponse(buf.getvalue(), content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="{kind}.csv"'
        return resp
    if fmt == "excel":
        import openpyxl
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = title[:30]
        for r in rows: ws.append(r)
        buf = io.BytesIO(); wb.save(buf); buf.seek(0)
        resp = HttpResponse(buf.read(),
                            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        resp["Content-Disposition"] = f'attachment; filename="{kind}.xlsx"'
        return resp
    if fmt == "pdf":
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=landscape(A4))
        styles = getSampleStyleSheet(); story = [Paragraph(f"<b>{title}</b>", styles["Title"]),
                                                    Paragraph(datetime.now().strftime("Dicetak %d %B %Y %H:%M"),
                                                              styles["Normal"]),
                                                    Spacer(1, 12)]
        t = Table([[str(c) for c in row] for row in rows], repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                                ("FONTSIZE", (0, 0), (-1, -1), 8),
                                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                                 [colors.white, colors.HexColor("#F8FAFC")])]))
        story.append(t); doc.build(story); buf.seek(0)
        resp = HttpResponse(buf.read(), content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="{kind}.pdf"'
        return resp
    return JsonResponse({"detail": "Format tidak didukung"}, status=400)


# ---------- ROOT ----------
def root_api(request):
    return JsonResponse({"service": "LogistiPro API", "status": "ok", "version": "1.0.0"})
