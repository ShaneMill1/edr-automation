
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



import argparse
from collections import OrderedDict
import datetime
import model_download_ingest
import glob
import json
import os
import numpy as np
import pandas as pd
import re
import shutil
import xarray as xr

def download_data(model,cycle,ingest_path):
   #downloads model data into ./data_ingest directory
   ds=model_download_ingest.model_ingest(cycle,model,ingest_path)


def create_all_grb(model,cycle,ingest_path):
   #concatenates the grib files together for one model grib file containing 0z/06z/12z/18z runs
   path=sorted(glob.glob(ingest_path+'/'+model+'/'+cycle+'/*'))
   if not os.path.exists(ingest_path+'/collections/'+model+'/'+cycle):
      os.makedirs(ingest_path+'/collections/'+model+'/'+cycle,exist_ok=True)
   model_dir=ingest_path+'/collections/'+model+'/'+cycle+'/'
   if os.path.exists(model_dir+cycle+'_'+model+'.grb'):
         os.remove(model_dir+cycle+'_'+model+'.grb')
   all_grb=open(model_dir+cycle+'_'+model+'.grb','wb')
   for f in path:
      shutil.copyfileobj(open(f,'rb'),all_grb)
   all_grb.close()


def create_model_csv(model,cycle,ingest_path):
   #opens concatenated grib as an xarray dataset using pynio. 
   #grabs the unique parameter ID, long name, level type, and dimensions
   #creates a record of each individual ID and its associated dimensions
   #also creates a csv that will act as a map between the dimension names and their values.
   #See GFS.csv and GFS_dim_info.csv as examples.
   model_dir=ingest_path+'/collections/'+model+'/'+cycle+'/'
   path=model_dir+cycle+'_'+model+'.grb'
   ds=xr.open_dataset(path,engine='pynio')
   grid_type_list=list()
   long_name_list=list()
   units_list=list()
   dim_dict_list=list()
   overall_list=list()
   for d in ds.data_vars:
      if hasattr(ds.data_vars[d], 'long_name') and hasattr(ds.data_vars[d], 'grid_type') and hasattr(ds.data_vars[d], 'units') and hasattr(ds.data_vars[d], 'dims'):
         grid_type_list.append(ds.data_vars[d].grid_type)
         long_name_list.append(ds.data_vars[d].long_name)
         units_list.append(ds.data_vars[d].units)
         dim_dict={key:[] for key in ds.data_vars[d].dims}
         for f in ds.data_vars[d].dims:
            ds_vars=getattr(ds.data_vars[d],f)
            #dim_dict[f].append(ds_vars.values)
            dim_dict[f].append(f)
         dim_dict.update({'id': ds.data_vars[d]._name})
         dim_dict.update({'long_name': ds.data_vars[d].long_name})
         dim_dict.update({'level_type': ds.data_vars[d].level_type})
         overall_list.append(dim_dict)
   df=pd.DataFrame.from_dict(overall_list)
   cols=df.columns.tolist()
   cols.insert(0,cols.pop(cols.index('id')))
   cols.insert(1,cols.pop(cols.index('long_name')))
   cols.insert(2,cols.pop(cols.index('level_type')))
   df=df.reindex(columns=cols)
   df.to_csv(model_dir+cycle+'_'+model+'.csv', sep=',', na_rep=' ', index=True)
   dim_info_list=list()
   dim_info_dict={key:[] for key in ds.dims}
   initial_time=ds[dim_dict['id']].initial_time
   initial_time=initial_time.replace('(','')
   initial_time=initial_time.replace(')','')
   initial_time=initial_time.replace('/','-')
   month=initial_time[0:2]
   day=initial_time[3:5]
   year=initial_time[6:10]
   time=initial_time[11:16]
   initial_time=np.datetime64(year+'-'+month+'-'+day+' '+time)
   for e in ds.dims:
      attr=getattr(ds,e)
      if 'forecast_time' in e:
         td_values=attr.values
         valid_time=[]
         for d in td_values:
            t=initial_time+d
            t=str(t)
            t=t[:-10]
            valid_time.append(t)
         attr.values=valid_time
      dim_info_dict.update({e: attr.values})
      dim_info_list.append(dim_info_dict)
   ef=pd.DataFrame.from_dict(dim_info_list)
   ef = ef.iloc[0]
   ef.to_csv(model_dir+cycle+'_'+model+'_dim_info.csv', sep=',', na_rep=' ', index=True) 
   return 


