from django.shortcuts import render
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils.text import slugify

from accounts.permissions import IsAdmin, IsBranchManager, IsAdminOrBranchManager
from branches.models import Branch
from .models import Category, Product, BranchProduct
# Create your views here.

# ======================================================
# CATEGORY VIEWS
# ======================================================


# ======================================================
# List categories
# ======================================================
@api_view(['GET'])
@permission_classes([AllowAny])
def ListCategories(request):
    categories = Category.objects.all().order_by('category_name')
    data = []
    for category in categories:
        data.append({
            'id': category.id,
            'category_name': category.category_name,
            'slug': category.slug,
            'image': request.build_absolute_uri(category.image.url) if category.image else None,
        })
    return Response(data, status = 200)



# ======================================================
# Create category
# ======================================================
@api_view(['POST'])
@permission_classes([IsAdmin])
def CreateCategory(request):
    category_name = request.data.get('category_name')
    image = request.FILES.get('image')

    if not category_name:
        return Response({'error': 'category_name is required'}, status = 400)

    slug = slugify(category_name)

    if Category.objects.filter(slug = slug).exists():
        return Response({'error': 'Category already exists'}, status = 400)

    category = Category.objects.create(
        category_name = category_name,
        slug = slug,
        image = image
    )

    return Response({
        'message': 'Category created successfully',
        'category': {
            'id': category.id,
            'category_name': category.category_name,
            'slug': category.slug,
            'image': request.build_absolute_uri(category.image.url) if category.image else None,
        }
    }, status = 201)



# ======================================================
# Update category
# ======================================================
@api_view(['PUT'])
@permission_classes([IsAdmin])
def UpdateCategory(request, category_id):
    try:
        category = Category.objects.get(id = category_id)
    except Category.DoesNotExist:
        return Response({'error': 'Category not found'}, status = 404)

    category_name = request.data.get('category_name', category.category_name)

    if category_name != category.category_name:
        new_slug = slugify(category_name)
        if Category.objects.filter(slug = new_slug).exclude(id=category_id).exists():
            return Response({'error': 'Category with this name already exists'}, status = 400)
        category.slug = new_slug

    category.category_name = category_name
    if 'image' in request.FILES:
        category.image = request.FILES['image']
    category.save()

    return Response({
        'message': 'Category updated successfully',
        'category': {
            'id': category.id,
            'category_name': category.category_name,
            'slug': category.slug,
            'image': request.build_absolute_uri(category.image.url) if category.image else None,
        }
    }, status = 200)



# ======================================================
# Delete category
# ======================================================
@api_view(['DELETE'])
@permission_classes([IsAdmin])
def DeleteCategory(request, category_id):
    try:
        category = Category.objects.get(id = category_id)
    except Category.DoesNotExist:
        return Response({'error': 'Category not found'}, status = 404)

    if category.products.exists():
        return Response({
            'error': 'Cannot delete category with existing products. Move or delete products first.'
        }, status = 400)

    category_name = category.category_name
    category.delete()
    return Response({'message': f'{category_name} deleted successfully'}, status = 200)


# ======================================================
# PRODUCT VIEWS
# ======================================================


# ======================================================
# List products
# ======================================================
@api_view(['GET'])
@permission_classes([AllowAny])
def ListProducts(request):
    queryset = Product.objects.filter(
        is_active = True
    ).select_related('category').order_by('product_name')

    category_id = request.query_params.get('category')
    if category_id:
        queryset = queryset.filter(category_id=category_id)

    search = request.query_params.get('search')
    if search:
        queryset = queryset.filter(product_name__icontains=search)

    data = []
    for product in queryset:
        data.append({
            'id': product.id,
            'product_name': product.product_name,
            'description': product.description,
            'category': product.category.category_name,
            'image': request.build_absolute_uri(product.image.url) if product.image else None,
            'is_active': product.is_active,
        })
    return Response(data, status=200)



# ======================================================
# Get product
# ======================================================
@api_view(['GET'])
@permission_classes([AllowAny])
def GetProduct(request, product_id):
    try:
        product = Product.objects.select_related('category').get(id = product_id)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status = 404)

    return Response({
        'id': product.id,
        'product_name': product.product_name,
        'description': product.description,
        'category': product.category.category_name,
        'image': request.build_absolute_uri(product.image.url) if product.image else None,
        'is_active': product.is_active,
        'created_at': product.created_at,
        'updated_at': product.updated_at,
    }, status = 200)



