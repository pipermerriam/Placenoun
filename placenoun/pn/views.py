import random

from urllib import urlencode

from django.conf import settings
from django.http import Http404
from django.shortcuts import render_to_response
from django.template import RequestContext

try:
  from fractions import gcd
except ImportError:
  from placenoun.numberutilities.main import gcd

from placenoun.pn.models import NounStatic, NounExternal, SearchGoogle, SearchBing
from placenoun.ga.ga import track_page_view

MAX_IMAGE_WIDTH = settings.MAX_IMAGE_WIDTH
MAX_IMAGE_HEIGHT = settings.MAX_IMAGE_HEIGHT

def index(request):
  template = 'index.html'
  data = {}

  context = RequestContext(request)
  return render_to_response(template, data, context)

def detail(request, this_image):
  template = 'debug.html'
  data = {'image_source': this_image.image.url}

  context = RequestContext(request)
  return render_to_response(template, data, context, mimetype="application/xhtml+xml")

def get_by_id(request, id):
  id = int(id)
  this_image = NounExternal.objects.get(pk = id)
  if not this_image.image:
    this_image.populate()
  if not this_image.status < 30:
    return Http404
  return this_image.http_image

def noun_static(request, noun, width, height):
  noun = noun.lstrip('+').rstrip('+')
  width = min(MAX_IMAGE_WIDTH, int(width))
  height = min(MAX_IMAGE_HEIGHT, int(height))
  track_page_view(request)

  noun_query = NounStatic.objects.filter(noun = noun, width = width, height = height)[:1]
  if noun_query:
    this_image = noun_query.get()
    return this_image.http_image

  noun_query = NounExternal.objects.filter(noun = noun, width = width, height = height, status__lt = 20)
  if noun_query.exists():
    this_image = noun_query[0]
    if not this_image.image:
      this_image.populate()
    if this_image.status == 10:
      this_image = this_image.to_static()
      return this_image.http_image

  aspect = float(width)/height
  noun_query = NounExternal.objects.filter(noun= noun, width__gte = width, height__gte = height, aspect = aspect, status__lt = 20)
  if noun_query.exists():
    this_image = noun_query[0]
    if not this_image.image:
      this_image.populate()
    if this_image.status == 10:
      this_image = this_image.to_static(size=(width, height))
      return this_image.http_image


  # At this point we couldn't find a suitable match, so... we'll serve
  # up a best fit result but it won't be perminant

  random.choice([SearchBing, SearchGoogle]).do_next_search(noun)

  radius = 1
  search_max = 32
  slope = float(height)/width
  while True:
    noun_query = NounExternal.get_knn_window(noun, width, height, radius)
    if not noun_query.exists():
      radius = radius*2
      if radius > search_max:
        search_max = search_max*2
        if search_max > 2048:
          return Http404
        radius = 1
        random.choice([SearchBing, SearchGoogle]).do_next_search(noun)
      continue

    noun_query = sorted(noun_query, key = lambda noun_obj: noun_obj.compare(width, height) )
    noun_query.reverse()
    while noun_query:
      this_image = noun_query.pop()
      if not this_image.image:
        this_image.populate()
      if not this_image.image:
        continue
      ret = this_image.http_image_resized(size=(width, height))
      return this_image.http_image_resized(size=(width, height))

def noun(request, noun, debug = False):
  noun = noun.lstrip('+').rstrip('+')
  request.META['utmipn'] = ''
  request.META['utmdt'] = ''
  track_page_view(request)
  noun_query = NounExternal.objects.filter(noun = noun, status__lte = 30)
  if noun_query.exists():
    if noun_query.count() < 100:
      random.choice([SearchBing, SearchGoogle]).do_next_search(noun)
    this_image = NounExternal.get_random(noun, 30)
    if not this_image.image:
      this_image.populate()
    if this_image.image:
      if debug:
        return detail(request, this_image)
      return this_image.http_image

  random.choice([SearchBing, SearchGoogle]).do_next_search(noun)

  while True:
    noun_query = NounExternal.objects.filter(noun = noun, status__lte = 30)
    if noun_query.exists():
      this_image = NounExternal.get_random(noun, 30)
      if not this_image.image:
        this_image.populate()
      if not this_image.image:
        continue
      if debug:
        return detail(request, this_image)
      return this_image.http_image
    else:
      random.choice([SearchBing, SearchGoogle]).do_next_search(noun)
