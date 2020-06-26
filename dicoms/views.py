from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.utils import timezone, dateparse
from django.utils.datastructures import MultiValueDictKeyError
from django.core import serializers

# importing path to project
from django.conf import settings

from django.views.decorators.csrf import csrf_exempt
from dicoms.forms import SearchForm, make_conversion_form, ConversionForm2
from dicoms.models import Subject, Session, Series
from string import ascii_letters, digits


from utils.transfer import login_and_sync


# standard library imports
from os.path import basename, normpath, dirname, realpath, join
from ast import literal_eval
from difflib import SequenceMatcher, get_close_matches
import json
from operator import itemgetter
import os
import threading
from utils.transfer import transfer_files

# for doing processing asyncronously, timeouts often occur otherwise

DICOMS_APP_FOLDER = dirname(realpath(__file__))
PROCESSED_BIDS = settings.CONVERTED_FOLDER
EPOCH_TIME = '1970-01-01T00:00:00Z'  # shouldn't have any dicoms older than this.


# Create your views here.
def get_all_subjects(request):
    """
    This doesn't really do anything, you should probably delete it.
    :param request:
    :return:
    """
    all_subjects = Subject.objects.all().order_by('SubjectID')
    context_dict = {'all_subjects': all_subjects}
    serialized_context = serialize_context_dict(context_dict)
    context_dict['serialized'] = serialized_context
    return render(request, 'dicoms/index.html', context_dict)


def search_subjects(request):
    """
    This is our search view, at present it collects queries relating to:
        - Subject ID
        - Study Name
        - Date Range Start
        - Date Range Start
    Then validates these entries, after which it redirects to the search
    results view.
    :param request:
    :return: Redirect to search results if search button is pressed and form fields
    are valid or renders this view again if this request is not POST
    """

    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
            search = form.save(commit=False)
            search.subject_search = request.POST['subject_search']
            search.study_search = request.POST['study_search']

            # if user supplied a starting date and it's valid
            # or if  they didn't at all.
            date_fields_provided = False
            if request.POST['date_range_alpha'] and \
                    dateparse.parse_date(request.POST['date_range_alpha']):
                with_tz = dateparse.parse_date(request.POST['date_range_alpha'])
                search.date_range_alpha = with_tz
                date_fields_provided = True
            else:
                search.date_range_alpha = dateparse.parse_datetime(EPOCH_TIME)

            # similar logic for and end date, if not is supplied defaults to now
            if request.POST['date_range_omega'] and \
                    dateparse.parse_date(request.POST['date_range_omega']):
                with_tz = dateparse.parse_date(request.POST['date_range_omega'])
                search.date_range_omega = with_tz
                date_fields_provided = True
            else:
                search.date_range_omega = timezone.now()

            # if no file is specified pass
            try:
                if request.FILES['multi_search']:
                    search.multi_search = request.FILES['multi_search']
            except MultiValueDictKeyError:
                pass

            # saving search to our database, not sure how necessary this is, but hey
            # why not?
            search.save()

            # If the user passes in a text file to the search with a list of
            # subjects do the following
            if search.multi_search:
                readit = search.multi_search.read()

                decoded = readit.decode('utf-8')
                subject_list = decoded.splitlines()
                list_search_queryset = Session.objects.none()
                for subject in subject_list:
                    one_from_list_queryset = Session.objects.filter(Subject__SubjectID__contains=subject,
                                                                    SessionDate__range=[search.date_range_alpha,
                                                                                  search.date_range_omega])
                    list_search_queryset = one_from_list_queryset | list_search_queryset
            else:
                list_search_queryset = Session.objects.none()

            # retrieving sessions via subject id's, if else is necessary to avoid returning
            # all sessions. '' returns every session.
            if search.subject_search:
                subject_queryset = Session.objects.filter(Subject__SubjectID__contains=search.subject_search,
                                                          SessionDate__range=[search.date_range_alpha,
                                                                              search.date_range_omega])
            else:
                subject_queryset = Session.objects.none()

            # retrieving sessions via StudyDescription, if else is necessary to avoid returning
            # all sessions. '' returns every session.
            if search.study_search:
                study_queryset = Session.objects.filter(StudyDescription__contains=search.study_search,
                                                        SessionDate__range=[search.date_range_alpha,
                                                                            search.date_range_omega])
            else:
                study_queryset = Session.objects.none()

            # if user provides a date
            if date_fields_provided and not search.subject_search and not search.multi_search \
                    and not search.study_search:
                date_set = Session.objects.filter(SessionDate__range=[search.date_range_alpha,
                                                                      search.date_range_omega])
            else:
                date_set = Session.objects.none()
            # combining querysets is equivalent to set(subject_queryset + study_queryset)

            full_set = subject_queryset | study_queryset | list_search_queryset | date_set
            full_set = full_set.order_by("Subject", "SessionDate")

            ### Below Don't DO THIS, it's just a fix for Johnny in the short term
            # TODO REMOVE THIS, SERIOUSLY 08/28/19
            try:
                date_stamp = timezone.now().isoformat()
                special_path = '/group_shares/fnl/scratch/for_johnny'
                full_path = os.path.join(special_path, date_stamp)
                with open(full_path, 'w') as outfile:
                    for subject in full_set:
                        print(subject.Subject, subject.Path, file=outfile)
            except:
                pass


            # populating our context dictionary
            context = {
                'search': search,
                'sessions': full_set}

            serialized = serialize_context_dict({'sessions': context['sessions']})
            context['serialized'] = serialized
            print(serialized)
            # redirecting/rendering the results to it's own html.
            return render(request, 'dicoms/search_results.html', context)
    else:
        form = SearchForm()

    return render(request, 'dicoms/search.html', {'form': form})


