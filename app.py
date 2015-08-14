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
from tornado import escape
import tornadoredis
import json
import redis
from boto_sns import send_push

PORT = 8888
ADDRESS = '0.0.0.0'

redis_connection = redis.StrictRedis(host='localhost', port=6379, db=0)


def add_user_to_rooms(rooms, device_token):
    """
    Adds user to rooms.
    """

    # This stores rooms that user in.
    redis_connection.sadd(device_token, *rooms)

    # We need to store device_tokens in order to send push notifications.
    for room in rooms:
        # This stores users joined to a specific room.
        users_joined_room_key = "users_joined_%s" % room
        redis_connection.sadd(users_joined_room_key, device_token)


def remove_user_from_rooms(device_token):
    """
    Removes user from rooms that she/he joined.
    """

    # Get the rooms that user in.
    rooms = redis_connection.smembers(device_token)

    for room in rooms:
        users_joined_room_key = "users_joined_%s" % room
        redis_connection.srem(users_joined_room_key, device_token)

    # Clear rooms that user in.
    redis_connection.delete(device_token)


def generate_neighbors(latitude, longitude, precision=9):
    """
    Generates neighbors of given coordinates and includes the coordinate itself.
    """

    latitude, longitude = map(float, [latitude, longitude])
    room = geohash.encode(latitude, longitude, precision=precision)
    neighbors = geohash.neighbors(room)
    neighbors.append(room)

    return neighbors


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("templates/test.html")


class CoordinateUpdateHandler(tornado.web.RequestHandler):
    def post(self):
        data = escape.json_decode(self.request.body)
        device_token = data["token"]
        latitude, longitude = data["_coordinates"].values()
        rooms = generate_neighbors(latitude, longitude)
        add_user_to_rooms(rooms, device_token)


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
    def set_rooms(self, coordinates, device_token):
        # remove_user_from_rooms(device_token)
        print('coordinates:', coordinates)
        yield gen.Task(self.client.unsubscribe, self.rooms)
        # GET THE ROOMS WITH COORDINATES
        latitude, longitude = coordinates.values()
        self.rooms = generate_neighbors(latitude, longitude)
        # add_user_to_rooms(self.rooms, device_token)
        yield gen.Task(self.client.subscribe, self.rooms)
        self.client.listen(self.on_message_published)

    def on_message_published(self, message):
        if not (message.kind == 'subscribe' or message.kind == 'unsubscribe'):
            message_id = json.loads(message.body).get('id')
            message = json.dumps(json.loads(message.body).get('body'))
            if message_id not in self.messages_published:
                self.messages_published.append(message_id)
                self.write_message(message)

    @gen.coroutine
    def on_message(self, data):
        print(data)
        datadecoded = json.loads(data)
        if '_coordinates' in str(datadecoded):
            yield self.set_rooms(datadecoded.get('_coordinates'), datadecoded["token"])

            # Send push notification to all receivers
            members = list()
            for room in self.rooms:
                users_joined_room_key = "users_joined_%s" % room
                members += redis_connection.smembers(users_joined_room_key)

            members = list(set(members))

            for member in members:
                send_push(member, datadecoded["body"])

            raise Return()
        message = {'body': datadecoded, 'id': str(uuid.uuid4())}

        for room in self.rooms:
            self.pubclient.publish(room, json.dumps(message))

    def on_close(self):
        for room in self.rooms:
            self.client.unsubscribe(room)

application = tornado.web.Application([
    (r'/msg', WebSocketHandler),
    (r'/', MainHandler),
    (r'/coordinate-sync', CoordinateUpdateHandler)
])


def main():
    tornado.platform.asyncio.AsyncIOMainLoop().install()
    application.listen(8888)
    asyncio.get_event_loop().run_forever()

if __name__ == '__main__':
    main()
