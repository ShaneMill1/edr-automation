import requests
from bs4 import BeautifulSoup
import datetime

def info(model,cycle):
   model=model.lower()
   url='https://mag.ncep.noaa.gov/data/'+model+'/'
   print(url)
   r = requests.get(url)
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
   info('gfs','00z')