# ======================================================
# Create product
# ======================================================
@api_view(['POST'])
@permission_classes([IsAdmin])
def CreateProduct(request):
    product_name = request.data.get('product_name')
    description = request.data.get('description', '')
    category_id = request.data.get('category')
    image = request.FILES.get('image')

    if not product_name or not category_id:
        return Response({'error': 'product_name and category are required'}, status = 400)

    try:
        category = Category.objects.get(id = category_id)
    except Category.DoesNotExist:
        return Response({'error': 'Category not found'}, status = 404)

    if Product.objects.filter(product_name__iexact = product_name).exists():
        return Response({'error': 'Product with this name already exists'}, status = 400)

    product = Product.objects.create(
        product_name = product_name,
        description = description,
        category = category,
        image = image
    )

    return Response({
        'message': 'Product created successfully',
        'product': {
            'id': product.id,
            'product_name': product.product_name,
            'description': product.description,
            'category': product.category.category_name,
            'image': request.build_absolute_uri(product.image.url) if product.image else None,
        }
    }, status = 201)



# ======================================================
# Update product
# ======================================================
@api_view(['PUT'])
@permission_classes([IsAdmin])
def UpdateProduct(request, product_id):
    try:
        product = Product.objects.select_related('category').get(id = product_id)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status = 404)

    category_id = request.data.get('category')
    if category_id:
        try:
            product.category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            return Response({'error': 'Category not found'}, status = 404)

    new_name = request.data.get('product_name')
    if new_name and Product.objects.filter(
        product_name__iexact = new_name
    ).exclude(id = product_id).exists():
        return Response({'error': 'Product with this name already exists'}, status=400)

    product.product_name = request.data.get('product_name', product.product_name)
    product.description = request.data.get('description', product.description)
    product.is_active = request.data.get('is_active', product.is_active)
    if 'image' in request.FILES:
        product.image = request.FILES['image']
    product.save()

    return Response({
        'message': 'Product updated successfully',
        'product': {
            'id': product.id,
            'product_name': product.product_name,
            'description': product.description,
            'category': product.category.category_name,
            'image': request.build_absolute_uri(product.image.url) if product.image else None,
            'is_active': product.is_active,
        }
    }, status = 200)



# ======================================================
# Delete product
# ======================================================
@api_view(['DELETE'])
@permission_classes([IsAdmin])
def DeleteProduct(request, product_id):
    try:
        product = Product.objects.get(id = product_id)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status = 404)

    product_name = product.product_name
    product.delete()
    return Response({'message': f'{product_name} deleted successfully'}, status = 200)


# ======================================================
# BRANCH PRODUCT VIEWS
# ======================================================

# ======================================================
# List branch products
# ======================================================
@api_view(['GET'])
@permission_classes([AllowAny])
def ListBranchProducts(request, branch_id):
    queryset = BranchProduct.objects.filter(
        branch_id=branch_id,
        is_available = True,
        product__is_active = True
    ).select_related('product', 'product__category', 'branch').order_by('product__product_name')

    category_id = request.query_params.get('category')
    if category_id:
        queryset = queryset.filter(product__category_id = category_id)

    search = request.query_params.get('search')
    if search:
        queryset = queryset.filter(product__product_name__icontains = search)

    min_price = request.query_params.get('min_price')
    max_price = request.query_params.get('max_price')
    if min_price:
        queryset = queryset.filter(price__gte = min_price)
    if max_price:
        queryset = queryset.filter(price__lte = max_price)

    in_stock = request.query_params.get('in_stock')
    if in_stock == 'true':
        queryset = queryset.filter(stock_quantity__gt = 0)

    data = []
    for item in queryset:
        data.append({
            'id': item.id,
            'product_id': item.product.id,
            'product_name': item.product.product_name,
            'description': item.product.description,
            'category': item.product.category.category_name,
            'image': request.build_absolute_uri(item.product.image.url) if item.product.image else None,
            'price': str(item.price),
            'stock_quantity': item.stock_quantity,
            'is_available': item.is_available,
            'in_stock': item.in_stock,
        })
    return Response(data, status=200)



