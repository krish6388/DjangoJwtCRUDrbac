import threading
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from .models import Product, Order, Category
from .serializers import UserSerializer, ProductSerializer, OrderSerializer, CategorySerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import PermissionDenied
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
import pandas as pd
import io
import random
from faker import Faker

def generate_template_view(request):
    return render(request, 'generate_form.html')

# api/register/ -> Register a new user, role: Agent(default)
class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.is_active = False
            user.save()

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            activation_link = f"http://localhost:8080/api/activate/{uid}/{token}/"
            print(activation_link)

            # send_mail(
            #     "Activate your account",
            #     f"Click the link to activate: {activation_link}",
            #     "noreply@yourdomain.com",
            #     [user.email],
            # )

            return Response({"message": "Registration successful. Please check your email to activate your account."})
            # return Response({"message": "User created successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# Activate the user if clicked on the activation link in logs (Mails can be used in prod env)
class ActivateUserView(APIView):
    def get(self, request, uidb64, token):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = get_user_model().objects.get(pk=uid)
        except Exception:
            return Response({"error": "Invalid activation link"}, status=400)

        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            # Token.objects.create(user=user)
            return Response({"message": "Account activated successfully!"})
        else:
            return Response({"error": "Activation link expired or invalid"}, status=400)

# api/login/ -> Logs in a registered user -> Give access token and refresh token
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)

        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'role': user.role
            }, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    
# class LogoutView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def post(self, request):
#         # Delete the token to force re-authentication
#         request.user.auth_token.delete()
#         return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)

# api/product -> Read and Create in Product model -> JWT Auth -> Any role can access
class ProductListCreateView(generics.ListCreateAPIView):
    
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        print(self.request.user.role)
        if self.request.user.role not in ['admin', 'staff']:
            raise PermissionDenied("Only Admin and Staff can upload products.")
        serializer.save(uploaded_by=self.request.user)

# api/product/{id} -> PUT/PATCH/DELETE in Product model -> JWT Auth -> Admin and Staff can access
class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            if request.user.role.lower() not in ['admin', 'staff']:
                raise PermissionDenied("Only Admin or Staff can update or delete a product.")

# api/categories -> Read and Create in Category model -> JWT Auth -> Any role can access read | Only Admin for Create
class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        print(self.request.user.role)
        if self.request.user.role not in ['admin']:
            raise PermissionDenied("Only admin can upload categories.")
        serializer.save()  

# api/categories/{id} -> PUT/PATCH/DELETE in Category model -> JWT Auth -> Only Admin can access
class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            if request.user.role.lower() not in ['admin']:
                raise PermissionDenied("Only Admin can update or delete a category.")

# api/order -> Read(Only own orders if not admin) and Create new Order -> JWT Auth -> Admin can access all rows of Order 
class OrderListCreateView(generics.ListCreateAPIView):
    # queryset = Order.objects.filter(
    #     user = 1
    # )
    # queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role != 'admin':
            return Order.objects.filter(user=self.request.user)
        else:
            return Order.objects.all()

    def perform_create(self, serializer):
        if self.request.user.role != 'agent':
            raise PermissionDenied("Only agents/buyers can place orders.")
        serializer.save(user=self.request.user)


# /generate -> Generate 'count'/1000(default) new rows in Product model -> JWT -> Only Admin can access
class GenerateDummyProductsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role != 'admin':
            raise PermissionDenied("Only admin can upload dummy products.")

        count = int(request.data.get("count", 1000))
        user = request.user  # Store reference since request will not be available in thread

        thread = threading.Thread(target=self.generate_products, args=(user, count))
        thread.start()

        return Response({"message": f"Started background task to create {count} dummy products."}, status=status.HTTP_202_ACCEPTED)

    def generate_products(self, user, count):
        fake = Faker()

        categories = list(Category.objects.all())
        if not categories:
            categories = [Category.objects.create(name=fake.word()) for _ in range(5)]

        products = []
        for _ in range(count):
            products.append(Product(
                category=random.choice(categories),
                title=fake.catch_phrase(),
                description=fake.text(),
                price=round(random.uniform(1000, 50000), 2),
                uploaded_by=user
            ))
        Product.objects.bulk_create(products)

# /export -> Give a link to download excel sheet of all rows in Product model
def export_products_excel(request):
    products = Product.objects.select_related('category').all()
    df = pd.DataFrame([
        {
            "ID": p.id,
            "Title": p.title,
            "Category": p.category.name,
            "Description": p.description,
            "Price": p.price,
            "Uploaded By": p.uploaded_by.username,
            "Status": p.status,
        }
        for p in products
    ])
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=products.xlsx'
    return response
