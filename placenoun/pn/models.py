import urllib
import urllib2
import os
import simplejson
import datetime
import mimetypes
import tempfile
import shutil

from PIL import Image

try:
  from fractions import gcd
except ImportError:
  from placenoun.numberutilities.main import gcd

from django.core.files import File
from django.conf import settings
from django.db import models
from django.http import HttpResponse, Http404
from django.template.defaultfilters import slugify

from placenoun.behaviors.models import *
from placenoun.fileutilities.main import *

API_KEY = settings.API_KEY
IMAGE_SIZE_CHOICES = ('icon', 'small', 'medium', 'large', 'xlarge', 'xxlarge', 'huge')

class Noun(TimeStampable):
  text = models.CharField(max_length = 100)
  sfw = models.NullBooleanField(default = None)

  @property
  def slug(self):
    return slugify(self.text)

  class Meta:
    abstract = True

def upload_path(instance, filename):
  return '/'.join([instance.slug, datetime.datetime.now().strftime('%Y/%m/%d'), os.path.basename(filename)])

class NounImage(Noun):
  image = models.ImageField(upload_to=upload_path, null = True)
  extension = models.CharField(max_length = 32, null = True)
  mime_type = models.CharField(max_length = 32, null = True)
  aspect_width = models.IntegerField(null = True)
  aspect_height = models.IntegerField(null = True)
  width = models.IntegerField(null = True)
  height = models.IntegerField(null = True)
  image_hash = models.CharField(max_length = 256, null = True)

  class Meta:
    abstract = True

  def set_image_properties(self):
    if not self.image:
      return False
    self.width = self.image.width
    self.height = self.image.height
    aspect_gcd = gcd(self.width, self.height)
    self.aspect_width = self.width/aspect_gcd
    self.aspect_height = self.height/aspect_gcd
    self.image.open('r')
    self.image_hash = hash_file(self.image.file)
    self.image.close()
    self.extension = os.path.splitext(self.image.path)[1]
    self.mime_type = mimetypes.types_map[self.extension]
    self.save()
    return True


  @property
  def http_image(self):
    if not self.image:
      if not self.populate():
        return Http404
    self.image.open('r')
    response = HttpResponse(content = self.image.file, mimetype = self.mime_type)
    
    return response


class NounImageExternal(NounImage):
  url = models.URLField(verify_exists = False)

  def populate(self):
    this_image = get_file_from_url(self.url)
    if this_image:
      self.image = File(this_image)
      self.save()
      if self.set_image_properties():
        return True
    return False

  @property
  def static(self, size = None):
    if not self.image:
      if not self.populate():
        return False
    this_static_noun, created = NounStatic.objects.get_or_create(parent = self, text = self.text, sfw = self.sfw)
    x = this_static_noun.parent
    if not created:
      return this_static_noun
    dst_file = tempfile.NamedTemporaryFile(suffix = self.extension)

    # Handle resizing if needed
    if size:
      self.image.open('r')
      src_img = Image.open(self.image.file, 'r')
      self.image.close()
      new_image = src_img.resize(size)
      new_image.save(dst_file)
    else:
      self.image.open('r')
      shutil.copyfileobj(self.image.file, dst_file)
      self.image.close()

    this_static_noun.image = File(dst_file)
    this_static_noun.save()
    if this_static_noun.set_image_properties():
      return this_static_noun
    return False
    

class NounStatic(NounImage):
  parent = models.ForeignKey(NounImageExternal, unique = True)

class Search(TimeStampable):
  last_searched = models.DateTimeField(null = True)
  has_results = models.NullBooleanField(default = None)
  query = models.SlugField()
  base = models.BooleanField(default = False)

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
  result_count = models.IntegerField(default = 0)
  page = models.IntegerField(default = 0)
  page_size = models.IntegerField(default = 8)
  imgsz = models.CharField(max_length = 10, default = '')
  restrict = models.CharField(max_length = 32, default = '')
  filetype = models.CharField(max_length = 10, default = '')
  rights = models.CharField(max_length = 32, default = '')
  site = models.CharField(max_length = 100, default = '')

  @property
  def params(self):
    params = {}
    params['v'] = '1.0'
    if API_KEY:
      params['key'] = API_KEY
    params['q'] = self.query
    params['rsz'] = self.page_size
    if self.result_count > self.page * self.page_size:
      params['start'] = self.page * self.page_size
    params['imgsz'] = self.imgsz
    params['restrict'] = self.restrict
    params['as_filetype'] = self.filetype
    params['as_rights'] = self.rights
    params['as_sitesearch'] = self.site

    return urllib.urlencode(params)

  @property
  def next_permuation(self):
    next_search, created = SearchGoogle.objects.get_or_create(
      query = self.query,
      page = self.page + 1)
    return next_search

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
    self.has_results = bool(len(data['responseData']['results']))
    if not self.has_results:
      self.save()
      return False

    self.result_count = int(data['responseData']['cursor']['estimatedResultCount'])
    self.last_searched = datatime.datetime.now()
    self.save()

    # Iterate through the results and create blank image objects.
    for result in data['responseData']['results']:
      new_image = NounImageExternal.objects.create(
        url = result['url'],
        width = result['width'],
        height = result['height'],
        text = self.query,
        )

    return True