def search_results(request):
    print(request)
    if request.method == "GET":
        print("dicoms.views.search_results rendered this page via get")
        return render(request, "dicoms/search_results.html")
    else:
        print("dicoms.views.search_results rendered this page via a post")
        return render(request, "dicoms/search_results.html")


def extract_most_complete_series_names(sessions):
    """
    Presently, the user will have to choose a subject that has the most
    representative number of scans to constitute a 'complete' series.
    This function determines completeness based on the number of unique
    series that a subject possesses.

    It would be better if the most complete series/scan list was
    gotten by looking through every subject and extracting unique
    series from that list, but for this moment we're relying on the user
    to make a good choice.
    :param sessions: A queryset of selected sessions passed in from a
    search
    :return: a single session's PK where that session contains the most
    complete ((although it might be better to
    return the session entirely, saves ourselves 1 query)
    """
    subject_and_series = {}
    for session in sessions:
        series = session.series_set.all()
        list_of_series = []
        for each in series:
            list_of_series.append(each.Path)
        cleaned_series = [basename(normpath(single_series)) for single_series in list_of_series]
        cleaned_series_set = set(cleaned_series)
        cleaned_series = list(cleaned_series_set)
        subject_and_series[session.pk] = cleaned_series

    sorted_by_num_series = sorted(subject_and_series,
                                  key=lambda k: len(subject_and_series[k]),
                                  reverse=True)
    if sorted_by_num_series:
        return sorted_by_num_series[0]
    else:
        return None


def extract_unique_series(sessions):
    """
    Presently, the user will have to choose a subject that has the most
    representative number of scans to constitute a 'complete' series.
    This function determines completeness based on the number of unique
    series that a subject possesses.

    It would be better if the most complete series/scan list was
    gotten by looking through every subject and extracting unique
    series from that list, but for this moment we're relying on the user
    to make a good choice.
    :param sessions: A queryset of selected sessions passed in from a
    search
    :return: a single session's PK where that session contains the most
    complete ((although it might be better to
    return the session entirely, saves ourselves 1 query)
    """
    subject_and_series = {}
    series_description = []
    storage_dict = {}
    series_number = {}
    for session in sessions:
        series = session.series_set.all()
        list_of_series = []
        # this dictionary is being used to store k: series desc, v: series primary key
        # it's necessary to divorce the two and easily reunite them later.
        # this is done solely so that when referring to html elements id's in the templates
        # that there are only numbers, no invalid characters referenced (it's fine for
        # rendering, but jquery does not like invalid chars).

        for each in series:
            list_of_series.append(each.SeriesDescription)
            storage_dict[each.SeriesDescription] = each.pk
            series_number[each.SeriesDescription] = each.SeriesNumber

        series_description = series_description + list_of_series

    unique_series = list(set(series_description))

    unique_w_pk = [(series, storage_dict[series], series_number[series]) for series in unique_series]
    unique_w_pk.sort(key=lambda tup: tup[2])

    return unique_w_pk


