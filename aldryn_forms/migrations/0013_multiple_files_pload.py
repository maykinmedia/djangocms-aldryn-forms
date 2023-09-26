# Generated by Django 2.2.13 on 2022-03-14 15:12

import django.db.models.deletion
from django.db import migrations, models

import djangocms_attributes_field.fields
import filer.fields.folder

import aldryn_forms.models
import aldryn_forms.sizefield.models


class Migration(migrations.Migration):

    dependencies = [
        ('aldryn_forms', '0012_auto_20190104_1242'),
    ]

    operations = [
        migrations.AddField(
            model_name='fileuploadfieldplugin',
            name='accepted_types',
            field=models.CharField(blank=True, help_text='The list of accepted types. E.g. ".pdf .jpg .png text/plain application/msword image/*".', max_length=255, null=True, validators=[aldryn_forms.models.validate_accepted_types], verbose_name='Accepted types'),
        ),
        migrations.AddField(
            model_name='fileuploadfieldplugin',
            name='enable_js',
            field=models.NullBooleanField(help_text='Enable javascript to view files for upload.', verbose_name='Enable js'),
        ),
        migrations.AddField(
            model_name='imageuploadfieldplugin',
            name='enable_js',
            field=models.NullBooleanField(help_text='Enable javascript to view files for upload.', verbose_name='Enable js'),
        ),
        migrations.AlterField(
            model_name='formplugin',
            name='action_backend',
            field=models.CharField(choices=[('default', 'Default'), ('email_only', 'Email only'), ('none', 'None')], default='default', max_length=15, verbose_name='Action backend'),
        ),
        migrations.CreateModel(
            name='MultipleFilesUploadFieldPlugin',
            fields=[
                ('name', models.CharField(blank=True, help_text='Used to set the field name', max_length=255, verbose_name='Name')),
                ('label', models.CharField(blank=True, max_length=255, verbose_name='Label')),
                ('required', models.BooleanField(default=False, verbose_name='Field is required')),
                ('required_message', models.TextField(blank=True, help_text='Error message displayed if the required field is left empty. Default: "This field is required".', null=True, verbose_name='Error message')),
                ('placeholder_text', models.CharField(blank=True, help_text='Default text in a form. Disappears when user starts typing. Example: "email@example.com"', max_length=255, verbose_name='Placeholder text')),
                ('help_text', models.TextField(blank=True, help_text='Explanatory text displayed next to input field. Just like this one.', null=True, verbose_name='Help text')),
                ('attributes', djangocms_attributes_field.fields.AttributesField(blank=True, default=dict, verbose_name='Attributes')),
                ('min_value', models.PositiveIntegerField(blank=True, null=True, verbose_name='Min value')),
                ('max_value', models.PositiveIntegerField(blank=True, null=True, verbose_name='Max value')),
                ('initial_value', models.CharField(blank=True, help_text='Default value of field.', max_length=255, verbose_name='Initial value')),
                ('custom_classes', models.CharField(blank=True, max_length=255, verbose_name='custom css classes')),
                ('cmsplugin_ptr', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, related_name='aldryn_forms_multiplefilesuploadfieldplugin', serialize=False, to='cms.CMSPlugin')),
                ('max_size', aldryn_forms.sizefield.models.FileSizeField(blank=True, help_text='The maximum file size of the upload, in bytes. You can use common size suffixes (kB, MB, GB, ...).', null=True, verbose_name='Maximum file size')),
                ('enable_js', models.NullBooleanField(help_text='Enable javascript to view files for upload.', verbose_name='Enable js')),
                ('accepted_types', models.CharField(blank=True, help_text='The list of accepted types. E.g. ".pdf .jpg .png text/plain application/msword image/*".', max_length=255, null=True, validators=[aldryn_forms.models.validate_accepted_types], verbose_name='Accepted types')),
                ('max_files', models.PositiveSmallIntegerField(blank=True, help_text='Maximum number of uploaded files.', null=True, verbose_name='Max. files')),
                ('upload_to', filer.fields.folder.FilerFolderField(help_text='Select a folder to which all files submitted through this field will be uploaded to.', on_delete=django.db.models.deletion.CASCADE, to='filer.Folder', verbose_name='Upload files to')),
            ],
            options={
                'abstract': False,
            },
            bases=('cms.cmsplugin',),
        ),
    ]