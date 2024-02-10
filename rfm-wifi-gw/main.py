from mqtt_as import MQTTClient, config
from asyncio import run, create_task, sleep, sleep_ms
from rfm69 import RFM69
from machine import SPI, Pin
from json import dumps, loads


# Local configuration

with open('config.json') as fp:
    secrets = loads(fp.read())

config['ssid'] = secrets['wifi_ssid']  # Optional on ESP8266
config['wifi_pw'] = secrets['wifi_pass']
config['server'] = secrets['mqtt_server']  # Change to suit e.g. 'iot.eclipse.org'
config['password'] = secrets['mqtt_pass']
config['user'] = secrets['mqtt_user']
# pins
# init pins
CS = Pin(17, Pin.OUT, value=True)
RESET = Pin(20, Pin.OUT, value=False)
MISO = Pin(16)
MOSI = Pin(19)
SCK = Pin(18)
LED = Pin("LED", Pin.OUT, value=False)
# MY_LED = Pin(LED)
# MY_LED.direction = Direction.OUTPUT
NODES = []


class NodeMsg:
    def __init__(self, msg, client, rfm):
        if msg == "ping":
            fields = [0, 'gw', '2', 'gw', 'O']
        else:
            fields = str(msg, "ascii").split(';')
        # print(fields)
        self.id = fields[0]  # node id
        self.name = fields[1]  
        self.type = fields[2] # 0 - presentation, 1 - state
        self.device = fields[3]
        self.payload = fields[4]
        # print(msg, fields)
        if len(fields) == 6:
            self.node_rssi = float(fields[5])
            print("Node RSSI", self.node_rssi)
        else:
            self.node_rssi = 0
        self.client = client
        self.topic_base = "homeassistant/"+self.device+"/"+self.name
        self.topic_state = self.topic_base+"/state"
        self.topic_cmd = self.topic_base+"/set"
        self.topic_attr = self.topic_base+"/attributes"
        self.rssi = rfm.last_rssi
        self.repulish = False
        self.rfm = rfm
        self.msg = msg
        # self.handle = self.gen_handler()
        print("processing message: ", self.msg)

    async def process(self):
        # print(type(self.type))
        if self.type == "0":
            print("Got presentation message from ", self.name)
            temp_nodes = []
            jmsg = {
                    'name': self.name,
                    'device_class': self.device,
                    'state_topic': self.topic_state,
                    'command_topic': self.topic_cmd,
                    'unique_id': self.name,
                    'payload_on': "ON",
                    'device': {'identifiers': [self.id], 'name': self.name},
                    'json_attributes_topic': self.topic_attr,
                    'json_attributes_template': "{{ value_json.data.value | tojson }}"
                    }
            attr_jmsg = {'Rssi': self.rssi, "NodeRssi": self.node_rssi}
            if len(NODES) > 0:
                # print(NODES)
                for node in NODES:
                    temp_nodes.append(node['id'])
                # print(temp_nodes)
                if self.id not in temp_nodes:
                    print("this is a new node..")
                    try:
                        # setup the node in MQTT
                        await self.client.publish(self.topic_base+"/config", dumps(jmsg), qos=1)
                        await self.client.publish(self.topic_attr, dumps(attr_jmsg), 1)
                        # set the initial state
                        await self.client.publish(self.topic_state, self.payload, qos=1)
                        # subscribe to command topic
                        print("Subscribing to:", self.topic_cmd)
                        await self.client.subscribe(self.topic_cmd, 1)
                        # self.client.add_topic_callback(self.topic_cmd, self.handle_rfm_receivee)
                        NODES.append({'id': self.id, 'topic': self.topic_cmd, 'msg': self.msg})
                    except OSError as err:
                        print("MQTT error:", err)
                else:
                    if self.repulish:
                        # setup the node in MQTT
                        await self.client.publish(self.topic_base+"/config", dumps(jmsg), qos=1)
                        await self.client.publish(self.topic_attr, dumps(attr_jmsg), 1)
                        # set the initial state
                        await self.client.publish(self.topic_state, self.payload, qos=1)
                        # subscribe to command topic
                        print("Subscribing to:", self.topic_cmd)
                        await self.client.subscribe(self.topic_cmd, 1)
                    else:
                        print("Node ", self.id, " already known.")
                        attr_jmsg = {'Rssi': self.rssi, "NodeRssi": self.node_rssi}
                        try:
                            await self.client.publish(self.topic_attr, dumps(attr_jmsg), 1)
                        except OSError as err:
                            print("mqtt error:", err)
                # self.client.add_topic_callback(self.topic_cmd, self.handle)
            else:
                try:
                    # setup the node in mqtt
                    await self.client.publish(self.topic_base+"/config", dumps(jmsg), qos=1)
                    await self.client.publish(self.topic_attr, dumps(attr_jmsg), 1)
                    # set the initial state
                    await self.client.publish(self.topic_state, self.payload, qos=1)
                    # subscribe to command topic
                    await self.client.subscribe(self.topic_cmd, 1)
                    # self.client.add_topic_callback(self.topic_cmd, self.handle)
                    NODES.append({'id': self.id, 'topic': self.topic_cmd, 'msg': self.msg})
                except OSError as err:
                    print("MQTT error:", err)
        elif self.type == "1":
            print("Got status message from node: ", self.name)
            jmsg = self.payload
            attr_jmsg = {'Rssi': self.rssi, "NodeRssi": self.node_rssi}

            try:
                await self.client.publish(self.topic_state, jmsg, 1)
                await self.client.publish(self.topic_attr, dumps(attr_jmsg), 1)
            except OSError as err:
                print("MQTT Error:", err)


