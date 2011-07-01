import urllib2
import urllib
import simplejson

api_key = 'ABQIAAAA68yIT3RKFrmKuV92AOKx2BQUh8Ai2s-HBkknHsM8uklop4yh-BTlR80Tvduat_GWA5UjBGRYrgGyKA'

from django.http import HttpResponse

def get_noun(request, noun):
  params = {}
  #params['key'] = api_key
  params['q'] = noun

  url = ('https://ajax.googleapis.com/ajax/services/search/images?' +
    urllib.urlencode(params))

  request = urllib2.Request(url, None, {'Referer': /* Enter the URL of your site here */})
  response = urllib2.urlopen(request)
  
  data = simplejson.load(response)
  src = data['responseData']['results'][0]['url']

  return HttpResponse('<img srs="%s">'%src)
