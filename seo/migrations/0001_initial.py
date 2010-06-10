# -*- coding: utf-8 -*-

from south.db import db
from django.db import models
from seo.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'MetaData'
        db.create_table('seo_metadata', (
            ('id', models.AutoField(primary_key=True)),
            ('path', models.CharField(default='', unique=True, max_length=255, blank=True)),
            ('title', models.CharField(default='', max_length=511, blank=True)),
            ('heading', models.CharField(default='', max_length=511, blank=True)),
            ('subheading', models.CharField(default='', max_length=511, blank=True)),
            ('keywords', models.TextField(default='', blank=True)),
            ('description', models.TextField(default='', blank=True)),
            ('extra', models.TextField(default='', blank=True)),
            ('content_type', models.ForeignKey(orm['contenttypes.ContentType'], null=True, editable=False, blank=True)),
            ('object_id', models.PositiveIntegerField(null=True, editable=False, blank=True)),
        ))
        db.send_create_signal('seo', ['MetaData'])
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'MetaData'
        db.delete_table('seo_metadata')
        
    
    
    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label','model'),)", 'db_table': "'django_content_type'"},
            '_stub': True,
            'id': ('models.AutoField', [], {'primary_key': 'True'})
        },
        'seo.metadata': {
            'Meta': {'ordering': '("path",)'},
            'content_type': ('models.ForeignKey', ["orm['contenttypes.ContentType']"], {'null': 'True', 'editable': 'False', 'blank': 'True'}),
            'description': ('models.TextField', [], {'default': "''", 'blank': 'True'}),
            'extra': ('models.TextField', [], {'default': "''", 'blank': 'True'}),
            'heading': ('models.CharField', [], {'default': "''", 'max_length': '511', 'blank': 'True'}),
            'id': ('models.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('models.TextField', [], {'default': "''", 'blank': 'True'}),
            'object_id': ('models.PositiveIntegerField', [], {'null': 'True', 'editable': 'False', 'blank': 'True'}),
            'path': ('models.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255', 'blank': 'True'}),
            'subheading': ('models.CharField', [], {'default': "''", 'max_length': '511', 'blank': 'True'}),
            'title': ('models.CharField', [], {'default': "''", 'max_length': '511', 'blank': 'True'})
        }
    }
    
    complete_apps = ['seo']