def group_parameters(model,cycle,ingest_path):
   #This will use the GFS.csv to group together parameters that have the same exact dimensions.
   model_dir=ingest_path+'/collections/'+model+'/'+cycle+'/'
   csv=cycle+'_'+model+'.csv'
   element_list=list()
   element_all=list()
   df=pd.read_csv(model_dir+csv)
   lookup_df=df[['id','long_name','level_type']]  
   #when looking at the groupby columns, please look at the "col" list or you may be misled
   col=list(df.columns)
   ef=df.groupby(col[3:])['id'].apply(list).reset_index(name='parameters')
   ef['long_name']=ef['parameters']
   ln_lookup=pd.Series(lookup_df.long_name.values,index=lookup_df.id).to_dict()
   ef=ef.assign(long_name=[[ln_lookup[k] for k in row if ln_lookup.get(k)] for row in ef.long_name])
   ef.to_csv(model_dir+csv[:-4]+'_grouping.csv', sep=',', index=False)
   return


def create_collections(model,cycle,ingest_path):
   #this creates the end result in csv and json format where we have each "collection" and the associated parameter IDs and additional 
   #dimension info.
   model_dir=ingest_path+'/collections/'+model+'/'+cycle+'/'
   group_file=cycle+'_'+model+'_grouping.csv'
   dim_file=cycle+'_'+model+'_dim_info.csv'
   df=pd.read_csv(model_dir+group_file)
   dim_cols=['dim_name','dim_val']
   dim_df=pd.read_csv(model_dir+dim_file,names=dim_cols)
   dim_name=dim_df['dim_name']
   #had to add the iloc for docker environment... comment out if not in docker
   dim_name=dim_name.iloc[1:]
   dim_df['dim_val']=dim_df['dim_val'].str.replace('\n','')
   dim_df['dim_val']=dim_df['dim_val'].str.replace('[','')
   dim_df['dim_val']=dim_df['dim_val'].str.replace(']','')
   #dim_df['dim_val']=dim_df['dim_val'].str.replace('.','')
   dim_df['dim_val']=dim_df['dim_val'].str.split()
   dim_value=dim_df['dim_val']
   dim_lookup=pd.Series(dim_df.dim_val.values,index=dim_df.dim_name).to_dict()
   df_2=pd.read_csv(model_dir+group_file)
   for d in dim_name:
      df_2[d]=df_2[d].astype('str')
      df_2[d]=df_2[d].str.replace("]","")
      df_2[d]=df_2[d].str.replace("[","")
      df_2[d]=df_2[d].str.replace("'","")
      df_2[d]=df_2[d].str.replace("'","")
      df_2[d]=df_2[d].astype('str')
      df_2[d]=df_2[d].map(dim_lookup)
   dval_df=df_2[dim_name]
   cols=list(df.columns) 
   cols.insert(0, cols.pop(cols.index('parameters')))
   cols.insert(1, cols.pop(cols.index('long_name')))
   cols.insert(2, cols.pop(cols.index('level_type')))
   df=df.reindex(columns=cols)
   df['dimensions']=df[cols[3:]].apply(lambda row: ','.join(row.values.astype(str)), axis=1)
   cols=list(df.columns)
   cols.insert(3, cols.pop(cols.index('dimensions')))
   df=df.reindex(columns=cols)
   df = df[['parameters','long_name','level_type','dimensions']]
   df['dimensions']=df['dimensions'].str.replace(' ,','')
   df['dimensions']=df['dimensions'].str.replace(', ','')
   df['dimensions']=df['dimensions'].str.replace("'",'')
   df['dimensions']=df['dimensions'].str.replace(']','')
   df['dimensions']=df['dimensions'].str.replace('[','')
   df['parameters']=df['parameters'].str.replace(']','')
   df['parameters']=df['parameters'].str.replace('[','')
   df['parameters']=df['parameters'].str.replace("'",'')
   df['long_name']=df['long_name'].str.replace("'",'')
   df['long_name']=df['long_name'].str.replace(']','')
   df['long_name']=df['long_name'].str.replace('[','') 
   df['collection_name']=df['dimensions'].str.replace(',','_')
   df['parameters']=df.parameters.map(lambda x: [i.strip() for i in x.split(',')])
   df['dimensions']=df.dimensions.map(lambda x: [i.strip() for i in x.split(',')])
   df['long_name']=df.long_name.map(lambda x: [i.strip() for i in x.split(',')])
   df['level_type']=df.level_type.map(lambda x: [i.strip() for i in x.split(',')])
   df['level_type']=df.level_type.astype(str)
   df['level_type']=df['level_type'].str.replace(']','')
   df['level_type']=df['level_type'].str.replace('[','')
   df['level_type']=df['level_type'].str.replace('(','')
   df['level_type']=df['level_type'].str.replace(')','')
   df['level_type']=df['level_type'].str.replace(' ','_')
   df['level_type']=df['level_type'].str.replace("'","")
   df['collection_name']=model+'_'+df['collection_name']+'_'+df['level_type']
   print(df['collection_name'])
   df['dimension_count']=df.dimensions.apply(len)
   df=pd.concat([df,dval_df],axis=1)
   df=df.sort_values(by=['dimension_count'])
   cols=list(df.columns)
   cols.insert(0, cols.pop(cols.index('collection_name')))
   cols.insert(1, cols.pop(cols.index('parameters')))
   cols.insert(2, cols.pop(cols.index('long_name')))
   cols.insert(3, cols.pop(cols.index('level_type')))
   cols.insert(4, cols.pop(cols.index('dimension_count')))
   cols.insert(5, cols.pop(cols.index('dimensions')))
   df.to_csv(model_dir+group_file[:-13]+'_collection.csv', sep=',', index=False)
   j=df.to_json(orient='records')
   with open(model_dir+group_file[:-13]+'_collection.json','w') as f: 
      res = json.loads(j,object_hook=remove_nulls)
      json.dump(res,f,indent=2, sort_keys=True)
   return 


