from WoW.formatters.jsonconv import json2html
from dicttoxml import dicttoxml
import yaml
import json
import glob
import copy
import WoW.isodatetime.parsers as parse
import WoW.isodatetime.dumpers as dump
from WoW import util
from WoW.provider.metadata import MetadataProvider
from WoW.cache_logic import collection_cache
from datetime import datetime, timedelta
import os
import pyproj


class FormatOutput(object):
    def __init__(self, config,link_path, met_ip=False):
        """
        Initialize object

        """
        self.result = None
        self.server = config['server']['url']
        self.link_path = link_path
        self.datasets = config['datasets']
        self.ndfd_config = None
        self.mp_ = MetadataProvider(config)
        self.met_ip = met_ip
        try:
           link_path_elements=self.link_path[0].split('/')
           ds_name=link_path_elements[2].split('_')
           self.ds_name=ds_name[0]+'_'+ds_name[1]
           self.automated_ds = config['datasets'][self.ds_name]['provider']['data_source']
           self.auto_cycle =  link_path_elements[3]
           model_string=link_path_elements[2].split('_')
           self.auto_model =  model_string[1]+'_'+model_string[2]
           
           self.auto_col_json = self.automated_ds +'/'+self.auto_model+'/'+self.auto_cycle+'/'+self.auto_cycle+'_'+self.auto_model+'_collection.json'
        except:
           pass


    def get_json(self, input):
        return json.dumps(input)

    def get_yaml(self, input):
        return yaml.dump(input)

    def get_xml(self, input):
        return dicttoxml(input, attr_type=False)

    def get_html(self, input):
        return json2html.convert(input)

    def create_links(self, nest):

        links = []
        if self.result is not None:
            links = self.result

        if nest:
            for p in self.link_path:
                links.append(self.link_template([], p))
        else:
            for p in self.link_path:
                links = self.link_template(copy.deepcopy(links), p)


        self.result = links
        return links

    def link_template(self, links, inpath):
        in_parts = inpath[1:].split('/')
        links.append({
            "href": self.server + inpath + "?outputFormat=application%2Fjson",
            "rel": "self",
            "type": "application/json",
            "title": in_parts[-1]  + " document as json"
        })
        links.append({
            "href": self.server + inpath + "?outputFormat=application%2Fx-yaml",
            "rel": "alternate",
            "type": "application/x-yaml",
            "title": in_parts[-1] + " document as yaml"
        })
        links.append({
            "href": self.server + inpath + "?outputFormat=text%2Fxml",
            "rel": "alternate",
            "type": "text/xml",
            "title": in_parts[-1] + " document as xml"
        })
        links.append({
            "href": self.server + inpath + "?outputFormat=text%2Fhtml",
            "rel": "alternate",
            "type": "text/html",
            "title": in_parts[-1] + " document as html"
        })
        return links

    def link_template_point(self, links, inpath):
        in_parts = inpath[1:].split('/')
        links.append({
            "href": self.server + inpath + "",
            "rel": "self",
            "type": "point",
            "title": "Point Query",
            "self": "Point"
        })
        return links

    def link_template_polygon(self, links, inpath):
        in_parts = inpath[1:].split('/')
        links.append({
            "href": self.server + inpath + "",
            "rel": "self",
            "type": "polygon",
            "title": "Polygon Query",
            "self": "Polygon"
        })
        return links


    def get_parameter_list(self, collname):

        parameters = []
        for c in collection_cache['data']['collections']:           
            if c['id'] == collname:
                for p in c['parameters']:
                    parameters.append(p)            
        return parameters

    def collections_description(self, collname, display_links):
        global collection_cache
        if collection_cache == None:
            collection_cache = {}
            collection_cache['update'] = (datetime.now() - timedelta(hours=5))

        if collection_cache['update'] < (datetime.now() - timedelta(minutes=5)):

            collections = self.collection_loop()
            collection_cache = {}
            collection_cache['update'] = datetime.now()
            collections['links'] = self.create_links(False)
            collection_cache['data'] = collections
        output = {}
        if collname == "all":
            output = self.all_values(output, display_links)
        elif collname.find("summary£") > -1:
            output = self.summary(collname)
        elif collname.find("extent£") > -1:
            output = self.extent(collname, output)
        elif 'automated' in collname:
            output = self.automated(output, display_links)
        else:
            output = self.other(collname, output)
      

        return output


    def collection_loop(self):

        collections = {}

        collections['collections'] = []        

        for c in self.datasets:

            collection = self.datasets[c]
            if collection["provider"]["data_source"].find("thredds") > -1:
                try: 
                    tc = ThreddsCatalogueProvider()
                    collections['collections'].extend(tc.query_catalogue(self.mp_, self.server, collection))
                except:
                    print ("Thredds server unavailable")
            elif collection["provider"]["name"] == "ndfd":
                ndfd = NDFDMetadataProvider(self.server, self.mp_)
                collections['collections'].extend(ndfd.get_metadata(c, collection))
            else:
                description = self.other_metadata(collection, c)
                
                description["outputCRS"] = [{"id":"EPSG:4326","wkt":util.proj2wkt(util.WGS84)}]
                description["polygonQueryOptions"] = {}
                description["polygonQueryOptions"]["interpolationX"] = ["nearest_neighbour"]
                description["polygonQueryOptions"]["interpolationY"] = ["nearest_neighbour"]
                description["pointQueryOptions"] = {}
                description["pointQueryOptions"]["interpolation"] = ["nearest_neighbour"]
                description["outputFormat"] = ["CoverageJSON"]

                collections['collections'].append(description)

        return collections


    def get_instance_value(self, collection):
        try:
            collection['id'].split('_')
            collection['instanceAxes'] = copy.deepcopy(self.datasets[collection['id'].split('_')[0]]['instanceAxes'])
            if ('z' in collection['instanceAxes']) and ('vertical' in collection['extent']):
                if len(collection['extent']['vertical']['name'][0]) > 0:
                    lower_bound, upper_bound = self.get_height_min_max(collection['extent']['vertical']['range'])
                    collection['instanceAxes']['z']['lowerBound'] = lower_bound
                    collection['instanceAxes']['z']['upperBound'] = upper_bound
                    if 'units' in collection['extent']['vertical']:
                        collection['instanceAxes']['z']['label'] = collection['extent']['vertical']['units']
                    if 'unit_desc' in collection['extent']['vertical']:
                        collection['instanceAxes']['z']['uomLabel'] = collection['extent']['vertical']['unit_desc']
                else:
                    del collection['instanceAxes']['z']
            if ('t' in collection['instanceAxes']) and ('temporal' in collection['extent']):
                lower_bound, upper_bound = self.get_time_min_max(collection['extent']['temporal']['range'])
                
                collection['instanceAxes']['t']['lowerBound'] = lower_bound
                collection['instanceAxes']['t']['upperBound'] = upper_bound
            del collection['extent']
        except:
            print('Invalid collection')

        return collection

    def get_time_min_max(self, iso_times):

        datetime_list = []
        for itime in iso_times:
            datetime_list.append(parse.TimePointParser().parse(itime))
        lower_bound = dump.TimePointDumper().dump(min(datetime_list),'CCYY-MM-DDThh:mm:ssZ')
        upper_bound = dump.TimePointDumper().dump(max(datetime_list),'CCYY-MM-DDThh:mm:ssZ')

        return lower_bound, upper_bound

    def get_height_min_max(self, heights):

        height_list = []
        for height in heights:
            height_list.append(float(height))
        lower_bound = min(height_list)
        upper_bound = max(height_list)

        return lower_bound, upper_bound   

    def all_values(self, output, display_links):
        output['collections'] = []
        for c in collection_cache['data']['collections']:
            collection_detail = {}
            collection_detail['id'] = c['id']
            collection_detail['title'] = c['title']
            collection_detail['description'] = c['description']
            collection_detail['extent'] = {}
            collection_detail['extent'] = util.geographictoextent(c['extent']['horizontal']['geographic'])


            url_parts = c['links'][0]['href'].split('/')
            collection_detail['links'] = self.link_template( [], "/" + url_parts[-4] + "/" + url_parts[-3])
            output['collections'].append(collection_detail)

        if display_links:
            output['links'] =  self.link_template( [], "/collections")
        return output
     
    def automated(self, output, display_links):
        collection_detail = {}
        col_json=self.auto_col_json
        zarr_store=self.automated_ds+'/'+self.auto_model+'/'+self.auto_cycle+'/zarr/*'
        col_ids=[]
        link_list=[]
        for c in sorted(glob.iglob(zarr_store)):
           c_short=os.path.basename(c)
           col_ids.append(c_short)
           link_list.append("/collections/automated_"+c_short+"/instance/"+self.auto_cycle)
        link_template_list=[]
        for l in link_list:
            link_template_list.append(self.link_template( [], l))
        output['links']=link_template_list
        return output
    

    def automated_collection_desc(self, collname, display_links):
        output={}
        cid="_".join(collname.split("_", 2)[1:])
        point='/collections/'+collname+'/instance/'+self.auto_cycle+'/point'
        polygon='/collections/'+collname+'/instance/'+self.auto_cycle+'/polygon'
        orig=self.link_template( [], '/collections/'+collname+'/instance/'+self.auto_cycle)
        point=self.link_template_point( [], point)
        polygon=self.link_template_polygon( [], polygon)
        link_list=orig+point+polygon
        output['links']=link_list
        output['collections']=collname
        output['title']=collname
        with open(self.auto_col_json, 'r') as col_json:
           col=json.load(col_json)
        for idx,c in enumerate(col):
           if col[idx]['collection_name']==cid:
              collection=c
        f_key=''
        for key in collection:
           if 'forecast_time' in key:
              f_key=key
        output['parameters']={}
        time_iso=[]
        for idx,p in enumerate(collection['parameters']):
           if not f_key:
              output['parameters'].update({p: {\
              'description': {'en': collection['long_name'][0]},
              'unit': {'label':{'en': ''} ,'symbol':{'value':'','type':''}},
              'observedProperty': {'label': {'en':  collection['long_name'][0]}},
              'extent': {'horizontal': {'name': ['longitude','latitude'],'coordinates': ['x','y'],'geographic': "BBOX[-180.0,-89.9,180.0,89.9]"}}}})
           if f_key:
              for t in collection[f_key]:
                 t=t.replace("'",'')
                 time_iso.append(t)
              output['parameters'].update({p: {\
              'description': {'en': collection['long_name'][0]},
              'unit': {'label':{'en': ''} ,'symbol':{'value':'','type':''}},
              'observedProperty': {'label': {'en':  collection['long_name'][0]}}, 
              'extent': {'temporal': {'name': ['time'],'coordinates':['time'], 'range': time_iso},'horizontal': {'name': ['longitude','latitude'],'coordinates': ['x','y'],'geographic': "BBOX[-180.0,-89.9,180.0,89.9]"}}}})
              for l in collection['dimensions']:
                 if 'lv' in l:
                    try:
                       output['parameters'].update({p: {\
                       'description': {'en': collection['long_name'][0]},
                       'unit': {'label':{'en': ''} ,'symbol':{'value':'','type':''}},
                       'observedProperty': {'label': {'en':  collection['long_name'][0]}},
                       'extent': {'temporal': {'name': ['time'],'coordinates':['time'], 'range': time_iso},'horizontal':\
                       {'name': ['longitude','latitude'],\
                       'coordinates': ['x','y'],'geographic': "BBOX["+collection['lon_0'][0]+','+collection['lat_0']\
                       [len(collection['lat_0'])-1]+','+collection['lon_0'][len(collection['lon_0'])-1]+','+\
                       collection['lat_0'][0]+"]"},'vertical':{'name':[l],'coordinates':['z'],'range':collection[l]}}}})
                    except:
                       output['parameters'].update({p: {\
                       'description': {'en': collection['long_name'][0]},
                       'unit': {'label':{'en': ''} ,'symbol':{'value':'','type':''}},
                       'observedProperty': {'label': {'en':  collection['long_name'][0]}},
                       'extent': {'temporal': {'name': ['time'],'coordinates':['time'], 'range': time_iso},'horizontal':\
                       {'name': ['longitude','latitude'],\
                       'coordinates': ['x','y'],'geographic': "BBOX["+collection['xgrid_0'][0]+','+collection['ygrid_0']\
                       [len(collection['ygrid_0'])-1]+','+collection['xgrid_0'][len(collection['xgrid_0'])-1]+','+\
                       collection['ygrid_0'][0]+"]"},'vertical':{'name':[l],'coordinates':['z'],'range':collection[l]}}}})

        output['outputFormat']=['CoverageJSON']
        output['pointQueryOptions']={}
        output['pointQueryOptions']['interpolation']=['nearest_neighbor']
        output['outputCRS']=[{'id': 'EPSG:4326'}]
        output['id']=collname
        #populate instance axes
        output['instanceAxes']={}
        for e in output['parameters'][p]['extent']:
           if e == 'horizontal':
              try:
                 output['instanceAxes']['x']={'label': 'Longitude', 'lowerBound': collection['lon_0'][0],\
                 'upperBound': collection['lon_0'][len(collection['lon_0'])-1], 'uomLabel': "degrees"}
              except:
                 output['instanceAxes']['x']={'label': 'Longitude', 'lowerBound': collection['xgrid_0'][0],\
                 'upperBound': collection['xgrid_0'][len(collection['xgrid_0'])-1], 'uomLabel': "degrees"}
              try:
                 output['instanceAxes']['y']={'label': 'Latitude', 'lowerBound': collection['lat_0'][len(collection['lat_0'])-1],\
                 'upperBound': collection['lat_0'][0], 'uomLabel': "degrees"}
              except:
                 output['instanceAxes']['y']={'label': 'Latitude', 'lowerBound': collection['ygrid_0'][len(collection['ygrid_0'])-1],\
                 'upperBound': collection['ygrid_0'][0], 'uomLabel': "degrees"}
           if e == 'vertical':
              output['instanceAxes']['z']={'label': l, 'lowerBound': collection[l][0], 'upperBound': collection[l][len(collection[l])-1], 'uomLabel': l}
           if e == 'temporal':
              output['instanceAxes']['t']={'label': 'Time', 'lowerBound': time_iso[0], 'upperBound': time_iso[len(time_iso)-1], 'uomLabel': "ISO8601"}
        return output


    def summary(self, collname):
        output = []
        self.link_path = []
        scol = collname.split("£")[1]
        for c in collection_cache['data']['collections']:
            if c['id'].find(scol) > -1:
                self.link_path.append('/collections/'+c['id'])          
        output = self.create_links(True)

        return output    
    
    def extent(self, collname, output):
        scol = collname.split("£")[1]
        for c in collection_cache['data']['collections']:           
            if c['id'] == scol:
                output = {}
                output['spatial'] = c['extent']['horizontal']['geographic']
                if 'temporal' in c['extent']:
                    lower_bound, upper_bound = self.get_time_min_max(c['extent']['temporal']['range'])
                    output['temporal'] = lower_bound + "/" + upper_bound
                if ('vertical' in c['extent']) and (len(c['extent']['vertical']['name'][0]) > 0):
                    lower_bound, upper_bound = self.get_height_min_max(c['extent']['vertical']['range'])
                    output['vertical'] = str(lower_bound) + "/" + str(upper_bound)

        return output
    
    def other(self, collname, output):
        collection_detail = {}
        for c in collection_cache['data']['collections']:
            
            if c['id'] == collname:
                collection_detail =  c
        collection_detail = self.get_instance_value(copy.deepcopy(collection_detail))
        if 'links' in collection_detail:
            query_links = []
            for val in collection_detail:
                if val == 'links':
                    query_links.extend(collection_detail[val])
                output[val] = collection_detail[val]
            url_parts = query_links[0]['href'].split('/')
            output['links'] = self.link_template( [], "/" + url_parts[-4] + "/" + url_parts[-3] + "/" + url_parts[-2])
            for qlink in query_links:
                if qlink['href'].lower().find('point') > -1:
                    qlink['self'] = "Point"
                    qlink['title'] = "Point query"
                elif qlink['href'].lower().find('polygon') > -1:
                    qlink['self'] = "Polygon"
                    qlink['title'] = "Polygon query"
                output['links'].append(qlink)

        return output

    def other_metadata(self, collection, c_id):
        if c_id == "metar":
            description = self.get_metar_metadata(collection, c_id)
        elif c_id == "osmhighways" or c_id == "dem":
            description = self.get_simple_metadata(collection, c_id)
        elif "automated" in c_id:
            description = self.get_automated_metadata(collection, c_id)
            print(collection)
        return description
    
    def get_metar_metadata(self, collection, c_id):
        temporal = []
        tperiod = timedelta(hours=-36)
        now = datetime.strptime(datetime.now().strftime(
            "%d-%m-%YT%H:00"), "%d-%m-%YT%H:%M")
        now = now + tperiod
        for tloop in range(1, 36, 1):
            temporal.append(
                (now + timedelta(hours=tloop)).isoformat()+'Z')

        description = {"id": c_id,
                    "title": self.datasets[c_id]['title'],
                    "description": collection['description'],
                    "extent": {
                        "horizontal": util.horizontaldef(["longitude","latutude"],["x","y"],collection['extent']['spatial'].split(',')),
                        "temporal": util.coorddef(["time"],["time"],temporal)
                    },
                    "links": [util.createquerylinks(self.server + '/collections/' + c_id + '/raw/point','self','point','Point query for raw ' + collection['title'])]

                    }
        description['parameters'] = {}
        for p in self.datasets[c_id]['parameters']:
            if type(self.datasets[c_id]['parameters'][p][0]) is str:
                parts = self.datasets[c_id]['parameters'][p][0].split(
                    '/')
                if parts[-3] == 'bufr4':
                    description['parameters'][p] = (self.mp_.get_buf4_detail(
                        parts[-3], parts[-2], parts[-1], None))
                elif parts[4] == 'grib2':
                    description['parameters'][p] =(self.mp_.get_grib_detail(
                        parts[-3], parts[-2], parts[-1], None))
                description['parameters'][p]['extent'] = description['extent']
            else:
                description['parameters'][self.datasets[c_id]['parameters'][p][0]['description']['en'].lower().replace(' ','_')] = (self.datasets[c_id]['parameters'][p][0])
                description['parameters'][self.datasets[c_id]['parameters'][p][0]['description']['en'].lower().replace(' ','_')]['extent'] = description['extent']
        return description
    
    def get_simple_metadata(self, collection, c_id):
        description = {"id": c_id,
                    "title": self.datasets[c_id]['title'],
                    "description": collection['description'],
                    "extent": {
                        "horizontal": util.horizontaldef(["longitude","latutude"],["x","y"],collection['extent']['spatial'].split(',')),
                    },
                    "links": [util.createquerylinks(self.server + '/collections/' + c_id + '/latest/point','self','point','Point query for latest ' + collection['title']),util.createquerylinks(self.server + '/collections/' + c_id + '/latest/polygon','self','polygon','Polygon query for latest ' + collection['title'])]

                    }
        description['parameters'] = {}
        for p in self.datasets[c_id]['parameters']:
            description['parameters'][self.datasets[c_id]['parameters'][p][0]['description']['en'].lower().replace(' ','_')] = (self.datasets[c_id]['parameters'][p][0])
            description['parameters'][self.datasets[c_id]['parameters'][p][0]['description']['en'].lower().replace(' ','_')]['extent'] = description['extent']
        return description


    def get_automated_metadata(self, collection, cid):
        #with open(self.auto_col_json, 'r') as col_json:
        #  col=json.load(col_json)
        #instance_id = self.auto_cycle
        #model=self.auto_model
        #cycle=self.auto_cycle
        
        model=collection['provider']['model'][0]
        cycle=collection['provider']['cycle'][0]
        description = {"id": cid,
                    "title": self.datasets[cid]['title'],
                    "description": collection['description'],
                    "extent": {
                        "horizontal": util.horizontaldef(["longitude","latutude"],["x","y"],collection['extent']['spatial'].split(',')),
                    },
                    "links": [util.createquerylinks(self.server + '/collections/automated_'+model + '_' + cid+'/instance/'+cycle+'/point','self','point','Point query for ' + collection['title']),util.createquerylinks(self.server + '/collections/automated_' + model +'_'+cid + '/instance/'+cycle+'/polygon','self','polygon','Polygon query for '+collection['title'])]
                    }
        description['parameters'] = {}

        return description
 