def search_selection(request):
    """
    This view allows the user to select multiple subjects for either
    conversion to bids format or for the generation of a conversion file
    for dcm2bids (note as of now it defaults to only choosing the subject
    with the most "complete" series, however this behavior can be modified
    easily in the extract series def within this module.
    :param request:
    :return: A redirect to a dcm2bids conversion page where the user is able
    to either pick a dcm2bids config file for the subjects they've chosen or
    generate one with the use of drop downs./home/exacloud/lustre1/fnl_lab/projects/INFANT/GEN_INFANT/masking_test/
    """
    if request.method == 'POST':
        context = {}
        # getting the primary keys of the sessions selected from the
        # previous view
        selected_subjects = request.POST.getlist("search_selection")
        if selected_subjects:
            request.session['selected_subjects'] = selected_subjects
        # retrieving the sessions with another query, this is possibly inefficient
        # but it works for now
        sessions = Session.objects.filter(pk__in=selected_subjects)

        context['sessions'] = sessions
        if context['sessions']:
            request.session['sessions'] = list(context['sessions'].values_list('pk', flat=True))
        # here we collect the session with the most series/scans in it
        session_id = extract_most_complete_series_names(sessions)

        # getting unique series descriptions
        unique_series = extract_unique_series(sessions)
        # context['session'] = Session.objects.get(pk=session_id)
        context['session'] = get_object_or_404(Session, pk=session_id)
        if context['session']:
            request.session['session'] = session_id
        # next collect every series corresponding to that session
        context['series'] = Series.objects.filter(Session=session_id)
        context['unique_series'] = unique_series
        if context['series']:
            request.session['series'] = list(context['series'].values_list('pk', flat=True))
            request.session['unique_series_description'] = context['unique_series']
        # keeping track of our selected subjects from the earlier search for
        # the next view.
        context['search_selection'] = selected_subjects
        serialized = serialize_context_dict(context)
        context['serialized'] = serialized
        return redirect('/dicoms/convert_builder/')

    else:
        context = {}
        serialized = serialize_context_dict(context)
        context['serialized'] = serialized
        return render(request, "dicoms/search.html", context)
        # return render(request, "dicoms/search.html", context)


def convert_subjects(request):  # , session_id):
    """
    This view directs the user to the page where the user creates a
    dicom configuration for their study/subject.
    :param request:
    :param : A context dictionary containing subjects,
    sessions, series, a list of primary keys corresponding with the previous
    selection of sessions that that person wishes to convert.
    :return:
    """
    date = timezone.localtime(timezone.now()).isoformat()
    context = {}

    for k, v in request.session.items():
        if k == 'sessions':
            context['sessions'] = Session.objects.filter(pk__in=v)
        elif k == 'series':
            series = Series.objects.filter(pk__in=v)
            # trimming off only the informative part of the path
            trimmed = []
            series_description = []
            for each in series:
                trimmed.append({'folder': basename(normpath(each.Path)),
                                'SeriesDescription': each.SeriesDescription})
            # sorting series on folder path
            trimmed = sorted(trimmed, key=itemgetter('folder'))

            context['series'] = trimmed
        elif k == 'selected_subjects':
            context['subjects'] = Subject.objects.filter(pk__in=v)
        elif k == 'unique_series_description':
            context['unique_series_description'] = v

    if request.method == 'POST':
        # load conversion page
        series_pks = request.POST.getlist('pk')
        series_descriptions = request.POST.getlist('series')
        required_labels = request.POST.getlist('required_label')
        image_type = ['' for entry in series_pks]
        session_pks = request.session.get('selected_subjects')

        for index, pk in enumerate(series_pks):
            """Here we're getting the image types/descriptions from each scan/series"""
            series_image_type = Series.objects.get(pk=pk).ImageType
            image_type[index] = series_image_type


        # collecting vars for scp. Host, User, Path, etc.
        transfer_kwargs = {
            'destination': request.POST['remote-path'],
            'user': request.POST['remote-user'],
            'host': request.POST['remote-server'],
            'password': request.POST['remote-password'],
        }

        # shipping just the dicoms off to their destination
        convert(session_pks, transfer_kwargs)



        # serializing objects in context dictionary into json
        serialized = serialize_context_dict(context)
        context['serialized'] = serialized
        return render(request, "dicoms/convert_page.html", context)
    else:
        # reload this page without any selected subjects.
        serialized = serialize_context_dict(context)
        context['serialized'] = serialized
        return render(request, "dicoms/convert_builder.html", context)




