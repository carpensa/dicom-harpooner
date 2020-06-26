from django import forms
from dicoms.models import Search, Session, Series
from os.path import basename, normpath
from django.utils.translation import ugettext_lazy as _
from bootstrap_datepicker_plus import DatePickerInput

from drf_braces.serializers.form_serializer import FormSerializer
import json


class SearchForm(forms.ModelForm):
    class Meta:
        model = Search
        fields = "__all__"

        labels = {
            'subject_search': _('Patient ID'),
            'study_search': _('Study Description'),
            'date_range_alpha': _('Start date'),
            'date_range_omega': _('End date')
        }
        help_texts = {
            'date_range_alpha': _('Enter study start date in format YYYY-MM-DD (Not required)'),
            'date_range_omega': _('Enter study end date in format YYYY-MM-DD (Not required)'),
            'multi_search': _('Search for multiple subjects by uploading a .txt file with one patient ID per line')
        }
        widgets = {
            'date_range_alpha': DatePickerInput(format='%Y-%m-%d'),
            'date_range_omega': DatePickerInput(format='%Y-%m-%d')
        }


class SerializedSearchForm(FormSerializer):
    class Meta(object):
        form = SearchForm

def make_conversion_form(session_id):
    """
    This is a form class generator, but I'm not sure if it's the best way to make dynamic
    forms.

    I'm going to attempt to create a dynamic form more directly below in
    ConversionForm2
    :param session_id:
    :return:
    """

    if Series.objects.filter(Session=session_id).exists():
        series_from_session = Series.objects.filter(Session=session_id)

        # loading choices for scan types from bidspec
        with open("dicoms/static/jss/bids_spec.json") as infile:
            bidspec = json.load(infile)
        scan_choices = bidspec['anat'] + bidspec['func'] + bidspec['fmap']
        scan_choices.sort()

        # creating a tuple list to pass to our form's select widget
        # django requires a tuple so we're making one
        tuple_scan_choices = [(scan, scan) for scan in scan_choices]

        fields = {}
        list_of_series = []

        # cleaning up path to get last dir/series name
        for each in series_from_session:
            list_of_series.append(each.Path)
        cleaned_series = [basename(normpath(single_series)) for single_series in list_of_series]
        cleaned_series_set = set(cleaned_series)
        cleaned_series = list(cleaned_series_set)

        for series in cleaned_series:
            fields[series] = forms.Select(choices=tuple_scan_choices)

        return type("ConversionForm", (forms.BaseForm,), {'base_fields': fields})

    else:
        return None


class ConversionForm2(forms.Form):
    name = forms.CharField(max_length=255)

    def __init__(self, session):
        super(ConversionForm2, self).__init__(session)
        series_from_session = Series.objects.filter(Session=session)
        bidspec = json.load(open("dicoms/bids_spec.json"))
        scan_choices = bidspec['anat'] + bidspec['func'] + bidspec['fmap']
        scan_choices.sort()

        # creating a tuple list to pass to our form's select widget
        # django requires a tuple so we're making one
        tuple_scan_choices = [(scan, scan) for scan in scan_choices]

        fields = {}
        list_of_series = []

        # cleaning up path to get last dir/series name
        for each in series_from_session:
            list_of_series.append(each.Path)
        cleaned_series = [basename(normpath(single_series)) for single_series in list_of_series]
        cleaned_series_set = set(cleaned_series)
        cleaned_series = list(cleaned_series_set)

        # for series in cleaned_series:
        #    fields[series] = forms.Select(tuple_scan_choices)

        # self.fields = fields
