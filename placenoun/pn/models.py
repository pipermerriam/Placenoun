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

GOOGLE_API_KEY = settings.GOOGLE_API_KEY
BING_API_KEY = settings.BING_API_KEY

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

    self.extension = os.path.splitext(self.image.path)[1].lower()
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
      try:
        self.image.open('r')
        pil_image = Image.open(self.image.file)
        pil_image.verify()
        self.image.close()
      except IOError:
        pass
      else:
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

  @classmethod
  def do_next_search(cls, noun):
    search_query = cls.objects.filter(query = noun)
    if search_query.exists():
      if search_query.filter(last_searched = None).exists():
        this_search = search_query.filter(last_searched = None).order_by('created_at')[:1].get()
      else:
        latest_search = search_query.order_by('-created_at')[:1].get()
        this_search = latest_search.next
    else:
      this_search = cls.objects.create(query = noun)
    if this_search:
      return this_search.shazam()
    return False

class SearchGoogle(Search):
  response_code = models.CharField(max_length = 100)
  result_count = models.BigIntegerField(default = 0)
  page = models.IntegerField(default = -1)
  page_size = models.IntegerField(default = 8)
  imgsz = models.CharField(max_length = 10, default = '')
  restrict = models.CharField(max_length = 32, default = '')
  filetype = models.CharField(max_length = 10, default = '')
  rights = models.CharField(max_length = 32, default = '')
  site = models.CharField(max_length = 100, default = '')

  def __unicode__(self):
    return "<SearchGoogle: %s : page(%s)>"%(self.query, self.page)

  @property
  def next(self):
    PAGES = range(0, 64, self.page_size)
    FILE_TYPES = ['', 'jpg', 'png', 'gif', 'bmp']
    RIGHTS = ['', 'cc_publicdomain', 'cc_attribute', 'cc_sharealike', 'cc_noncommercial', 'cc_nonderived']
    IMAGE_SIZE = ['', 'huge', 'xxlarge', 'medium', 'icon']
    RESTRICT = ['', 'cc_attribute']

    page = self.page
    page_size = self.page_size
    imgsz = self.imgsz
    restrict = self.restrict
    rights = self.rights
    filetype = self.filetype

    if (page+1)*page_size < 64:
      page = page + 1
    elif FILE_TYPES.index(filetype) < len(FILE_TYPES) - 1:
      page = 1
      filetype = FILE_TYPES[FILE_TYPES.index(filetype)+1]
    elif RIGHTS.index(rights) < len(RIGHTS) - 1:
      page = 1
      filetype = ''
      rights = RIGHTS[RIGHTS.index(rights)+1]
    elif IMAGE_SIZE.index(imgsz) < len(IMAGE_SIZE) - 1:
      page = 1
      filetype = ''
      rights = ''
      imgsz = IMAGE_SIZE[IMAGE_SIZE.index(imgsz)+1]
    elif RESTRICT.index(restrict) < len(RESTRICT) - 1:
      page = 1
      filetype = ''
      rights = ''
      imgsz = ''
      restrict = RESTRICT[RESTRICT.index(restrict)+1]
    else:
      return False

    return SearchGoogle.objects.get_or_create(
      query = self.query,
      page = page,
      filetype = filetype,
      rights = rights,
      imgsz = imgsz,
      restrict = restrict)[0]


  @property
  def params(self):
    params = {}
    params['v'] = '1.0'
    if GOOGLE_API_KEY:
      params['key'] = GOOGLE_API_KEY
    params['q'] = self.query
    #params['rsz'] = self.page_size
    params['start'] = self.page * self.page_size
    if self.imgsz:
      params['imgsz'] = self.imgsz
    if self.restrict:
      params['restrict'] = self.restrict
    if self.filetype:
      params['as_filetype'] = self.filetype
    if self.rights:
      params['as_rights'] = self.rights
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

    self.last_searched = datetime.datetime.now()

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

class SearchBing(Search):
  result_count = models.BigIntegerField(default = -1)
  page = models.IntegerField(default = 0)
  page_size = models.IntegerField(default = 10)

  def __unicode__(self):
    return "<SearchBing: %s : page(%s)>"%(self.query, self.page)

  @property
  def next(self):
    page = self.page
    page_size = self.page_size

    if (page +1)*page_size < 1000:
      page += 1
    else:
      return False

    return SearchBing.objects.get_or_create(
      page = page,
      page_size = page_size,
      query = self.query
      )[0]

  @property
  def params(self):
    params = {}
    params['Sources'] = 'Image'
    params['Version'] = '2.0'
    params['AppId'] = BING_API_KEY
    params['Query'] = self.query
    params['Image.Count'] = self.page_size
    params['Image.Offset'] = self.page * self.page_size

    return urllib.urlencode(params)

  def shazam(self, raw = False):
    url = ('http://api.search.live.net/json.aspx?' + self.params)
  
    request = urllib2.Request(url, None, {'Referer': 'http://www.placenoun.com/'})
    response = urllib2.urlopen(request)
    
    data = simplejson.load(response)

    # Allows the return of the raw google json data
    if raw:
      return data

    self.last_searched = datetime.datetime.now()

    self.result_count = int(data['SearchResponse']['Image']['Total'])
    if not self.result_count:
      self.save()
      return False

    # If there are zero results for the search. return False.
    self.has_results = 'Results' in data['SearchResponse']['Image']
    if not self.has_results:
      self.save()
      return False

    self.save()

    # Iterate through the results and create blank image objects.
    for result in data['SearchResponse']['Image']['Results']:
      new_image, created = NounExternal.objects.get_or_create(
        url = result['MediaUrl'],
        width = result['Width'],
        height = result['Height'],
        noun = self.query,
        )
      if created:
        new_image.aspect = Decimal(result['Width'])/Decimal(result['Height'])

    return True
