from flask import Flask
from flask import make_response
from flask import request
from flask import render_template
from os import path, sep
import os
import yaml
import click
from WoW.provider.base import ProviderQueryError
from WoW.api import API
from WoW.provider.metadata import MetadataProvider
from WoW.formatters.format_output import FormatOutput
from WoW.util import style_html
from flask_cors import CORS
from jinja2 import Environment, FileSystemLoader




app = Flask(__name__, static_url_path='/static')
CORS(app)

with open(os.environ.get('WoW_CONFIG')) as fh:
    CONFIG = yaml.load(fh)
api_ = API(CONFIG)
registry_ = MetadataProvider(CONFIG)

TEMPLATES = '{}{}templates'.format(os.path.dirname(
    os.path.realpath(__file__)), os.sep)

@app.route('/')
def root():
    headers, status_code, content = api_.root(
        request.headers, request.args)
  

    response = make_response(content, status_code)

    if headers:
        response.headers = headers

    return response

@app.route('/groups', strict_slashes=False)
@app.route('/groups/<path:subpath>', strict_slashes=False)
def groups(subpath=None):
    headers, status_code, content = api_.describe_group(
        request.headers, request.args, subpath)

    response = make_response(content, status_code)

    if headers:
        response.headers = headers

    return response



@app.route('/collections/<collection>/<identifier>/point')
def get_data(collection,identifier):

    try:
        headers, status_code, content = api_.get_feature(
            request.headers, request.args, collection,identifier)

        response = make_response(content, status_code)

        if headers:
            response.headers = headers

        return response
    except ProviderQueryError:
        return _render_j2_template(CONFIG, "index_p.html", None)

@app.route('/collections/<collection>/<identifier>/polygon')
def get_polygon_data(collection, identifier):

    try:
        headers, status_code, content = api_.get_feature(
            request.headers, request.args, collection)

        response = make_response(content, status_code)

        if headers:
            response.headers = headers

        return response
    except ProviderQueryError:
        return _render_j2_template(CONFIG, "index_p.html", None)


@app.route('/api', strict_slashes=False)
def api():

    headers, status_code, content = api_.api(request.headers, request.args)
    response = make_response(content, status_code)
    if headers:
        response.headers = headers

    return response


@app.route('/collections/<collection>/instance/<identifier>', strict_slashes=False)
def get_automated_collection_details(collection, identifier):


    headers, status_code, content = api_.describe_automated_collections(
        request.headers, request.args, collection, identifier)

    response = make_response(content, status_code)

    if headers:
        response.headers = headers

    return response


@app.route('/collections/<collection>/instance/<identifier>/point', strict_slashes=False)
def get_data_automated(collection,identifier):

    try:
        headers, status_code, content = api_.get_feature(
            request.headers, request.args, collection,identifier)

        response = make_response(content, status_code)

        if headers:
            response.headers = headers

        return response
    except ProviderQueryError:
        return _render_j2_template(CONFIG, "index_p.html", None)


@app.route('/collections/<collection>/instance/<identifier>/polygon')
def get_polygon_data_automated(collection, identifier):

    try:
        headers, status_code, content = api_.get_feature(
            request.headers, request.args, collection, identifier)

        response = make_response(content, status_code)

        if headers:
            response.headers = headers

        return response
    except ProviderQueryError:
        return _render_j2_template(CONFIG, "index_p.html", None)


@app.route('/collections/<collection>/<identifier>', strict_slashes=False)
def get_collection_details(collection, identifier):


    headers, status_code, content = api_.describe_collection(
        request.headers, request.args, collection, identifier)

    response = make_response(content, status_code)

    if headers:
        response.headers = headers

    return response


@app.route('/collections/<collection>', strict_slashes=False)
def get_identifier_details(collection):


    headers, status_code, content = api_.list_identifers(
        request.headers, request.args, collection)

    response = make_response(content, status_code)

    if headers:
        response.headers = headers

    return response


@app.route('/collections', strict_slashes=False)
def collection():


    headers, status_code, content = api_.describe_collections(
        request.headers, request.environ, request.args)

    response = make_response(content, status_code)
    if headers:
        response.headers = headers

    return response


@app.route('/metadata/', strict_slashes=False)
@app.route('/metadata/<register>', strict_slashes=False)
@app.route('/metadata/<register>/<table>', strict_slashes=False)
@app.route('/metadata/<register>/<table>/<codeid>', strict_slashes=False)
def metadata(register=None, table=None, codeid=None):

    headers, status_code, content = registry_.query(request.headers, request.args,  register, table, codeid, True)
    response = make_response(content, status_code)
    if headers:
        response.headers = headers

    return response

@app.route('/conformance', strict_slashes=False)
def conformance():
    headers, status_code, content = api_.api_conformance(request.headers,
                                                         request.args)

    response = make_response(content, status_code)
    if headers:
        response.headers = headers

    return response

@click.command()
@click.pass_context
@click.option('--debug', '-d', default=False, is_flag=True, help='debug')
def serve(ctx, debug=False):
    """Serve weather on the web via Flask"""

    if not api_.config['server']['pretty_print']:
        app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

    if 'cors' in api_.config['server'] and api_.config['server']['cors']:
        from flask_cors import CORS
        CORS(app)

    app.run(debug=debug, host=api_.config['server']['bind']['host'],
            port=api_.config['server']['bind']['port'])

def _render_j2_template(config, template, data):
    """
    render Jinja2 template

    :param config: dict of configuration
    :param template: template (relative path)
    :param data: dict of data

    :returns: string of rendered template
    """

    env = Environment(loader=FileSystemLoader(TEMPLATES))

    template = env.get_template(template)
    return template.render(config=config, data=data, version='0.0.1')
