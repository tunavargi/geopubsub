import uuid
import geohash
from tornado.gen import Return
from tornado.platform.asyncio import AsyncIOMainLoop
import tornado.websocket
import tornado.web
import tornado.options
import tornado.httpserver
import asyncio
from tornado import gen
import tornadoredis
import json

PORT = 8888
ADDRESS = '0.0.0.0'


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("templates/test.html")


class WebSocketHandler(tornado.websocket.WebSocketHandler):

    def __init__(self, *args, **kwargs):
        self.rooms = []
        super().__init__(*args, **kwargs)

    def check_origin(self, origin):
        return True
    
    @gen.coroutine
    def open(self, *args, **kwargs):
        # CONNECT AND GET THE ROOMS
        self.rooms = ['dummy']
        self.client = tornadoredis.Client()
        self.pubclient = tornadoredis.Client()
        self.messages_published = []
        self.client.connect()
        self.pubclient.connect()
        yield gen.Task(self.client.subscribe, self.rooms)
        self.client.listen(self.on_message_published)

    @gen.coroutine
    def set_rooms(self, coordinates):
        print('coordinates:', coordinates)
        yield gen.Task(self.client.unsubscribe, self.rooms)
        # GET THE ROOMS WITH COORDINATES
        latitude, longitude = coordinates.values()
        room = geohash.encode(latitude, longitude, precision=7)
        neighbors = geohash.neighbors(room)
        neighbors.append(room)
        self.rooms = neighbors
        yield gen.Task(self.client.subscribe, self.rooms)
        self.client.listen(self.on_message_published)


    def on_message_published(self, message):
        if not (message.kind == 'subscribe' or message.kind == 'unsubscribe'):
            message_id = json.loads(message.body).get('id')
            if message_id not in self.messages_published:
                self.messages_published.append(message_id)
                self.write_message(message.body)

    @gen.coroutine
    def on_message(self, data):
        print(data)
        datadecoded = json.loads(data)
        if '_coordinates' in str(datadecoded):
            yield self.set_rooms(datadecoded.get('_coordinates'))
            raise Return()
        message = {'body': datadecoded, 'id': str(uuid.uuid4())}

        for room in self.rooms:
            self.pubclient.publish(room, json.dumps(message))

    def on_close(self):
        for room in self.rooms:
            self.client.unsubscribe(room)

application = tornado.web.Application([
    (r'/msg', WebSocketHandler),
    (r'/', MainHandler)
])


def main():
    tornado.platform.asyncio.AsyncIOMainLoop().install()
    application.listen(8888)
    asyncio.get_event_loop().run_forever()

if __name__ == '__main__':
    main()
