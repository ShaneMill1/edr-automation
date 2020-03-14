from datetime import datetime, timedelta
import json
import logging
import os
import copy
import shapely.wkt
from shapely.geometry import box
from jinja2 import Environment, FileSystemLoader
from shapely.geometry import Polygon, Point
from WoW.log import setup_logger
from WoW.provider import load_provider
from WoW.formatters import FORMATTERS, load_formatter, format_output
from WoW.provider.base import ProviderConnectionError, ProviderQueryError
from WoW.templates.open_api import OPENAPI
from WoW.util import style_html
import WoW.isodatetime.parsers as parse

VERSION = '0.0.1'
LOGGER = logging.getLogger(__name__)

TEMPLATES = '{}{}templates'.format(os.path.dirname(
    os.path.realpath(__file__)), os.sep)

HEADERS = {
    'Content-type': 'application/json',
    'X-Powered-By': 'Weather on the Web {}'.format(VERSION)
}


class API(object):
    """API object"""

    def __init__(self, config):
        """
        constructor

        :param config: configuration dict

        :returns: `WoW.API` instance
        """

        self.config = config
        self.config['server']['url'] = self.config['server']['url'].rstrip('/')

        if 'templates' not in self.config['server']:
            self.config['server']['templates'] = TEMPLATES

        setup_logger(self.config['logging'])

    def root(self, headers, args):
        """
        Provide API

        :param headers: dict of HTTP headers
        :param args: dict of HTTP request parameters

        :returns: tuple of headers, status code, content
        """


        headers = {}
        content_type = args.get('outputFormat')
        fo = format_output.FormatOutput(self.config, ["/","/api","/metadata","/conformance","/groups","/collections"])
        output = fo.create_links(True)
        if content_type is not None:

            if content_type.find('html') > -1:
                output = _render_j2_template(self.config, 'root.html', output)
                content_type = 'text/html'
            elif content_type.find('xml') > -1:
                output = fo.get_xml(output)
                content_type = 'application/xml'
            elif (content_type.find('yml') > -1) or (content_type.find('yaml') > -1):
                output = fo.get_yaml(output)
                content_type = 'application/x-yaml'
            else:
                output = fo.get_json(output)
                content_type = 'application/json'
        else:
            content_type = 'text/html'
            output = _render_j2_template(self.config, 'root.html', output)
 
        headers['Content-Type'] = content_type

        return headers, 200, output




    def api(self, headers, args):
        """
        Provide OpenAPI document

        :param headers: dict of HTTP headers
        :param args: dict of HTTP request parameters

        :returns: tuple of headers, status code, content
        """
        open_api_ = OPENAPI(self.config['server']['url'])
        content_type = args.get('outputFormat')
        output = ''
        if content_type is not None:
            if content_type.find('json') > -1:
                output = open_api_.get_json()
            elif content_type.find('html') > -1:
                output =  open_api_.get_html()
            elif content_type.find('xml') > -1:
                output = open_api_.get_xml()
            elif (content_type.find('yml')) or (content_type.find('yaml') > -1):
                output = open_api_.get_yaml()
        else:
            content_type = 'text/html'
            output =  open_api_.get_html()

        headers_ = HEADERS.copy()
        headers_['Content-type'] = content_type

        return headers_, 200, output

    def api_conformance(self, headers, args):
        """
        Provide conformance definition

        :param headers: dict of HTTP headers
        :param args: dict of HTTP request parameters

        :returns: tuple of headers, status code, content
        """

        headers_ = HEADERS.copy()

        formats = ['json', 'html','application/json','text/html','application%2Bjson','text%2Bhtml']

        format_ = args.get('outputFormat')


        if format_ is not None and format_ not in formats:
            exception = {
                'code': 'InvalidParameterValue',
                'description': 'Invalid format'
            }
            LOGGER.error(exception)
            return headers_, 400, json.dumps(exception)

        conformance = {
            'conformsTo': [
                {'title':'CoverageJSON specification','href':'https://github.com/covjson/specification'},
                {'title':'Well Known Text specification','href':'http://docs.opengeospatial.org/is/18-010r7/18-010r7.html'},
                {'title':'ISO8601 specification','href':'https://www.iso.org/iso-8601-date-and-time-format.html'}
            ]
        }

        if (format_ == None) or (format_.find('html') > -1):  # render
            headers_['Content-type'] = 'text/html'
            content = _render_j2_template(self.config, 'conformance.html',
                                          conformance)
            return headers_, 200, content

        return headers_, 200, json.dumps(conformance)

    def describe_group(self, headers, args, subpath=None):
        output = {}
        fo = format_output.FormatOutput(self.config, ['/groups'])
        output['links'] = fo.create_links(False)
        content_type = args.get('outputFormat')
        group_links = []
        cdescrip = None
        headers = {}
        group_links, cdescrip = self.group_metadata(subpath)
        template_name = "group.html"
        if cdescrip == None:
            fo = format_output.FormatOutput(self.config, group_links)
            output['members'] = fo.create_links(True)
        else:
            fo = format_output.FormatOutput(self.config, ["/collections"])
            co_descrip = fo.collections_description(cdescrip, False)
            output['members'] = []
            for co_link in co_descrip:
                if co_link[3]['href'].find('collection') > -1:
                    output['members'].append(co_link)

        if content_type is not None:

            if content_type.find('html') > -1:
                output = _render_j2_template(self.config,template_name,output)
                content_type = 'text/html'
            elif content_type.find('xml') > -1:
                output = fo.get_xml(output)
                content_type = 'application/xml'
            elif (content_type.find('yml') > -1) or (content_type.find('yaml') > -1):
                output = fo.get_yaml(output)
                content_type = 'application/x-yaml'
            else:
                output = fo.get_json(output)
                content_type = 'application/json'
        else:
            content_type = 'text/html'
            output = _render_j2_template(self.config,template_name,output)


        headers['Content-Type'] = content_type

        return headers, 200, output

    def group_metadata(self, subpath):
        
        group_links = []
        cdescrip = None
        if not subpath is None:
            groupids = subpath.split("/")
            groupid = groupids[-1]
        if subpath == None:
            for group in self.config['groups']:
                if self.config['groups'][group]['type'] == 'group':
                    group_links.append('/groups/'+group)
        else:
            group_links, cdescrip = self.build_group_links(subpath, groupids,  groupid, group_links)
        
        return group_links, cdescrip

    def build_group_links(self, subpath, groupids, groupid, group_links):
        cdescrip = None
        if not (groupid in self.config['groups']):
            cdescrip = 'summary£'+groupid       
        elif self.config['groups'][groupid]['type'].find('group') > -1:
            for child in self.config['groups'][groupid]['children']:
                group_links.append('/groups/'+subpath+"/"+child)
        else:
            cdescrip = 'summary£'+self.config['datasets'][groupid]["provider"]["name"]     

        return group_links, cdescrip

    def list_identifers(self, headers, args, collection):

        output = {}
        fo = format_output.FormatOutput(self.config, ["/collections/"+collection])
        output['links'] = fo.create_links(False)
        output['instances'] = []
        content_type = args.get('outputFormat')

        instance = self.set_instance_type(collection)
        
        output['instances'] = instance
        output['name'] = collection
        output['title'] = collection.replace('_',' ')
        output['parameters'] = fo.get_parameter_list(collection)
        headers = {}
        if content_type is not None:
            if content_type.find('html') > -1:
                headers['Content-Type'] = 'text/html'
                output = _render_j2_template(self.config,"collection.html",output)
            elif content_type.find('xml') > -1:
                headers['Content-Type'] = 'application/xml'
                output = fo.get_xml(output)
            elif (content_type.find('yml') >-1) or (content_type.find('yaml') > -1):
                headers['Content-Type'] = 'application/x-yaml'
                output = fo.get_yaml(output)
            else:
                output = fo.get_json(output)
                headers['Content-Type'] = 'application/json'
        else:
            headers['Content-Type'] = 'text/html'
            output = _render_j2_template(self.config,"collection.html",output)

        return headers, 200, output


    def set_default_instance_type(self, collection):
        fn = ""
        for ds in self.config['datasets']:
            if collection.find(self.config['datasets'][ds]['name']) > -1:
                if self.config['datasets'][ds]['provider']['type'] == 'obs':
                    fn = 'raw'
                elif self.config['datasets'][ds]['provider']['type'] == 'model_file':
                   try:            
                      fn = self.config['datasets'][ds]['provider']['data_source']+'coord_info.json'
                   except:
                      fn = 'latest'
                else:
                    fn = 'latest'
        return fn

    def set_instance_type(self, collection):
        instance = []
        fn = self.set_default_instance_type(collection)
        if fn.find('coord_info.json') > -1:
            with open(fn) as json_file:
                iid = json.load(json_file)['folder']
                instance.append(self.instance_desc(collection, 'latest', 'Latest model run', 'The ' + collection + ' collection for the latest available model run', "/collections/"+collection))
                instance.append(self.instance_desc(collection, iid, iid + ' model run', 'The ' + collection + ' collection for the '+iid+' model run', "/collections/"+collection))

        elif fn == 'raw':
            instance.append(self.instance_desc(collection, 'raw', 'Raw values', 'The raw data values for the ' + collection + ' collection', "/collections/"+collection))
            instance.append(self.instance_desc(collection, 'qcd', 'Quality controlled values', 'The Quality controlled values for the ' + collection + ' collection', "/collections/"+collection))
        else:
            if 'automated' in collection:
               instance_cycle=self.config['datasets'][collection]['provider']['cycle']
               instance_model=self.config['datasets'][collection]['provider']['model']
               for m in instance_model:
                  for c in instance_cycle:
                     instance.append(self.instance_desc(collection,c,c+' values', 'The '+c+' values for the automated ' + m + ' collection', "/collections/automated_"+m))
            else:
               instance.append(self.instance_desc(collection, 'latest', 'Latest values', 'The latest values for the ' + collection + ' collection', "/collections/"+collection))
        return instance
    
    def describe_automated_collections(self, headers, args, dataset, identifier):
        fo = format_output.FormatOutput(self.config, ["/collections/"+dataset+"/"+identifier])
        output = fo.create_links(False)

        content_type = args.get('outputFormat')
        output = fo.automated_collection_desc(dataset,True)

        output['name'] = dataset
        output['instance'] = identifier
        headers = {}
        try:
            if content_type is not None:
                if content_type.find('html') > -1:
                    headers['Content-Type'] = 'text/html'
                    output = _render_j2_template(self.config,"instance.html",output)
                elif content_type.find('xml') > -1:
                    headers['Content-Type'] = 'application/xml'
                    output = fo.get_xml(output)
                elif (content_type.find('yml') >-1) or (content_type.find('yaml') > -1):
                    headers['Content-Type'] = 'application/x-yaml'
                    output = fo.get_yaml(output)
                else:
                    output = fo.get_json(output)
                    headers['Content-Type'] = 'application/json'
            else:
                headers['Content-Type'] = 'text/html'
                output = _render_j2_template(self.config,"instance.html",output)
        except:
            output = _render_j2_template(self.config,'error.html',{})

        return headers, 200, output   



    def describe_collection(self, headers, args, dataset, identifier):
        fo = format_output.FormatOutput(self.config, ["/collections/"+dataset+"/"+identifier])
        output = fo.create_links(False)
        
        content_type = args.get('outputFormat')
        output = fo.collections_description(dataset, True)

        output['name'] = dataset
        output['instance'] = identifier
        headers = {}
        try:
            if content_type is not None:
                if content_type.find('html') > -1:
                    headers['Content-Type'] = 'text/html'
                    output = _render_j2_template(self.config,"instance.html",output)
                elif content_type.find('xml') > -1:
                    headers['Content-Type'] = 'application/xml'
                    output = fo.get_xml(output)
                elif (content_type.find('yml') >-1) or (content_type.find('yaml') > -1):
                    headers['Content-Type'] = 'application/x-yaml'
                    output = fo.get_yaml(output)
                else:
                    output = fo.get_json(output)
                    headers['Content-Type'] = 'application/json'
            else:
                headers['Content-Type'] = 'text/html'
                output = _render_j2_template(self.config,"instance.html",output)
        except:
            output = _render_j2_template(self.config,'error.html',{})

        return headers, 200, output

    def describe_collections(self, headers, environ, args, dataset=None):
        """
        Provide feature collection metadata

        :param headers: dict of HTTP headers
        :param args: dict of HTTP request parameters

        :returns: tuple of headers, status code, content
        """
        ipparts = environ['REMOTE_ADDR'].split('.')
        if len(headers.getlist("X-Forwarded-For")) > 0:
            ipparts = headers.getlist("X-Forwarded-For")[0].split('.')

        met_ip = False
        if (ipparts[0] == '151') and (ipparts[1] == '170') or environ['REMOTE_ADDR'] == '127.0.0.1':
            met_ip = True

        fo = format_output.FormatOutput(self.config, ["/collections"], met_ip)
        content_type = args.get('outputFormat')
        output = fo.collections_description("all", True)
        headers = {}
        try:
            if content_type is not None:
                if content_type.find('html') > -1:
                    headers['Content-Type'] = 'text/html'
                    output = _render_j2_template(self.config,"collections.html",output)
                elif content_type.find('xml') > -1:
                    headers['Content-Type'] = 'application/xml'
                    output = fo.get_xml(output)
                elif (content_type.find('yml') >-1) or (content_type.find('yaml') > -1):
                    headers['Content-Type'] = 'application/x-yaml'
                    output = fo.get_yaml(output)
                else:
                    output = fo.get_json(output)
                    headers['Content-Type'] = 'application/json'
            else:
                headers['Content-Type'] = 'text/html'
                output = _render_j2_template(self.config,'collections.html',output)
        except:
            output = _render_j2_template(self.config,'error.html',{})

        return headers, 200, output

    def get_feature(self, headers, args, dataset,identifier):
        """
        Get a feature

        :param headers: dict of HTTP headers
        :param args: dict of HTTP request parameters
        :param dataset: collection name

        :returns: tuple of headers, status code, content
        """
        outputFormat = args.get('outputFormat') 
        headers_ = HEADERS.copy()

        qtype = "cube"
        if len(args) > 0:
            coords, qtype, valid_loc = self.process_coords(args, dataset)
            timerange = args.get('time')
            params = self.get_params(args)

            time_range = None
            output = None
            if timerange is not None:
                if timerange.find("/") > -1:
                    time_range = parse.TimeIntervalParser().parse(timerange)
                else:
                    time_range = parse.TimeIntervalParser().parse(timerange+"/"+timerange)

            z_value = args.get('z')
            if z_value == None:
                z_value = args.get('Z')

            if valid_loc:
                headers_, http_code, output = self.get_provider(dataset, qtype, coords, time_range, z_value, params, identifier, outputFormat)
            else:
                exception = {
                    'code': '400',
                    'description': 'Data requested is outside of the area covered by the datasource '
                }
                LOGGER.error(exception)
                headers_['Content-Type'] = 'application/json'
                return headers_, 400, json.dumps(exception)


        else:
            raise ProviderQueryError()

        return headers_, http_code, output 

    def get_provider(self, dataset, qtype, coords, time_range, z_value, params, identifier, outputFormat):
        headers_ = HEADERS.copy()
        try:
            p = load_provider(dataset, self.config)
            output = p.query(dataset,qtype, coords, time_range, z_value, params, identifier, outputFormat)
            return headers_, 200, output
        except ProviderConnectionError:
            exception = {
                'code': 'NoApplicableCode',
                'description': 'connection error (check logs)'
            }
            headers_['Content-Type'] = 'application/json'
            LOGGER.error(exception)
            return headers_, 500, json.dumps(exception) 



    def get_params(self, args):
        params = []
        if args.get('parametername') is not None:
            params = args.get('parametername').split(",")
            # handle leading and trailing spaces in the parameter list
            for ploop in range(0,len(params)):
                params[ploop] = params[ploop].strip()        
        return params


    def process_coords(self, args, dataset):

        bbox = self.get_bbox(dataset)
        valid_loc = False
        coords = []
        if args.get('coords') is not None:
            wkt = shapely.wkt.loads(args.get('coords'))
            qtype = wkt.type.lower()
            if wkt.type == 'Point':
                coords.append(wkt.x)
                coords.append(wkt.y)
            elif wkt.type == 'MultiPoint':
                for x in wkt.wkt[12:-1].split(','):
                    coords.append(x.strip().split(' '))                    
            elif wkt.type == 'Polygon':
                for cloop in range(0,len(wkt.exterior.xy[0])):
                    coord = [wkt.exterior.xy[0][cloop],wkt.exterior.xy[1][cloop]]
                    coords.append(coord)

            if bbox.contains(wkt):
                valid_loc = True

        return coords, qtype, valid_loc 

    def get_bbox(self, dataset):
        bbox_str = []
        if dataset in self.config['datasets']:
            bbox_str = self.config['datasets'][dataset]['extent']['spatial'].split(",")
        else:
            bbox_str = self.config['datasets'][dataset.split("_")[0]+'_'+dataset.split("_")[1]]['extent']['spatial'].split(",")
        bbox = box(float(bbox_str[0]), float(bbox_str[1]), float(bbox_str[2]), float(bbox_str[3]))        

        return bbox

    def instance_desc(self, collection, iid, title, description, link_path):
        desc = {}
        desc['id'] = iid
        desc['title'] = title
        desc['description'] = description
        fo = format_output.FormatOutput(self.config, [link_path+"/"+iid])
        desc['extent'] = fo.collections_description('extent£'+collection,True)
        desc['links'] = fo.create_links(False)
        
        return desc

def to_json(dict_):
    """
    serialize dict to json

    :param dict_: dict_

    :returns: JSON string representation
    """

    return json.dumps(dict_)

def _render_j2_template(config, template, data):
    """
    render Jinja2 template

    :param config: dict of configuration
    :param template: template (relative path)
    :param data: dict of data

    :returns: string of rendered template
    """

    env = Environment(loader=FileSystemLoader(TEMPLATES))
    env.filters['to_json'] = to_json
    env.globals.update(to_json=to_json)

    template = env.get_template(template)
    return template.render(config=config, data=data, version=VERSION)
