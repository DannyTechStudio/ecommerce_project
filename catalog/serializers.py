import hashlib
# from itertools import product
from rest_framework import serializers
from .models import Category, Product, ProductImage


# Category Serializer
class CategoryReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'created_at', 'updated_at']
    
    
class CategoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description']
        
    def validate_name(self, name):
        return name.strip()
    
    def validate_slug(self, slug):
        return slug.lower().strip()
    

# Product Serializer
class ProductReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'description', 'category', 'quantity', 'brand', 'price', 'is_active', 'created_at']
      
  
class ProductWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'description', 'category', 'brand', 'price', 'quantity', 'created_at', 'updated_at']
        read_only_fields = ['is_active', 'created_at', 'updated_at']
    
    def validate_name(self, name):
        name = name.strip()
        if len(name) < 3:
            raise serializers.ValidationError("Product must be at least 3 characters long.")
        
        return name
    
    def validate_quantity(self, quantity):
        if quantity <= 0:
            raise serializers.ValidationError("Quantity must not be zero or less")
        
        return quantity
    
    
    def validate_slug(self, slug):
        slug = slug.lower().strip()
        qs = Product.objects.filter(slug=slug)
        
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise serializers.ValidationError("A product with this slug already exits")
        
        return slug
    
    
    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must not be negative or zero")
        
        return value
            

    def validate_category(self, category):
        if not category.is_active:
            raise serializers.ValidationError("You cannot assign a product to an inactive category")
        
        return category
    
    
# ProductImage Serializer
class ProductImageReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'product', 'image', 'is_primary', 'created_at']
        read_only_fields = ['created_at']
        

class ProductImageWriteSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'is_primary', 'created_at']
        read_only_fields = ['created_at']
        
    def validate(self, attrs):
        instance = self.instance
        product = self.context['product']
        
        # checking product activeness
        if not product.is_active:
            raise serializers.ValidationError('This product is inactive.')
        
        # prevent product change on update
        if instance and instance.product != product:
            raise serializers.ValidationError('You cannot change the product of an existing image.') 
        
        # enforce max image upload on create
        if not instance:
            number_of_images = ProductImage.objects.filter(product=product).count()
            if number_of_images > 5:
                raise serializers.ValidationError('A product cannot have more than 5 images.')
        
        return attrs
    
    def validate_image(self, image):
        image = serializers.ImageField()
        
        # MIME type ckeck
        valid_mime_types = ['image/jpeg', 'image/png', 'image/webp']
        if image.content_type not in valid_mime_types:
            raise serializers.ValidationError('Unsupported image type. JPEG, PNG and WebP are only allowed.')
        
        # Image size check(2MB)
        if image.size > 2 * 1024 * 1024:
            raise serializers.ValidationError('Image must not exceed 2MB')
        
        # Duplicate image check (content-based)
        instance = self.instance
        product = self.context['product']
        incoming_image_hash = hashlib.sha256()
        for chunk in image.chunks():
            incoming_image_hash.update(chunk)
        incoming_image_digest = incoming_image_hash.hexdigest()
        
        qs = ProductImage.objects.filter(product=product)
        
        if instance:
            qs = qs.exclude(pk=instance.pk)
            
        for img in qs:
            existing_image_hash = hashlib.sha256()

            for chunk in img.image.chunks():
                existing_image_hash.update(chunk)

            existing_image_digest = existing_image_hash.hexdigest()
            if incoming_image_digest == existing_image_digest:
                raise serializers.ValidationError('This product already exist for this product.')

        # primary image reassignment
        if image.is_primary:

            qs = ProductImage.objects.filter(product=product, is_primary=True)
            if instance:
                qs = qs.exclude(pk=instance.pk)

            qs.update(is_primary=False)
    
        return image
            