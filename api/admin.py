from django.contrib import admin
from .models import Product, Category, Order, User

# Register your models here.
admin.site.register(Product)
admin.site.register(Category)
admin.site.register(Order)
admin.site.register(User)
