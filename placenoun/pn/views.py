import urllib2
import urllib
import simplejson

from decimal import Decimal, getcontext

from django.shortcuts import render_to_response
from django.template import RequestContext

from placenoun.pn.models import NounStatic, NounExternal, SearchGoogle, SearchBing

def index(request):
  template = 'index.html'
  data = {}

  context = RequestContext(request)
  return render_to_response(template, data, context)

def noun_static(request, noun, width, height):
  width = min(2048, int(width))
  height = min(2048, int(height))

  noun_query = NounStatic.objects.filter(noun = noun, width = width, height = height)
  if noun_query.exists():
    this_image = noun_query.get()
    return this_image.http_image

  noun_query = NounExternal.objects.filter(available = True, noun = noun, width = width, height = height)
  q1 = noun_query
  if noun_query.exists():
    this_image = noun_query[:1].get().to_static()
    if this_image:
      return this_image.http_image

  aspect = Decimal(width)/Decimal(height)
  num_part = str(aspect).split('.')[0]
  getcontext().prec = len(num_part) + 10
  aspect = Decimal(width)/Decimal(height)
  noun_query = NounExternal.objects.filter(available = True, noun= noun, aspect = aspect, width__gte = width, height__gte = height)
  q2 = noun_query
  if noun_query.exists():
    this_image = noun_query[:1].get().to_static(size=(width, height))
    if this_image:
      return this_image.http_image


  # At this point we couldn't find a suitable match, so... we'll serve
  # up a best fit result but it won't be perminant

  if not SearchBing.do_next_search(noun):
    SearchGoogle.do_next_search(noun)

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
    if not this_image.id:
      continue
    return this_image.http_image_resized(size=(width, height))

def noun(request, noun):
  noun_query = NounExternal.objects.filter(noun = noun)
  if noun_query.exists():
    if noun_query.count() > 100:
      this_image = noun_query.order_by('?')[:1].get()
      if this_image.id:
        return this_image.http_image

  if not SearchBing.do_next_search(noun):
    SearchGoogle.do_next_search(noun)

  while True:
    noun_query = NounExternal.objects.filter(noun = noun)
    if noun_query.exists():
      this_image = noun_query.order_by('?')[:1].get()
      if not this_image.id:
        continue
      return this_image.http_image
