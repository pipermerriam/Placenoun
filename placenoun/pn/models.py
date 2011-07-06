import urllib
import urllib2
import os
import simplejson
import datetime
import mimetypes
import tempfile
import shutil

from decimal import Decimal
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
from django.db.models.signals import post_init

from placenoun.behaviors.models import *
from placenoun.fileutilities.main import *

API_KEY = settings.API_KEY

def upload_path(instance, filename):
  return '/'.join([instance.slug[:2].strip('.-_'), instance.slug, datetime.datetime.now().strftime('%Y/%m/%d'), os.path.basename(filename)])

class NounBase(TimeStampable):
  noun = models.CharField(max_length = 100)
  nsfw = models.NullBooleanField(default = None)

  image = models.ImageField(upload_to=upload_path, null = True)
  extension = models.CharField(max_length = 32, null = True)
  mimetype = models.CharField(max_length = 32, null = True)
  aspect = models.DecimalField(max_digits = 19, decimal_places=10, null = True)
  width = models.IntegerField(null = True)
  height = models.IntegerField(null = True)
  image_hash = models.CharField(max_length = 256, null = True)

  class Meta:
    abstract = True

  @property
  def slug(self):
    return slugify(self.noun.replace('+',' '))

  def set_image_properties(self):
    if not self.image:
      return False
    self.image.open('r')
    image_hash = hash_file(self.image.file)
    self.image.close()
    if not image_hash == None and type(self).objects.filter(image_hash = image_hash).exists():
      self.delete()
      return False
    self.image_hash = image_hash

    self.extension = os.path.splitext(self.image.path)[1]
    if self.extension.lower() == '.gif':
      self.image.open('r')
      pil_image = Image.open(self.image.file)
      try:
        pil_image.seek(1)
      except EOFError:
        self.image.close()
        pass
      else:
        self.delete()
        return False
    self.mimetype = mimetypes.types_map[self.extension]

    self.width = self.image.width
    self.height = self.image.height
    self.aspect = Decimal(self.width)/Decimal(self.height)

    self.save()
    return True


  @property
  def http_image(self):
    self.image.open('r')
    response = HttpResponse(content = self.image.file, mimetype = self.mimetype)
    
    return response

  def http_image_resized(self, size):
    self.image.open('r')
    temp_image = Image.open(self.image.file).resize(size)

    response = HttpResponse(mimetype = self.mimetype)
    temp_image.save(response, self.extension.strip('.').capitalize())

    return response

class NounExternal(NounBase):
  url = models.URLField(verify_exists = False)
  available = models.BooleanField(default = True)

  def __unicode__(self):
    return "<NounExternal: %s>"%(self.id)

  def populate(self):
    this_image = get_file_from_url(self.url)
    if this_image:
      self.image = File(this_image)
      self.save()
      return self.set_image_properties()
    self.delete()
    return False

  def to_static(self, size = None):
    this_static, created = NounStatic.objects.get_or_create(
      parent = self, 
      noun = self.noun, 
      nsfw = self.nsfw,
      extension = self.extension,
      mimetype = self.mimetype,
      aspect = self.aspect)
    if not created:
      return this_static
    dst_file = tempfile.NamedTemporaryFile(suffix = self.extension)

    # Handle resizing if needed
    if size:
      self.image.open('r')
      src_img = Image.open(self.image.file, 'r')
      new_image = src_img.resize(size)
      self.image.close()
      new_image.save(dst_file)
    else:
      self.image.open('r')
      shutil.copyfileobj(self.image.file, dst_file)
      self.image.close()

    this_static.image = File(dst_file)
    this_static.save()
    if this_static.set_image_properties():
      self.available = False
      self.save()
      return this_static
    return False

def populate_image(sender, instance, **kwargs):
  if instance.url and not instance.image and instance.id:
    instance.populate()

post_init.connect(populate_image, NounExternal)

class NounStatic(NounBase):
  parent = models.ForeignKey(NounExternal, unique = True)

  def __unicode__(self):
    return "<NounStatic: id($s) : noun(%s) : for %sx%s>"%(self.id, self.noun, self.width, self.height) 

class Search(TimeStampable):
  last_searched = models.DateTimeField(null = True)
  has_results = models.NullBooleanField(default = None)
  query = models.CharField(max_length = 100)

  class Meta:
    abstract = True

class SearchGoogle(Search):
  response_code = models.CharField(max_length = 100)
  result_count = models.BigIntegerField(default = 0)
  page = models.IntegerField(default = 0)
  page_size = models.IntegerField(default = 4)
  imgsz = models.CharField(max_length = 10, default = '')
  restrict = models.CharField(max_length = 32, default = '')
  filetype = models.CharField(max_length = 10, default = '')
  rights = models.CharField(max_length = 32, default = '')
  site = models.CharField(max_length = 100, default = '')

  def __unicode__(self):
    return "<SearchGoogle: %s : page(%s)>"%(self.query, self.page)

  @property
  def params(self):
    params = {}
    params['v'] = '1.0'
    if API_KEY:
      params['key'] = API_KEY
    params['q'] = self.query
    #params['rsz'] = self.page_size
    params['start'] = self.page * self.page_size
    #params['imgsz'] = self.imgsz
    #params['restrict'] = self.restrict
    #params['as_filetype'] = self.filetype
    #params['as_rights'] = self.rights
    #params['as_sitesearch'] = self.site

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
    self.has_results = bool(len(data['responseData']['results']))
    if not self.has_results:
      self.save()
      return False

    self.result_count = int(data['responseData']['cursor']['estimatedResultCount'])
    self.last_searched = datetime.datetime.now()
    self.save()


    # Iterate through the results and create blank image objects.
    for result in data['responseData']['results']:
      new_image, created = NounExternal.objects.get_or_create(
        url = result['url'],
        width = result['width'],
        height = result['height'],
        noun = self.query,
        )
      if created:
        new_image.aspect = Decimal(result['width'])/Decimal(result['height'])

    return True
