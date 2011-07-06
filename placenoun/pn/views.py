import urllib2
import urllib
import simplejson

from decimal import Decimal

from django.shortcuts import render_to_response
from django.template import RequestContext

from placenoun.pn.models import NounStatic, NounExternal, SearchGoogle

def index(request):
  template = 'index.html'
  data = {}

  context = RequestContext(request)
  return render_to_response(template, data, context)

def noun_static(request, noun, width, height):
  width = int(width)
  height = int(height)
  noun_query = NounStatic.objects.filter(noun = noun, width = width, height = height)
  if noun_query.exists():
    this_image = noun_query.get()
    return this_image.http_image

  noun_query = NounExternal.objects.filter(available = True, noun = noun, width = width, height = height)
  if noun_query.exists():
    this_image = noun_query.get().to_static()
    if this_image:
      return this_image.http_image

  aspect = Decimal(width)/Decimal(height)
  noun_query = NounExternal.objects.filter(available = True, noun= noun, aspect = aspect, width__gte = width, height__gte = height)
  if noun_query.exists():
    this_image = noun_query.get().to_static(size=(width, height))
    if this_image:
      return this_image.http_image

  # At this point we couldn't find a suitable match, so... we'll serve
  # up a best fit result but it won't be perminant

  search_query = SearchGoogle.objects.filter(query = noun)
  if search_query.exists():
    latest_search = search_query.order_by('-page')[0]
    if not latest_search.last_searched:
      this_search = latest_search
    else:
      this_search = SearchGoogle.objects.create(query = noun, page = latest_search.page + 1)
  else:
    this_search = SearchGoogle.objects.create(query = noun)
  this_search.shazam()

  radius = 1
  while True:
    noun_query = NounExternal.objects.filter(noun = noun).filter(
      width__lte = width + radius, height__lte = height + radius).filter(
      width__gte = width - radius, height__gte = height - radius)
    if not noun_query.exists():
      radius = radius*2
      continue
    noun_query = sorted(noun_query, key = lambda noun_obj: ( (width-noun_obj.width)**2 + (height-noun_obj.height)**2)**0.5 )
    this_image = noun_query[0]
    return this_image.http_image_resized(size=(width, height))

def noun(request, noun, width = None, height = None):
  noun_query = NounStatic.objects.filter(noun = noun)
  if noun_query.exists():
    this_image = noun_query.order_by('?')[0]
    return this_image.http_image

  search_query = SearchGoogle.objects.filter(query = noun)
  if search_query.exists():
    latest_search = search_query.order_by('-page')[0]
    if not latest_search.last_searched:
      this_search = latest_search
    else:
      this_search = SearchGoogle.objects.create(query = noun, page = latest_search.page + 1)
  else:
    this_search = SearchGoogle.objects.create(query = noun)
  this_search.shazam()

  noun_query = NounExternal.objects.filter(noun = noun)
  if noun_query.exists():
    this_image = noun_query.order_by('?')[0]
    return this_image.http_image