def remove_nulls(d):
   return {k: v for k, v in d.items() if v is not None}


def convert_to_zarr(model,cycle,ingest_path):
   ingest_path=ingest_path+'/collections/'+model+'/'+cycle
   col_json_file=ingest_path+'/'+cycle+'_'+model+'_collection.json'
   ds_f=ingest_path+'/'+cycle+'_'+model+'.grb'
   with open(col_json_file) as json_file:
      col_json = json.load(json_file)
   ds=xr.open_dataset(ds_f,engine='pynio')
   for c in col_json:
      param=c['parameters']
      param=[s.replace("'","") for s in param]
      col_ds=ds[param]
      col_ds.to_zarr(ingest_path+'/zarr/'+c['collection_name'],mode='w')
      print(c['collection_name']+' converted to zarr')
   return

if __name__ == "__main__":
   
   parser = argparse.ArgumentParser(description='Ingest Model and create collections')
   parser.add_argument('model', type = str, help = 'Enter the model (ex: GFS)')
   parser.add_argument('cycle', type = str, help = 'Enter the model cycle (ex: 12z)')
   parser.add_argument('ingest_path', type = str, help = 'Enter the directory where you want the data to be stored')
   args=parser.parse_args()
   model=args.model
   cycle=args.cycle
   ingest_path=args.ingest_path
   
   download_data(model,cycle,ingest_path)
   create_all_grb(model,cycle,ingest_path)
   create_model_csv(model,cycle,ingest_path)
   group_parameters(model,cycle,ingest_path)
   create_collections(model,cycle,ingest_path)
   convert_to_zarr(model,cycle,ingest_path)
