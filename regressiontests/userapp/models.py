from django.db import models

class Page(models.Model):
    title = models.CharField(max_length=255, default="", blank=True)
    type = models.CharField(max_length=50, default="", blank=True)
    content = models.TextField(default="", blank=True)

    @models.permalink
    def get_absolute_url(self):
        return ('userapp_page_detail', [self.type], {})

    def __unicode__(self):
        return self.title or self.content


class Product(models.Model):
    meta_description = models.TextField(default="")
    meta_keywords    = models.CharField(max_length=255, default="")
    meta_title       = models.CharField(max_length=255, default="")

    @models.permalink
    def get_absolute_url(self):
        return ('userapp_product_detail', [self.id], {})

    def __unicode__(self):
        return self.meta_title


class Category(models.Model):
    name = models.CharField(max_length=255, default="M Category Name")
    page_title = models.CharField(max_length=255, default="M Category Page Title")

    @models.permalink
    def get_absolute_url(self):
        return ('userapp_my_view', ["abc"], {})

class NoPath(models.Model):
    pass
