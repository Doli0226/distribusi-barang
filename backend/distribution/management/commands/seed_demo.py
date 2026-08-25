"""Seed demo data untuk LogistiPro Indonesia."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from distribution.models import (Category, Distribution, DistributionStatusHistory, ItemRequest, Notification,
                                  Product, Profile, Recipient, RequestItem, StockTransaction, Vehicle,
                                  Warehouse, WarehouseStock)


def upsert_user(email, password, full_name, role):
    user, created = User.objects.get_or_create(username=email, defaults={"email": email})
    user.email = email
    user.first_name = full_name
    if role == "admin":
        user.is_staff = True; user.is_superuser = True
    user.set_password(password); user.save()
    initials = "".join(p[0] for p in full_name.split()[:2]).upper() or email[:2].upper()
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.role = role; profile.full_name = full_name; profile.avatar_initials = initials
    profile.save()
    return user


class Command(BaseCommand):
    help = "Seed demo data"

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Seeding LogistiPro demo data...")

        # Users
        admin = upsert_user("admin@logistipro.id", "admin123", "Adi Rahman", "admin")
        user = upsert_user("user@logistipro.id", "user123", "Siti Rahma", "user")
        upsert_user("budi@logistipro.id", "user123", "Budi Santoso", "user")

        # Categories
        cats = {}
        for name, desc in [("Elektronik", "Peralatan & aksesori elektronik"),
                            ("ATK & Furnitur", "Alat tulis dan perabotan kantor"),
                            ("Kemasan", "Kardus, plastik & bahan kemasan"),
                            ("APD", "Alat pelindung diri")]:
            cats[name] = Category.objects.get_or_create(name=name, defaults={"description": desc})[0]

        # Warehouses
        whs = {}
        for code, name, loc, city, cap in [
            ("WH-JKT", "Gudang Pusat Jakarta", "Jl. Cakung Cilincing No. 12", "Jakarta", 5000),
            ("WH-BDG", "Gudang Regional Bandung", "Jl. Soekarno Hatta No. 245", "Bandung", 3000),
            ("WH-SBY", "Gudang Timur Surabaya", "Jl. Rungkut Industri No. 8", "Surabaya", 3500),
        ]:
            whs[code] = Warehouse.objects.get_or_create(code=code,
                defaults={"name": name, "location": loc, "city": city, "capacity": cap})[0]

        # Products
        products = []
        for sku, name, cat, unit, minstock in [
            ("SKU-EL-001", "Kabel LAN Cat6 305m", "Elektronik", "roll", 20),
            ("SKU-EL-002", "Router WiFi 6", "Elektronik", "unit", 15),
            ("SKU-EL-003", "Adaptor Power 12V", "Elektronik", "unit", 30),
            ("SKU-AT-014", "Kursi Lipat Premium", "ATK & Furnitur", "unit", 40),
            ("SKU-AT-015", "Meja Lipat Portabel", "ATK & Furnitur", "unit", 25),
            ("SKU-KB-008", "Kardus Pengiriman M", "Kemasan", "pcs", 300),
            ("SKU-KB-009", "Plastik Bubble Wrap 50m", "Kemasan", "roll", 40),
            ("SKU-AP-021", "Hand Sanitizer 500ml", "APD", "botol", 80),
            ("SKU-AP-022", "Masker Medis 3-Ply", "APD", "box", 50),
        ]:
            p = Product.objects.get_or_create(sku=sku, defaults={
                "name": name, "category": cats[cat], "unit": unit,
                "minimum_stock": minstock, "description": name + " - kualitas terbaik"})[0]
            products.append(p)

        # Stocks
        stocks_qty = {"SKU-EL-001": {"WH-JKT": 120, "WH-BDG": 40},
                       "SKU-EL-002": {"WH-JKT": 60, "WH-SBY": 30},
                       "SKU-EL-003": {"WH-JKT": 15, "WH-BDG": 10},  # low
                       "SKU-AT-014": {"WH-JKT": 32, "WH-BDG": 20},  # low
                       "SKU-AT-015": {"WH-SBY": 45},
                       "SKU-KB-008": {"WH-JKT": 680, "WH-SBY": 200},
                       "SKU-KB-009": {"WH-JKT": 55, "WH-BDG": 20},
                       "SKU-AP-021": {"WH-JKT": 42, "WH-SBY": 18},  # low
                       "SKU-AP-022": {"WH-JKT": 120, "WH-BDG": 60}}
        for sku, warehouses in stocks_qty.items():
            p = Product.objects.get(sku=sku)
            for wcode, qty in warehouses.items():
                stock, created = WarehouseStock.objects.get_or_create(
                    product=p, warehouse=whs[wcode], defaults={"quantity": qty})
                if not created and stock.quantity == 0:
                    stock.quantity = qty; stock.save()
                if created:
                    StockTransaction.objects.create(stock=stock, transaction_type="in", quantity=qty,
                                                    balance_after=stock.quantity,
                                                    note="Stok awal", created_by=admin)

        # Recipients
        recipients = []
        for code, name, city, prov in [
            ("PNR-001", "PT Nusantara Elektrindo", "Bandung", "Jawa Barat"),
            ("PNR-002", "CV Sinar Kemasan", "Surabaya", "Jawa Timur"),
            ("PNR-003", "Puskesmas Kelapa Gading", "Jakarta", "DKI Jakarta"),
            ("PNR-004", "UMKM Berkah Jaya", "Semarang", "Jawa Tengah"),
        ]:
            r = Recipient.objects.get_or_create(code=code, defaults={
                "name": name, "phone": "+62812" + str(1000000 + len(recipients)),
                "email": f"{code.lower()}@partner.id",
                "address": f"Jl. Utama No. {len(recipients) + 10}", "city": city,
                "province": prov})[0]
            recipients.append(r)

        # Vehicles
        for plate, vtype, brand, cap, status in [
            ("B 1234 XYZ", "Truk Box", "Mitsubishi Colt Diesel", "3 Ton", "available"),
            ("B 5678 ABC", "Truk Engkel", "Isuzu Elf", "2 Ton", "in_use"),
            ("D 9012 DEF", "Pickup", "Suzuki Carry", "1 Ton", "available"),
            ("L 3456 GHI", "Van", "Daihatsu Gran Max", "700 Kg", "maintenance"),
        ]:
            Vehicle.objects.get_or_create(plate_number=plate, defaults={
                "vehicle_type": vtype, "brand": brand, "capacity": cap, "status": status})

        # Sample requests
        if ItemRequest.objects.count() == 0:
            now = timezone.now()
            samples = [
                {"requester": user, "wh": whs["WH-JKT"], "recipient": recipients[0], "days_ago": 2,
                 "status": "pending", "items": [("SKU-EL-001", 5)]},
                {"requester": user, "wh": whs["WH-JKT"], "recipient": recipients[2], "days_ago": 3,
                 "status": "approved", "items": [("SKU-AP-021", 10), ("SKU-AP-022", 5)]},
                {"requester": User.objects.get(username="budi@logistipro.id"), "wh": whs["WH-JKT"],
                 "recipient": recipients[1], "days_ago": 5, "status": "completed",
                 "items": [("SKU-KB-008", 100)]},
                {"requester": user, "wh": whs["WH-BDG"], "recipient": recipients[3], "days_ago": 7,
                 "status": "rejected", "items": [("SKU-AT-014", 50)]},
            ]
            for i, s in enumerate(samples, 1):
                r = ItemRequest.objects.create(
                    number=f"REQ-{now.year}-{i:04d}", requester=s["requester"],
                    warehouse=s["wh"], recipient=s["recipient"],
                    destination=f"{s['recipient'].address}, {s['recipient'].city}",
                    needed_date=(now + timedelta(days=5)).date(), status=s["status"],
                    created_at=now - timedelta(days=s["days_ago"]))
                r.created_at = now - timedelta(days=s["days_ago"])
                r.save(update_fields=["created_at"])
                for sku, qty in s["items"]:
                    RequestItem.objects.create(request=r, product=Product.objects.get(sku=sku), quantity=qty)
                if s["status"] == "rejected":
                    r.rejection_reason = "Stok tidak memadai untuk periode ini"; r.save()
                if s["status"] == "completed":
                    d = Distribution.objects.create(
                        number=f"DST-{now.year}-{i:04d}", request=r, warehouse=r.warehouse,
                        destination=r.destination, delivery_number=f"DLV-{i:04d}",
                        status="completed", shipped_at=now - timedelta(days=s["days_ago"] - 1),
                        completed_at=now - timedelta(days=s["days_ago"] - 2), created_by=admin,
                        vehicle=Vehicle.objects.first(),
                        estimated_arrival=(now - timedelta(days=s["days_ago"] - 2)).date())
                    for st in ["prepared", "in_transit", "arrived", "completed"]:
                        DistributionStatusHistory.objects.create(distribution=d, status=st,
                                                                  changed_by=admin, note=f"Status {st}")

        # Sample notifications
        if Notification.objects.count() == 0:
            for u in [admin, user]:
                Notification.objects.create(user=u, title="Selamat datang di LogistiPro",
                                             message="Sistem distribusi barang siap digunakan.", kind="info")
            Notification.objects.create(user=admin, title="Stok rendah",
                                         message="Beberapa barang berada di bawah stok minimum.", kind="warning")

        self.stdout.write(self.style.SUCCESS("Selesai. Kredensial: admin@logistipro.id/admin123, user@logistipro.id/user123"))
