import urllib2
import urllib
import simplejson

api_key = 'ABQIAAAA68yIT3RKFrmKuV92AOKx2BQUh8Ai2s-HBkknHsM8uklop4yh-BTlR80Tvduat_GWA5UjBGRYrgGyKA'

from django.http import HttpResponse

def get_noun(request, noun):
  params = {}
  params['v'] = '1.0'
  #params['key'] = api_key
  params['q'] = noun

  url = ('https://ajax.googleapis.com/ajax/services/search/images?' +
    urllib.urlencode(params))

  request = urllib2.Request(url, None)
  response = urllib2.urlopen(request)
  
  data = simplejson.load(response)
  src = data['responseData']['results'][0]['url']

  return HttpResponse('<img src="%s">'%src)
