import urllib
import urllib2
import simplejson
import datetime
import tempfile

from django.core.files import File
from django.conf import settings
from django.db import models

from placenoun.behaviors.models import *
from placenoun.fileutilities.main import *

API_KEY = settings.API_KEY
IMAGE_SIZE_CHOICES = ('icon', 'small', 'medium', 'large', 'xlarge', 'xxlarge', 'huge')

class Noun(TimeStampable):
  text = models.CharField(max_length = 100)
  sfw = models.NullBooleanField(default = None)

  @property
  def nsfw():
    if sfw == False:
      return True
    elif sfw == True:
      return False
    else:
      return None

  class Meta:
    abstract = True

class NounImage(Noun):
  image = models.ImageField(upload_to="nouns/%Y/%m/%d", null = True)
  aspect_width = models.IntegerField(null = True)
  aspect_height = models.IntegerField(null = True)
  width = models.IntegerField(null = True)
  height = models.IntegerField(null = True)
  image_hash = models.CharField(max_length = 256, null = True)

  class Meta:
    abstract = True

class NounImageExternal(NounImage):
  url = models.URLField(verify_exists = False)

  def populate(self):
    file = get_file_from_url(self.url)
    self.image = File(file)

class Search(TimeStampable):
  last_searched = models.DateTimeField()
  has_results = models.NullBooleanField(default = None)
  query = models.SlugField()

  # Default search properties
  # @shazam: executes the search.  False says on results were found
  # @is_final: says that there are no more permutations to be executed
  # @next_permutation: relates to is_final stating that there is no other
  # search permuation to be executed
  @property
  def shazam():
    return False

  @property
  def is_final():
    return True

  @property
  def next_permutation():
    return False

class SearchGoogle(Search):
  response_code = models.CharField(max_length = 100)
  imgsz = models.CharField(max_length = 10)
  restrict = models.CharField(max_length = 32)
  filetype = models.CharField(max_length = 10)
  rights = models.CharField(max_length = 32)
  site = models.CharField(max_length = 100)

  @property
  def params(self):
    params = {}
    params['v'] = '1.0'
    if API_KEY:
      params['key'] = API_KEY
    params['q'] = self.query
    params['imgsz'] = self.imgsz
    params['restrict'] = self.restrict
    params['as_filetype'] = self.filetype
    params['as_rights'] = self.rights
    params['as_sitesearch'] = self.site

    return urllib.urlencode(params)

  # Executes the search.
  def shazam(self, raw = False):
    url = ('https://ajax.googleapis.com/ajax/services/search/images?' + self.params)
  
    request = urllib2.Request(url, None, {'Referer': 'http://www.placenoun.com/'})
    response = urllib2.urlopen(request)
    
    data = simplejson.load(response)

    # Allows the return of the raw google json data
    if raw:
      return data

    # Checks to be sure that we received a 200 response code.
    self.response = data['responseStatus']
    if not self.response == 200:
      self.save()
      return False

    # If there are zero results for the search. return False.
    self.has_results = len(data['responseData']['results'])
    if not self.has_results:
      self.save()
      return False

    # Iterate through the results and create blank image objects.
    for result in data['responseData']['results']:
      new_image = NounImageExternal.objects.create(
        url = result['url'],
        text = self.query,
        )

    return True
