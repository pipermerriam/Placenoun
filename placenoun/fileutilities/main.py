# File Utilities
import urllib2
import hashlib
import os

# Takes a url and returns a file object
def get_file_from_url(url):
  import tempfile

  url_response = urllib2.urlopen(url)
  extension = os.path.splitext(url)[1]
  if extension == '.jpg':
    extension = '.jpeg'

  temp = tempfile.NamedTemporaryFile(suffix = extension )

  while True:
    buf = url_response.read(1024)
    if buf:
      temp.write(buf)
      continue
    break
  return temp

# Takes a file object and returns an SHA256 hash of it.
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
