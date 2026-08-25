from django.contrib import admin
from .models import (Category, Distribution, DistributionStatusHistory, ItemRequest, Notification, Product, Profile,
                     Recipient, RequestItem, StockTransaction, Warehouse, WarehouseStock)

for model in [Profile, Category, Product, Warehouse, WarehouseStock, StockTransaction, Recipient, ItemRequest, RequestItem, Distribution, DistributionStatusHistory, Notification]:
    admin.site.register(model)