@csrf_exempt
def create_dcm2bids_config(request):
    """
    This function exists as handler to be called the javascript in our convert builder
    page. This view will either build the conversion form from some of the information
    gleaned via jquery/js via some queries to the database to retrieve info. Or it will
    simply take in a json from jquery/js and populate a DcmToBidsJson and associate it
    with the requisite sessions that it's been created for.

    Edit: We're going to pass everything we collect here to python and do the work in
    this view. There's no reason to fight javascript unless you have to.
    :param request:
    :return:
    """

    if request.method == 'POST':
        print("posted to create_dcm2bids_config")
        return HttpResponse("you posted to create_dcm2bids_config")
    else:
        print("get'd to create_dcm2bids_config")
        return HttpResponse("you get'd or something else to create_dcm2bids_config")


def convert(selected_session_pks, transfer_kwargs=None):
    """
    This is the bit that actually does the work of converting dicoms into bids
    formatted nifti's and their corresponding sidecar.jsons. It takes three
    arguments and then passes those arguments to a dcm2bids to do the conversion.
    :param selected_session_pks: These are the primary keys for each session
    that the user has selected to be converted. An individual session corresponds
    to all of the imaging data acquired during a single visit (session, tautological
    description I know).
    :param config: The dcm2bids conf file that the user has created w/ via selecting
    the appropriate modalities, choosing custom labels, and selecting which scans
    to includ exclude in their conversion.
    :param output_dir: The directory where the output from the conversion will
    be stored.
    :return:
    """

    # querying the database for all of the sessions the user selected.
    selected_sessions = Session.objects.filter(pk__in=selected_session_pks)

    # converting
    for session in selected_sessions:
        # get participant ID. parse metadata to strip characters
        allowed = ascii_letters + digits
        participant_ID = ''.join([a for a in str(session.Subject) if a in allowed])

        # get session_ID. make sure it's in the format YYYYMMDD
        session_ID = session.SessionDate.strftime("%Y%m%d")

        # building kwargs to pass to dcm2bids
        transfer_kwargs["source"] = session.Path
        transfer_kwargs["subject_id"] = participant_ID
        transfer_kwargs["session"] = session_ID
        transfer_kwargs["session_date"] = session_ID


        # if provided with transfer args, moving across server or locally
        if transfer_kwargs:
            transfer_files(**transfer_kwargs)

    return 0


def serialize_context_dict(dictionary: dict) -> str:
    temp_dict = {}
    try:
        for key, value in dictionary.items():
            isnt_model = False
            try:
                # if object is a django queryset or model type object
                if 'models' in str(type(value)):

                    # serializing object into string
                    first_pass = serializers.serialize("json", value)


                    # passing object back into a dictionary, we do this so we have access to the
                    # model/object attributes that were previously hidden within the class (well hidden to non-python)
                    back_to_dict = json.loads(first_pass)
                    temp_dict[key] = back_to_dict
                else:
                    isnt_model = True
            except (TypeError, AttributeError) as err:
                if err is TypeError and "models" in str(type(value)):
                    value = str(value)
                isnt_model = True

            if isnt_model:
                try:
                    # I think there is a smarter way to do this
                    temp_values = json.dumps(value)
                    temp_dict[key] = json.loads(temp_values)
                except TypeError:
                    if "model" in str(type(value)):
                        temp_dict[key] = str(value)
                    else:
                        temp_dict[key] = value
                    pass

    except AttributeError as err:
        print(err)

    return json.dumps(temp_dict)
