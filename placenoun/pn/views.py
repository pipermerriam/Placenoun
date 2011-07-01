import urllib2
import urllib
import simplejson

from django.conf.settings import API_KEY
from django.shortcuts import render_to_response
from django.template import RequestContext

from django.http import HttpResponse

from placenoun.pn.models import Noun, Image

def index(request)
  template = 'index.html'
  data = {}

  context = RequestContext(request)
  return render_to_response(template, data, context)

def noun(request, noun):
  this_noun, created = Noun.objects.get_or_create(text = noun)
  
  if not Image.objects.filter(noun = this_noun).exists():
    pass
  
  
  if not

def search(request, noun)
  params = {}
  params['v'] = '1.0'
  if API_KEY:
    params['key'] = api_key
  params['q'] = noun
  
  params['imgsz'] = 'huge'

  url = ('https://ajax.googleapis.com/ajax/services/search/images?' +
    urllib.urlencode(params))

  request = urllib2.Request(url, None, {'Referer': 'http://www.placenoun.com/'})
  response = urllib2.urlopen(request)
  
  data = simplejson.load(response)
  src = data['responseData']['results'][0]['url']

  return HttpResponse('<img src="%s">'%src)