def init_rfm69(cs, reset, sck, mosi, miso):
    spi = SPI(0, sck=sck, mosi=mosi, miso=miso)
    rfm = RFM69(spi=spi, nss=cs, reset=reset)
    rfm.frequency_mhz = 433.1
    rfm.node = 0
    rfm.ack_retries = 5
    rfm.encryption_key = (
        b"\x01\x02\x03\x04\x05\x06\x07\x08\x01\x02\x03\x04\x05\x06\x07\x08"
    )
    return rfm


def init_mqtt():
    config["queue_len"] = 10  # Use event interface with default queue size
    MQTTClient.DEBUG = True  # Optional: print diagnostic messages
    client = MQTTClient(config)
    try:
        run(main(client))
    finally:
        client.close()  # Prevent LmacRxBlk:1 errors


async def handle_rfm_receive(rfm, mqtt):
    while True:
        try:
            pkt = rfm.receive(with_ack=True)
            # print("Rssi: ", rfm.rssi)
        except RuntimeError as e:
            print("Got error", e, "Resetting RFM")
            rfm.reset()
            pkt = None
        if pkt is None:
            LED.low()
        else:
            print("Got packet ..", pkt, "Rssi:", rfm.last_rssi)
            LED.high()
            msg = NodeMsg(pkt, mqtt, rfm)
            await msg.process()
        await sleep_ms(1)


async def republish(client, rfm):
    while True:
        if len(NODES) > 0:
            print("Republishing nodes ...")
            for node in NODES:
                print(node)
                msg = NodeMsg(node['msg'], client, rfm)
                msg.repulish = True
                await msg.process()
        await sleep(120)


async def messages(client, rfm):  # Respond to incoming messages
    async for topic, msg, retained in client.queue:
        print((topic.decode('ascii'), msg, retained))
        for node in NODES:
            if topic.decode('ascii') == node['topic']:
                print("sending command to ", node['topic'].split('/')[2],
                      " with payload ", msg.decode('ascii'))
                rfm.destination = int(node['id'])
                if rfm.send_with_ack(msg):
                    print("command sent!")
                else:
                    print("failed to send command!")


async def up(client):  # Respond to connectivity being (re)established
    while True:
        await client.up.wait()  # Wait on an Event
        client.up.clear()
        for node in NODES:
            try:
                await client.subscribe(node['topic'], 1)  # renew subscriptions
            except OSError as err:
                print("Error resubscribing", err)


async def gw_state(client):
    while True:
        print("Sending GW state to mqtt")
        try:
            await client.publish('homeassistant/binary_sensor/upy-gw/state', 'ON', qos=1)
        except OSError as err:
            print("Error sending GW state, ", err)
        await sleep(30)


async def send_ping(rfm):
    while True:
        print("Sending ping to all nodes ..")
        rfm.send_with_ack("ping")
        await sleep(30)


async def gw_present(client):
    while True:
        try:
            await client.publish('homeassistant/binary_sensor/upy-gw/config',
                                 dumps({'name': 'upy-gw', 
                                        'device_class': 'running',
                                        'state_topic': 'homeassistant/binary_sensor/upy-gw/state',
                                        'command_topic': 'homeassistant/binary_sensor/upy-gw/set',
                                        'unique_id': 'upy-gw',
                                        'device': {'identifiers': ["gw01"], 'name': "upy_gw01"}}))
        except OSError as err:
            print("Error republishing GW", err)
        await sleep(60)


async def main(client):
    print("Starting up ...")
    print("Initialising RFM Radio ...")
    rfm = init_rfm69(CS, RESET, SCK, MOSI, MISO)
    print("RFM OK")
    print("Connecting to MQTT Broker ...")
    await client.connect()

    # start the async tasks
    create_task(up(client))
    create_task(messages(client, rfm))
    create_task(handle_rfm_receive(rfm, client))
    create_task(gw_state(client))
    create_task(send_ping(rfm))
    create_task(gw_present(client))
    create_task(republish(client, rfm))

    while True:
        await sleep(0.5)
        LED.toggle()
        # If WiFi is down the following will pause for the duration.
        # await sleep(1)
        # print('publishing state Stopped')
        # # If WiFi is down the following will pause for the duration.
        # await client.publish('homeassistant/binary_sensor/upy-gw/state', 'OFF', qos=1)

init_mqtt()
