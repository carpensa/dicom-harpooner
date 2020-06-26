import os
import pathlib
import sys
import time
import traceback

# importing django specific modules
import django
import pydicom
import pytz
from dateutil import parser as dateparser

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ImageSearcher.ImageSearcher.settings')
django.setup()

#from ImageSearcher.dicoms.models import Session, Subject, Series
from dicoms.models import Session, Subject, Series
from django.template.defaultfilters import slugify
from django.utils import timezone


def clean_name(name):
    return name.replace('_', '').replace('-', '').lower()


def index_dicoms(root_dir):
    """Index Structure:
        Key: PatientID
        Value: {}, keys are AcquisitionDate of series, values are
            {} with keys:
                path
                dcmcount: count of dcm files found
                desc:  SeriesDescription from the .dcm metadata
                time: AcquisitionTime from the .dcm metadata
                series: SeriesNumber from the .dcm metadata    
    """
    try:

        start_time = time.time()
        dcms_read_count = 0
        session_dict = {}
        len_session_dict = len(session_dict)
        directories_searched_count = 0
        old_subject_id = ''
        fast_mode = True
        do_once = True
        print("indexing {}".format(root_dir))
        for root, dirs, files in os.walk(root_dir):

            directories_searched_count += 1

            if directories_searched_count % 10 == 0:
                print("Directories Searched: {}".format(directories_searched_count))

            for f in files:
                print("Found File: {}".format(f))
                try:
                    dicom = pydicom.dcmread(os.path.join(root, f))
                    print("Read File: {}".format(f))
                    isdicom = True
                    print("     File: {} isdicom".format(f))
                    # this is a new one, some of these dicoms don't have a PatientID attribute
                    check_patient_id = dicom.PatientID
                    print("Collected PatientID: {}".format(check_patient_id))

                except (pydicom.errors.InvalidDicomError, FileNotFoundError, PermissionError, AttributeError, OSError):
                    isdicom = False
                if isdicom:
                    # initializing this variable once.
                    if do_once:
                        print(os.path.join(root,f))
                        old_subject_entry = pydicom.dcmread(os.path.join(root, f))
                        do_once = False

                    dcms_read_count += 1

                    test_subject_entry = pydicom.dcmread(os.path.join(root, f))
                    new_subject_id = test_subject_entry.PatientID
                    len_session_dict = len(session_dict)
                    if (new_subject_id != old_subject_id and session_dict != {}) \
                            or (len(files) == 0 and session_dict != {}):
                        average_paths = []
                        for k, v in session_dict.items():
                            average_paths.append(k)

                        # finding the average path of all fo the series in a session
                        average_path = os.path.commonpath(average_paths)
                        session_folder = pathlib.Path(average_path)
                        # finding folder permissions
                        session_group = session_folder.group()
                        session_owner = session_folder.owner()

                        # **************************************************************************************************
                        # Insert populating models here
                        try:
                            #     """This is hacky, you need to fix this."""
                            new_subject, sc = Subject.objects.get_or_create(SubjectID=old_subject_id,
                                                                            slug=slugify(old_subject_id))
                        except django.db.utils.IntegrityError:
                            traceback.print_exc(file=sys.stdout)
                            pass

                        # creating a session object
                        try:
                            new_session, new_ses_status = Session.objects.get_or_create(Subject=new_subject,
                                                                        Path=average_path,
                                                                        owner=session_owner,
                                                                        group=session_group)

                            aware = dateparser.parse(old_subject_entry.SeriesDate).replace(tzinfo=pytz.UTC)
                            new_session.SessionDate = aware
                            new_session.StudyDescription = old_subject_entry.StudyDescription
                            new_session.save()
                        except (AttributeError, django.db.utils.IntegrityError) as err:
                            # traceback.print_exc(file=sys.stdout)
                            new_session.save()
                            pass

                        # creating each series that took place during a session
                        for kwargs in session_dict.values():
                            try:
                                new_series, ns = Series.objects.get_or_create(**kwargs, Session=new_session, Subject=new_subject)
                                new_series.save()
                            except django.db.utils.IntegrityError:
                                traceback.print_exc(file=sys.stdout)
                        # **************************************************************************************************
                        # End populating models

                        session_dict = {}
                        old_subject_id = new_subject_id
                        old_subject_entry = test_subject_entry
                    else:
                        old_subject_id = new_subject_id
                        old_subject_entry = test_subject_entry
                    session_dict[root] = {}
                    new_len_session_dict = len(session_dict) # keeping track of the session dict, if it stops changing then
                    # we want to make sure to update the database with an entry.

                    # Below is a list of data that we're trying to extract from the dicom,
                    # we'll pass this list into a getattr try except, because occasionally
                    # some dicom's won't have the data we're looking for
                    dicom_data_we_want = ['SeriesDescription',
                                          'StudyDescription',
                                          'ImageType',
                                          'SeriesNumber',
                                          'PatientID',
                                          'SeriesDate',
                                          'StudyDate'
                                          ]
                    for attribute in dicom_data_we_want:
                        try:
                            if attribute is 'ImageType':
                                value = getattr(test_subject_entry, attribute)
                                value = str(value._list)
                                session_dict[root][attribute] = value
                            elif 'Date' in attribute:
                                value = getattr(test_subject_entry, attribute)
                                value = dateparser.parse(str(value)).replace(tzinfo=pytz.UTC)
                                session_dict[root][attribute] = value
                            else:
                                value = getattr(test_subject_entry, attribute)
                                session_dict[root][attribute] = str(value)
                        except (AttributeError, ValueError):
                            pass
                        finally:
                            session_dict[root]['IndexedDate'] = timezone.now()
                            session_dict[root]['Path'] = root

                if fast_mode:
                    break
        #### MODULARIZE THIS!!! this code previously failed to update the database if there was only one
        # subject
        #if len(files) == 0 and session_dict != {}:
        if session_dict != {}:
            print(files, session_dict)
            average_paths = []
            for k, v in session_dict.items():
                average_paths.append(k)

            # finding the average path of all fo the series in a session
            average_path = os.path.commonpath(average_paths)
            session_folder = pathlib.Path(average_path)
            # finding folder permissions
            session_group = session_folder.group()
            session_owner = session_folder.owner()

            # **************************************************************************************************
            # Insert populating models here
            try:
                #     """This is hacky, you need to fix this."""
                new_subject, sc = Subject.objects.get_or_create(SubjectID=old_subject_id,
                                                                slug=slugify(old_subject_id))
                print("Found new subject {}".format(new_subject))
            except django.db.utils.IntegrityError:
                traceback.print_exc(file=sys.stdout)
                pass

            # creating a session object
            try:
                new_session, new_ses_status = Session.objects.get_or_create(Subject=new_subject,
                                                                            Path=average_path,
                                                                            owner=session_owner,
                                                                            group=session_group)

                aware = dateparser.parse(old_subject_entry.SeriesDate).replace(tzinfo=pytz.UTC)
                new_session.SessionDate = aware
                new_session.StudyDescription = old_subject_entry.StudyDescription
                new_session.save()
                print("Found new session: {}".format(new_session.Path))
            except (AttributeError, django.db.utils.IntegrityError) as err:
                # traceback.print_exc(file=sys.stdout)
                new_session.save()
                pass

            # creating each series that took place during a session
            for kwargs in session_dict.values():
                try:
                    new_series, ns = Series.objects.get_or_create(**kwargs, Session=new_session, Subject=new_subject)
                    new_series.save()
                except django.db.utils.IntegrityError:
                    traceback.print_exc(file=sys.stdout)
        print("Elapsed Time: {}, {} dicoms checked in {} directories".format(
            time.time() - start_time,
            dcms_read_count,
            directories_searched_count))
    except (ValueError, IsADirectoryError):
        pass
    return 1


if __name__ == "__main__":
    index_dicoms("/dicom/2013")
    index_dicoms("/dicom")
