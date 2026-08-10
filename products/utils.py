from django.utils.text import slugify


def generate_unique_slug(instance, value):
    """
    Generate a unique slug for a model instance.
    """

    base_slug = slugify(value)
    slug = base_slug
    counter = 1

    Model = instance.__class__

    while Model.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug