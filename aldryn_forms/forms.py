import re

from django import forms
from django.conf import settings
from django.forms.forms import NON_FIELD_ERRORS
from django.forms.utils import ErrorDict
from django.utils.translation import ugettext
from django.utils.translation import ugettext_lazy as _

from PIL import Image

from .models import FormPlugin, FormSubmission
from .sizefield.utils import filesizeformat
from .utils import add_form_error, get_action_backends, get_user_model


class FileSizeCheckMixin(object):

    def __init__(self, *args, **kwargs):
        self.files = []  # This is set in FormPlugin.process_form() in cms_plugins.py
        self.max_size = kwargs.pop('max_size', None)
        self.accepted_types = kwargs.pop('accepted_types', [])
        super(FileSizeCheckMixin, self).__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        super(FileSizeCheckMixin, self).clean(*args, **kwargs)

        if not self.files:
            return []

        all_errors = []

        # Check file extension.
        if self.accepted_types:
            accepted_types, main_mimetypes = self.split_mimetypes(self.accepted_types)
            errors = []
            for file_in_memory in self.files:
                match = re.search(r'(\.\w+)$', file_in_memory.name.lower())
                extension = match.group(1) if match else None  # '.csv'
                if not (
                        extension in self.accepted_types
                        or file_in_memory.content_type in self.accepted_types
                        or file_in_memory.content_type.split("/")[0] in main_mimetypes
                        ):
                    errors.append(ugettext('"%(file_name)s" is not of accepted file type.') % {
                        'file_name': file_in_memory.name,
                    })
            if errors:
                all_errors.append(
                    " ".join(errors) + " " + ugettext("Accepted file types are") + ": " + ", ".join(
                        self.accepted_types) + ".")

        # Check files size summary.
        if self.max_size is not None:
            errors = []
            files_size_summary = 0
            for file_in_memory in self.files:
                files_size_summary += file_in_memory.size
            if files_size_summary > self.max_size:
                if len(self.files) > 1:
                    msg = ugettext('The total file size has exceeded the specified limit %(size)s.')
                else:
                    msg = ugettext('File size exceeded the specified limit %(size)s.')
                all_errors.append(msg % {'size': filesizeformat(self.max_size)})

        if all_errors:
            raise forms.ValidationError(" ".join(all_errors))
        return self.files

    def split_mimetypes(self, accepted_types):
        """Split mimetypes with wildcards."""
        # Example of accepted_types: ['.pdf', 'text/plain', 'application/msword', 'image/*', 'text/*']
        accepted, main_mimetypes = [], []
        for name in accepted_types:
            match = re.match(r'(\w+)/\*', name)
            if match:
                main_mimetypes.append(match.group(1))
            else:
                accepted.append(name)
        return accepted, main_mimetypes


class RestrictedFileField(FileSizeCheckMixin, forms.FileField):
    pass


class RestrictedMultipleFilesField(FileSizeCheckMixin, forms.FileField):

    def __init__(self, *args, **kwargs):
        self.max_files = kwargs.pop('max_files', None)
        super(RestrictedMultipleFilesField, self).__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        super(RestrictedMultipleFilesField, self).clean(*args, **kwargs)
        if not self.files:
            return []
        if self.max_files is not None and len(self.files) > self.max_files:
            raise forms.ValidationError(
                ugettext("The number of uploaded files exceeded the set limit of %(limit)s.") % {
                    'limit': self.max_files
                })
        return self.files


class RestrictedImageField(FileSizeCheckMixin, forms.ImageField):

    def __init__(self, *args, **kwargs):
        self.max_width = kwargs.pop('max_width', None)
        self.max_height = kwargs.pop('max_height', None)
        super(RestrictedImageField, self).__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        data = super(RestrictedImageField, self).clean(*args, **kwargs)

        if data is None or not any([self.max_width, self.max_height]):
            return data

        if hasattr(data, 'image'):
            # Django >= 1.8
            width, height = data.image.size
        else:
            width, height = Image.open(data).size
            # cleanup after ourselves
            data.seek(0)

        if self.max_width and width > self.max_width:
            raise forms.ValidationError(
                ugettext(
                    'Image width must be under %(max_size)s pixels. '
                    'Current width is %(actual_size)s pixels.'
                ) % {
                    'max_size': self.max_width,
                    'actual_size': width,
                })

        if self.max_height and height > self.max_height:
            raise forms.ValidationError(
                ugettext(
                    'Image height must be under %(max_size)s pixels. '
                    'Current height is %(actual_size)s pixels.'
                ) % {
                    'max_size': self.max_height,
                    'actual_size': height,
                })

        return data


class FormSubmissionBaseForm(forms.Form):

    # these fields are internal.
    # by default we ignore all hidden fields when saving form data to db.
    language = forms.ChoiceField(
        choices=settings.LANGUAGES,
        widget=forms.HiddenInput()
    )
    form_plugin_id = forms.IntegerField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        self.form_plugin = kwargs.pop('form_plugin')
        self.request = kwargs.pop('request')
        super(FormSubmissionBaseForm, self).__init__(*args, **kwargs)
        language = self.form_plugin.language

        self.instance = FormSubmission(
            name=self.form_plugin.name,
            language=language,
            form_url=self.request.build_absolute_uri(self.request.path),
        )
        self.fields['language'].initial = language
        self.fields['form_plugin_id'].initial = self.form_plugin.pk

    def _add_error(self, message, field=NON_FIELD_ERRORS):
        try:
            self._errors[field].append(message)
        except (KeyError, TypeError):
            if not self._errors:
                self._errors = ErrorDict()
            self._errors[field] = self.error_class([message])

    def get_serialized_fields(self, is_confirmation=False):
        """
        The `is_confirmation` flag indicates if the data will be used in a
        confirmation email sent to the user submitting the form or if it will be
        used to render the data for the recipients/admin site.
        """
        for field in self.form_plugin.get_form_fields():
            plugin = field.plugin_instance.get_plugin_class_instance()
            # serialize_field can be None or SerializedFormField  namedtuple instance.
            # if None then it means we shouldn't serialize this field.
            serialized_field = plugin.serialize_field(self, field, is_confirmation)

            if serialized_field:
                yield serialized_field

    def get_serialized_field_choices(self, is_confirmation=False):
        """Renders the form data in a format suitable to be serialized.
        """
        fields = self.get_serialized_fields(is_confirmation)
        fields = [(field.label, field.value) for field in fields]
        return fields

    def get_cleaned_data(self, is_confirmation=False):
        fields = self.get_serialized_fields(is_confirmation)
        form_data = dict((field.name, field.value) for field in fields)
        return form_data

    def save(self, commit=False):
        self.instance.set_form_data(self)
        self.instance.save()


class ExtandableErrorForm(forms.ModelForm):

    def append_to_errors(self, field, message):
        add_form_error(form=self, message=message, field=field)


class FormPluginForm(ExtandableErrorForm):

    def __init__(self, *args, **kwargs):
        super(FormPluginForm, self).__init__(*args, **kwargs)

        if getattr(settings, 'ALDRYN_FORMS_SHOW_ALL_RECIPIENTS', False) and 'recipients' in self.fields:
            self.fields['recipients'].queryset = get_user_model().objects.all()

    def clean(self):
        redirect_type = self.cleaned_data.get('redirect_type')
        redirect_page = self.cleaned_data.get('redirect_page')
        url = self.cleaned_data.get('url')

        if redirect_type:
            if redirect_type == FormPlugin.REDIRECT_TO_PAGE:
                if not redirect_page:
                    self.append_to_errors('redirect_page', _('Please provide CMS page for redirect.'))
                self.cleaned_data['url'] = None

            if redirect_type == FormPlugin.REDIRECT_TO_URL:
                if not url:
                    self.append_to_errors('url', _('Please provide an absolute URL for redirect.'))
                self.cleaned_data['redirect_page'] = None
        else:
            self.cleaned_data['url'] = None
            self.cleaned_data['redirect_page'] = None

        action_backend = get_action_backends().get(self.cleaned_data.get('action_backend'))
        if action_backend is not None:
            error = getattr(action_backend, "clean_form", lambda form: None)(self)
            if error:
                self.append_to_errors('action_backend', error)
        return self.cleaned_data


class BooleanFieldForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        if 'instance' not in kwargs:  # creating new one
            initial = kwargs.pop('initial', {})
            initial['required'] = False
            kwargs['initial'] = initial
        super(BooleanFieldForm, self).__init__(*args, **kwargs)

    class Meta:
        fields = ['label', 'help_text', 'required', 'required_message', 'custom_classes']


class SelectFieldForm(forms.ModelForm):

    class Meta:
        fields = ['label', 'help_text', 'required', 'required_message', 'custom_classes']


class RadioFieldForm(forms.ModelForm):

    class Meta:
        fields = ['label', 'help_text', 'required', 'required_message', 'custom_classes']


class CaptchaFieldForm(forms.ModelForm):

    class Meta:
        # captcha is always required
        fields = ['label', 'help_text', 'required_message']


class MinMaxValueForm(ExtandableErrorForm):

    def clean(self):
        min_value = self.cleaned_data.get('min_value')
        max_value = self.cleaned_data.get('max_value')
        if min_value and max_value and min_value > max_value:
            self.append_to_errors('min_value', _(u'Min value can not be greater than max value.'))
        if self.cleaned_data.get('required') and min_value is not None and min_value < 1:
            self.append_to_errors('min_value', _('If checkbox "Field is required" is set, "Min choices" must be at least 1.'))
        return self.cleaned_data


class TextFieldForm(MinMaxValueForm):

    def __init__(self, *args, **kwargs):
        super(TextFieldForm, self).__init__(*args, **kwargs)

        self.fields['min_value'].label = _(u'Min length')
        self.fields['min_value'].help_text = _(u'Required number of characters to type.')

        self.fields['max_value'].label = _(u'Max length')
        self.fields['max_value'].help_text = _(u'Maximum number of characters to type.')
        self.fields['max_value'].required = False

    class Meta:
        fields = ['label', 'placeholder_text', 'help_text',
                  'min_value', 'max_value', 'required', 'required_message', 'custom_classes']


class HiddenFieldForm(ExtandableErrorForm):
    class Meta:
        fields = ['name', 'initial_value']


class EmailFieldForm(TextFieldForm):

    def __init__(self, *args, **kwargs):
        super(EmailFieldForm, self).__init__(*args, **kwargs)
        self.fields['min_value'].required = False
        self.fields['max_value'].required = False

    class Meta:
        fields = [
            'label',
            'placeholder_text',
            'help_text',
            'min_value',
            'max_value',
            'required',
            'required_message',
            'email_send_notification',
            'email_subject',
            'email_body',
            'custom_classes',
        ]

    def clean(self):
        if "name" in self.changed_data:
            _, action_backend = self.instance.get_parent_form_action_backend()
            if action_backend is not None:
                error = getattr(action_backend, "clean_field", lambda form: None)(self)
                if error:
                    self.append_to_errors('name', error)
        return super().clean()


class FileFieldForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(FileFieldForm, self).__init__(*args, **kwargs)
        self.fields['help_text'].help_text = _(
            'Explanatory text displayed next to input field. Just like this '
            'one. You can use MAXSIZE as a placeholder for the maximum size '
            'configured below.')

    class Meta:
        fields = ['label', 'help_text', 'required', 'required_message',
                  'custom_classes', 'upload_to', 'max_size']


class ImageFieldForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ImageFieldForm, self).__init__(*args, **kwargs)
        self.fields['help_text'].help_text = _(
            'Explanatory text displayed next to input field. Just like this '
            'one. You can use MAXSIZE, MAXWIDTH, MAXHEIGHT as a placeholders '
            'for the maximum file size and dimensions configured below.')

    class Meta:
        fields = FileFieldForm.Meta.fields + ['max_height', 'max_width']


class TextAreaFieldForm(TextFieldForm):

    def __init__(self, *args, **kwargs):
        super(TextAreaFieldForm, self).__init__(*args, **kwargs)
        self.fields['max_value'].required = False

    class Meta:
        fields = ['label', 'placeholder_text', 'help_text', 'text_area_columns',
                  'text_area_rows', 'min_value', 'max_value', 'required', 'required_message', 'custom_classes']


class MultipleSelectFieldForm(MinMaxValueForm):

    def __init__(self, *args, **kwargs):
        super(MultipleSelectFieldForm, self).__init__(*args, **kwargs)

        self.fields['min_value'].label = _(u'Min choices')
        self.fields['min_value'].help_text = _(u'Required amount of elements to chose.')

        self.fields['max_value'].label = _(u'Max choices')
        self.fields['max_value'].help_text = _(u'Maximum amount of elements to chose.')

    class Meta:
        # 'required' and 'required_message' depend on min_value field validator
        fields = ['label', 'help_text', 'min_value', 'max_value', 'custom_classes']
