import urllib2
import urllib
import simplejson

from django.shortcuts import render_to_response
from django.template import RequestContext

from django.http import HttpResponse

from placenoun.pn.models import NounStatic, NounImageExternal, SearchGoogle

def index(request):
  template = 'index.html'
  data = {}

  context = RequestContext(request)
  return render_to_response(template, data, context)

def noun_static(request, noun, width, height):
  noun_query = NounStatic.objects.filter(text = noun, width = width, height = height)
  if noun_query.exists():
    this_image = noun_query.get()
    return this_image.http_image

  noun_query = NounImageExternal.objects.filter(text = noun, width = width, height = height)
  if noun_query.exists():
    this_image = noun_query.get().static
    return this_image.http_image

def noun(request, noun, width = None, height = None):
  if not NounImageExternal.objects.filter(text = noun).exists():
    new_search = SearchGoogle()
    new_search.query = noun
    if not new_search.shazam():
      context = RequestContext(request)
      return render_to_response(template, data, context)
  this_image = NounImageExternal.objects.filter(text = noun)[0]

  return this_image.http_image



def search(request, noun):
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
