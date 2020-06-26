from django.db import models
from django.utils import timezone


# Create your models here.
class Subject(models.Model):
    """
    Subject model gets created when a subject is located during a dicom
    crawl. This subject is then linked to a session.

    : subject_id : the (hopefully) unique identifier of a subject who posseses
    dicoms. This id will be determined from the information gleaned in dicom
    from the dicom header
    : AKA : this value can reflect either the SubjectID or it could be something
    placed/renamed by the user. The use case for this field is to make provide
    the user with a method to correct/rename subject ids that may have been entered
    incorrectly into the original DICOM header data.
    : slug : a version of the subject id with spaces or other unfriendly chars
    removed. If one ends up creating pages for subjects this field will come in
    handy.
    """
    SubjectID = models.CharField(unique=True, max_length=200)
    AKA = models.CharField(blank=True, max_length=200, null=True)
    slug = models.SlugField(unique=True, max_length=200, blank=True)

    def __str__(self):
        return self.SubjectID


class Session(models.Model):
    """
    This class keeps track of an entire session consisting of one or more
    series/scans. When converting from dicom to bids the filepath of this
    session/folder is what will be passed as one of the arguments, not the
    individual series.
    : Subject : The subject/patient of the session linked to the Subject model
    above
    : SessionName : A field accessible to the user/converter to rename/organize
    sessions, i.e. (baseline, phase1, end, etc)
    : Path : the pat to the session folder
    : StudyDescription : If available w/in the dicom header this info will be
    included in this model
    : DateIndexed : date that this session was added/updated to the database
    : SessionDate : date on which the session took place, inferred from dicom
    header or from the creation date of the Path variable above.
    : owner : owner of the folder on the host machine
    : group : group ownership on the host machine/dicom source
    """
    # group to contain all scans on a given day for a single subject
    Subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    SessionName = models.CharField(max_length=255, blank=True, default=None, null=True)
    Path = models.TextField(default=None)
    StudyDescription = models.CharField(max_length=255, default=None, blank=True, null=True)
    DateIndexed = models.DateTimeField(default=timezone.now, null=True)
    SessionDate = models.DateTimeField(default=None, null=True, blank=True)
    owner = models.CharField(max_length=255, default=None, null=True)
    group = models.CharField(max_length=255, default=None, null=True)

    def __str__(self):
        return self.Path


class Series(models.Model):
    """
    This class stores information about a single individual's
    session. Information is populated into this class via
    crawling the directory where the subjects dicoms are located,
    reading the information stored in the dicom headers, and
    keeping track of that info along with the full path to
    those dicoms, the user that found them, and the permissions
    of the user.

    : AquisitionTime : time of aquisition extracted from dicom header
    : dcm_to_bids_text : json config for dcm2bids conversion, redundant now
    : ImageType : list of types of images,
    : IndexedDate : date that this session was entered into the database
    : Path : path to the dicoms of this subject's session
    : PatientID : should match subject_id
    : SeriesDate : date of session extracted from dicom header
    that this json has its own model.
    """

    Subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    # time of dicom acquisition, extracted from dicom header
    AcquisitionTime = models.DateTimeField(default=None, blank=True, null=True)
    # Image type (list of image types??) Ask Darrick
    ImageType = models.CharField(default=None, blank=True, max_length=255, null=True)
    # date that the session was entered into the database
    IndexedDate = models.DateTimeField(default=timezone.now, blank=True, null=True)
    # path to subject
    Path = models.TextField(default=None)
    # patient_id should match subject id, probably redundant
    PatientID = models.CharField(max_length=200, unique=False, null=True)
    # date of session, extracted from dicom header
    SeriesDate = models.DateTimeField(default=None, blank=True, null=True)
    # study date extracted from dicom header
    StudyDate = models.DateTimeField(default=None, blank=True, null=True)
    # Session
    Session = models.ForeignKey("Session", on_delete=True, default=None,
                                blank=True, null=True)
    # SeriesDescription
    SeriesDescription = models.CharField(max_length=255, blank=True, null=True)
    # StudyDescription
    StudyDescription = models.CharField(max_length=255, blank=True, null=True)
    # SeriesNumber
    SeriesNumber = models.IntegerField(default=None, blank=True, null=True)

    def __str__(self):
        return self.Path

    # class Meta:
    #    unique_together = (("Path", "PatientID"),)


class Search(models.Model):
    """
    This search model exists to keep track of each dicom search, but moreso
    to provide a model from which a django search form is generated. Could be
    redundant, but right now it's in use so there's no need to fiddle with it.

    Also keeping track of searches could provide useful metrics later on down
    the line.
    : subject_search : search field for searching by subject id's
    : study_search : search field for searching by study name/description (not sure which)
    : date_range_alpha : starting date of search, defaults to epoch time in views
    : date_range_omega : ending date of search, defaults to now in view
    : multi_search : file field upload to allow the user to upload a list of subject
    ids to search the database for (as of 09/05/19 it only accepts text files with each
    subject id separated by a newline break.
    """
    subject_search = models.CharField(max_length=255, blank=True)
    study_search = models.CharField(max_length=255, blank=True)
    date_range_alpha = models.DateTimeField(blank=True, null=True)
    date_range_omega = models.DateTimeField(blank=True, null=True)
    multi_search = models.FileField(upload_to='subject_lists/',
                                    blank=True)

    def __str__(self):
        if self.subject_search and not self.study_search:
            return self.subject_search
        elif self.study_search and not self.subject_search:
            return self.study_search
        elif not self.subject_search and not self.study_search \
                and (self.date_range_alpha and self.date_range_omega):
            return self.date_range_omega.strftime("%Y-%m-%d") + " to " + \
                   self.date_range_alpha.strftime("%Y-%m-%d")
        else:
            return str(self.pk)