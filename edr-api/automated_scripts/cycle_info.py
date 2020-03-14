# =================================================================
#
# Authors: Shane Mill <shane.mill@noaa.gov>
#
# Copyright (c) 2019 Shane Mill - National Weather Service
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND   
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.      
#
# =================================================================


import requests
from bs4 import BeautifulSoup
import datetime

def info(model,cycle):
   model=model.lower()
   r = requests.get('https://mag.ncep.noaa.gov/data/'+model)
   soup = BeautifulSoup(r.text, 'html.parser')

   if cycle=='00z':
      time_z = soup.find_all('tr')[3].find_all('td')[1].text[:-6]
      time_z=datetime.datetime.strptime(time_z, '%d-%b-%Y').strftime('%Y%m%d')
   if cycle=='06z':
      time_z = soup.find_all('tr')[4].find_all('td')[1].text[:-6]
      time_z=datetime.datetime.strptime(time_z, '%d-%b-%Y').strftime('%Y%m%d')
   if cycle=='12z':
      time_z = soup.find_all('tr')[5].find_all('td')[1].text[:-6]
      time_z=datetime.datetime.strptime(time_z, '%d-%b-%Y').strftime('%Y%m%d')
   if cycle=='18z':
      time_z = soup.find_all('tr')[6].find_all('td')[1].text[:-6]
      time_z=datetime.datetime.strptime(time_z, '%d-%b-%Y').strftime('%Y%m%d')

   if model=='gfs':
      url_dir = 'https://nomads.ncep.noaa.gov/pub/data/nccf/com/'+model+'/prod/'+model+'.'+time_z+'/'+cycle[:-1]+'/'
      print(url_dir)
   if model=='nam':
      url_dir = 'https://nomads.ncep.noaa.gov/pub/data/nccf/com/'+model+'/prod/'+model+'.'+time_z+'/'
      print(url_dir)
   if model=='hrrr':
      url_dir = 'https://nomads.ncep.noaa.gov/pub/data/nccf/com/'+model+'/prod/'+model+'.'+time_z+'/conus/'
      print(url_dir)
   if model=='rap':
      url_dir = 'https://nomads.ncep.noaa.gov/pub/data/nccf/com/'+model+'/prod/'+model+'.'+time_z+'/'
      print(url_dir)
   return time_z, url_dir

if __name__ == "__main__":
   info('nam','00z')



