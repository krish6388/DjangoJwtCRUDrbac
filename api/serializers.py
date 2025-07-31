from rest_framework import serializers
from .models import User, Category, Product, Order
from django.contrib.auth.password_validation import validate_password


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'role')

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    is_expensive = serializers.ReadOnlyField()
    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ['uploaded_by', 'is_expensive']

    def validate_video(self, value):
        max_size = 20 * 1024 * 1024  # 20 MB in bytes
        if value.size > max_size:
            raise serializers.ValidationError("Video size must be less than or equal to 20 MB.")
        return value

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = '__all__'

