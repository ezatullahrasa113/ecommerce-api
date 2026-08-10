from django.db import models
from decimal import Decimal
from .utils import generate_unique_slug
from django.utils.text import slugify

# Create your models here.


class Category(models.Model):
    name = models.CharField(max_length=255,unique=True)
    slug = models.SlugField(max_length=255,unique=True,blank=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'Categories'

    
    def save(self, *args, **kwargs):
       if not self.slug:
        
        self.slug=slugify(self.name)
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category,related_name='products',on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255,unique=True,blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10,decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f'{self.name} - ${self.price}'

    def apply_discount(self,percentage:float) -> None:
        # applies a discount to the product price.

        discount_amount = self.price*Decimal(percentage/100)
        self.price -= discount_amount
        self.save()

    def save(self, *args, **kwargs):
            
            if not self.pk:
                    self.slug = generate_unique_slug(self,self.name)
    
            else:
                    old = Product.objects.get(pk = self.pk)
    
                    if old.name != self.name:
                        self.slug = generate_unique_slug(self,self.name)
    
            super().save(*args, **kwargs)