# ======================================================
# Add branch product
# ======================================================
@api_view(['POST'])
@permission_classes([IsAdminOrBranchManager])
def AddBranchProduct(request):
    product_id = request.data.get('product')
    price = request.data.get('price')
    stock_quantity = request.data.get('stock_quantity', 0)

    if not product_id or not price:
        return Response({'error': 'product and price are required'}, status = 400)

    # Determine branch
    if request.user.role == 'branch_manager':
        try:
            branch = request.user.managed_branch
        except Exception:
            return Response({'error': 'You are not assigned to any branch'}, status = 404)
    else:
        branch_id = request.data.get('branch')
        if not branch_id:
            return Response({'error': 'branch is required for admin'}, status = 400)
        try:
            branch = Branch.objects.get(id = branch_id)
        except Branch.DoesNotExist:
            return Response({'error': 'Branch not found'}, status = 404)

    try:
        product = Product.objects.get(id = product_id)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status = 404)

    if BranchProduct.objects.filter(branch = branch, product = product).exists():
        return Response({'error': 'Product already exists in this branch. Update it instead.'}, status = 400)

    branch_product = BranchProduct.objects.create(
        branch = branch,
        product = product,
        price = price,
        stock_quantity = stock_quantity
    )

    return Response({
        'message': 'Product added to branch successfully',
        'branch_product': {
            'id': branch_product.id,
            'product_name': branch_product.product.product_name,
            'branch_name': branch_product.branch.branch_name,
            'price': str(branch_product.price),
            'stock_quantity': branch_product.stock_quantity,
            'is_available': branch_product.is_available,
        }
    }, status = 201)



# ======================================================
# Update branch product
# ======================================================
@api_view(['PUT'])
@permission_classes([IsAdminOrBranchManager])
def UpdateBranchProduct(request, branch_product_id):
    try:
        branch_product = BranchProduct.objects.select_related(
            'product', 'branch'
        ).get(id = branch_product_id)
    except BranchProduct.DoesNotExist:
        return Response({'error': 'Branch product not found'}, status = 404)

    if request.user.role == 'branch_manager':
        try:
            branch = request.user.managed_branch
        except Exception:
            return Response({'error': 'You are not assigned to any branch'}, status = 404)
        if branch_product.branch != branch:
            return Response({'error': 'You can only update products in your own branch'}, status = 403)

    branch_product.price = request.data.get('price', branch_product.price)
    branch_product.stock_quantity = request.data.get('stock_quantity', branch_product.stock_quantity)
    branch_product.is_available = request.data.get('is_available', branch_product.is_available)
    branch_product.save()

    return Response({
        'message': 'Branch product updated successfully',
        'branch_product': {
            'id': branch_product.id,
            'product_name': branch_product.product.product_name,
            'branch_name': branch_product.branch.branch_name,
            'price': str(branch_product.price),
            'stock_quantity': branch_product.stock_quantity,
            'is_available': branch_product.is_available,
        }
    }, status = 200)



# ======================================================
# Delete Branch Product
# ======================================================
@api_view(['DELETE'])
@permission_classes([IsAdminOrBranchManager])
def DeleteBranchProduct(request, branch_product_id):
    try:
        branch_product = BranchProduct.objects.get(id=branch_product_id)
    except BranchProduct.DoesNotExist:
        return Response({'error': 'Branch product not found'}, status=404)

    if request.user.role == 'branch_manager':
        try:
            branch = request.user.managed_branch
        except Exception:
            return Response({'error': 'You are not assigned to any branch'}, status = 404)
        if branch_product.branch != branch:
            return Response({'error': 'You can only delete products in your own branch'}, status = 403)

    branch_product.delete()
    return Response({'message': 'Product removed from branch successfully'}, status  =200)



# ======================================================
# My branch product
# ======================================================
@api_view(['GET'])
@permission_classes([IsBranchManager])
def MyBranchProducts(request):
    try:
        branch = request.user.managed_branch
    except Exception:
        return Response({'error': 'You are not assigned to any branch'}, status=404)

    queryset = BranchProduct.objects.filter(
        branch = branch
    ).select_related('product', 'product__category').order_by('product__product_name')

    category_id = request.query_params.get('category')
    if category_id:
        queryset = queryset.filter(product__category_id = category_id)

    search = request.query_params.get('search')
    if search:
        queryset = queryset.filter(product__product_name__icontains = search)

    low_stock = request.query_params.get('low_stock')
    if low_stock == 'true':
        queryset = queryset.filter(stock_quantity__lt=10)

    data = []
    for item in queryset:
        data.append({
            'id': item.id,
            'product_name': item.product.product_name,
            'category': item.product.category.category_name,
            'image': request.build_absolute_uri(item.product.image.url) if item.product.image else None,
            'price': str(item.price),
            'stock_quantity': item.stock_quantity,
            'is_available': item.is_available,
            'in_stock': item.in_stock,
        })
    return Response(data, status = 200)