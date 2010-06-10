# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'ViewMetaData'
        db.create_table('seo_viewmetadata', (
            ('metadata_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['seo.MetaData'], unique=True, primary_key=True)),
            ('view', self.gf('seo.viewmetadata.SystemViewField')(max_length=255, unique=True, null=True, blank=True)),
        ))
        db.send_create_signal('seo', ['ViewMetaData'])

        # Deleting field 'MetaData.view'
        db.delete_column('seo_metadata', 'view')


    def backwards(self, orm):
        
        # Deleting model 'ViewMetaData'
        db.delete_table('seo_viewmetadata')

        # Adding field 'MetaData.view'
        db.add_column('seo_metadata', 'view', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255, null=True, blank=True), keep_default=False)


    models = {
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'seo.metadata': {
            'Meta': {'object_name': 'MetaData'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'extra': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'heading': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '511', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '255', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'subheading': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '511', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '511', 'blank': 'True'})
        },
        'seo.viewmetadata': {
            'Meta': {'object_name': 'ViewMetaData', '_ormbases': ['seo.MetaData']},
            'metadata_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['seo.MetaData']", 'unique': 'True', 'primary_key': 'True'}),
            'view': ('seo.viewmetadata.SystemViewField', [], {'max_length': '255', 'unique': 'True', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['seo']
