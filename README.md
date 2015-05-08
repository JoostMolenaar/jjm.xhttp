xhttp
=====

Framework for building WSGI apps in which requests and responses are just dictionaries.

Hello, world
------------

A basic app that returns "Hello, world!" on any HTTP method would look like this:

    @xhttp.xhttp_app
    def app(request):
        return {
            'x-status': xhttp.status.OK,
            'x-content': 'Hello, world!\n',
            'content-type': 'text/plain' }
            
The `xhttp_app` decorator translates an incoming WSGI request to the XHTTP API, where everything is just a dictionary.
The application returns one header (Content-Type) that will go to the client. The decorator picks up the `x-status`
and `x-content` headers and uses those to generate a valid HTTP response.
            
Resource
--------

There's a Resource class that routes a request to a particular method, based on the incoming HTTP verb:

    class Hello(xhttp.Resource):
        def GET(self, request):
            return {
                'x-status': xhttp.status.OK,
                'x-content': 'Hello, world!\n' }
        
        def POST(self, request):
            return { 'x-status': xhttp.status.NO_CONTENT }
    
    app = xhttp.xhttp_app(Hello())

It returns a `Method Not Allowed` when the method is not found on the class.

Router
------

There's a Router class that routes a request to a XHTTP app, based on the incoming path:

    class Resource1(xhttp.Resource):
        pass
        
    class Resource2(xhttp.Resource):
        pass
        
    class App(xhttp.Router):
        def __init__(self):
            super(App, self).__init__(
                ('^/resource1/$', Resource1()),
                ('^/resource2/$', Resource2()))
                
    app = xhttp.xhttp_app(App())

So the incoming URL is matched (with regexes) to see if it can be routed to either the Resource1 or Resource2 instance.
If it matches, those Resources will return a `Method Not Allowed` response. If another URL comes in, a `Not Found` is
returned.

Decorators
----------

Since all the inputs and outputs are just dictionaries, other things are done through decorators.

- `@accept`: Handles content negotiation
- `@get`, `@post` and `@cookie`: Handle query parameters, form post parameters and cookies
- `@catcher`: Catches exceptions, replacing them by 500 Internal Server Errors or other HTTP status codes
- `@if_modified_since` and `@if_none_match`: Handles conditional requests
- `@accept_encoding`: Handles gzip compression
- `@accept_charset`: Handles unicode
- `@cache_control` and `@vary`: Set Cache-Control and Vary headers [probably will replace this with something more generic]
- `@app_cached`: Caches responses in-memory
