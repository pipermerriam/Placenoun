import urllib
import urllib2
import simplejson
import datetime
import tempfile

from django.core.files import File
from django.conf import settings
from django.db import models

from placenoun.behaviors.models import * 

API_KEY = settings.API_KEY
IMAGE_SIZE_CHOICES = ('icon', 'small', 'medium', 'large', 'xlarge', 'xxlarge', 'huge')

# Create your models here.
class Noun(TimeStampable):
  text = models.CharField(max_length = 100)

class Search(TimeStampable):
  noun = models.ForeignKey(Noun)
  last_searched = models.DateTimeField()
  response_code = models.CharField(max_length = 100)
  results = models.IntegerField()
  query = models.CharField(max_length = 64)
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

  def doit(self, raw = False):
    url = ('https://ajax.googleapis.com/ajax/services/search/images?' + self.params)
  
    request = urllib2.Request(url, None, {'Referer': 'http://www.placenoun.com/'})
    response = urllib2.urlopen(request)
    
    data = simplejson.load(response)
    if raw:
      return data

    self.response = data['responseStatus']
    if not self.response == 200:
      self.save()
      return False

    self.results = len(data['responseData']['results'])
    if not self.results:
      self.save()
      return False

    if not self.noun:
      self.noun, created = Noun.objects.get_or_create(text = self.query)

    for result in data['responseData']['results']:
      img = urllib2.open(result['url'])
      temp = tempfile.NameTemporaryFile(suffix = '.' + img.url.split('.').pop())

      while True:
        buf = img.read(1024)
        if buf:
          temp.write(buf)
          continue
        break

      img_hash = hash_file(temp)

      if Image.objects.filter(image_hash = img_hash).exists():
        continue

      new_image = Image.objects.create(
        noun = self.noun,
        search = self,
        image = File(temp),
        width = result['width'],
        height = result['height'],
        image_hash = img_hash,
        image_id = result['imageId'],
        url = result['url'],
        unescapedUrl = result['unescapedUrl']
        )

    return True

def get_image_from_url(url):
  url_response = urllib2.urlopen(url)
  temp = tempfile.NamedTemporaryFile(suffix = '.' + url_response.url.split('.').pop())

  while True:
    buf = url_response.read(1024)
    if buf:
      temp.write(buf)
      continue
    break
  return temp
  
def hash_file(file):
  file.seek(0)
  hasher = hashlib.sha256()
  while True:
    buf = file.read(1024)
    if buf:
      hasher.update(buf)
      continue
    break
  return hasher.hexdigest()


class Image(TimeStampable):
  noun = models.ForeignKey(Noun)
  search = models.ForeignKey(Search)
  image = models.ImageField()
  width = models.IntegerField()
  height = models.IntegerField()
  image_hash = models.CharField(max_length = 64)
  image_id = models.CharField(max_length = 20)
  url = models.URLField()
  unescapedUrl = models.URLField()

  last_seen = models.DateTimeField()
