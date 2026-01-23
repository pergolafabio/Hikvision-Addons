# cmd: python3 hikvision_register.py --ip 192.168.0.17 --domain 192.168.0.71 --username 10000000005 --extension 10000000005 --name Asterisk --password XXX --debug
# If above command works, drop the "--debug" , no needed, 192.1680.17 = host , 192.168.0.71 = primary indoor panel
# First register an extension on your primary indoor, use serial: Q12345678 , and use number 5 (10000000005), setup same password as in command above
#

# -*- coding: utf-8 -*-
import sys
import socket
import requests
import re
import random
import hashlib
import threading
import time
import logging
_logger = logging.getLogger("sip-server")

class Packet(list):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.body = ""
        self.status_line = ""

    def get_by_name(self, name):
        for key, value in self:
            if key == name:
                return value
        raise LookupError(f"No header called {name}")

    def get_many_by_name(self, name):
        for key, value in self:
            if key == name:
                yield value

    @staticmethod
    def parse(data: str) -> "Packet":
        headers = Packet()
        lines = data.splitlines()
        headers.status_line = lines[0]
        idx = 0
        for idx, line in enumerate(lines[1:]):
            if not line:
                break
            key, value = line.split(":", 1)
            headers.set_header(key, value.strip())
        headers.body = "\n".join(lines[idx + 1:])
        return headers

    def __str__(self):
        result = self.status_line + "\r\n"
        for key, value in self:
            result += f"{key}: {value}\r\n"
        result += "\r\n" + self.body
        return result

    def set_header(self, name, value, replace=False):
        if replace:
            for idx, (header, _) in enumerate(self):
                if header == name:
                    self[idx] = (header, value)
                    return
        self.append((name, value))

class SIPSession:
    USER_AGENT = "eXosip/3.6.0"
    rtp_threads = []
    sip_history = {}
    
    def __init__(self, ip, username, domain, password, auth_username=False, account_port=5061, display_name="-"):
        self.ip = ip
        self.username = username
        domain_port = domain.split(":", 1)
        if len(domain_port) == 2:
            self.domain_port = int(domain_port[1])
        else:
            self.domain_port = 5065
        self.domain = domain_port[0]
        self.password = password
        self.auth_username = auth_username
        self.account_port = account_port
        self.display_name = display_name
        self.call_accepted = EventHook()
        self.call_rejected = EventHook()
        self.call_ended = EventHook()
        self.call_error = EventHook()        
        self.call_ringing = EventHook()
        self.call_registered = EventHook()
        self.message_sent = EventHook()
        self.message_received = EventHook()

        self.sipsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sipsocket.bind(("0.0.0.0", account_port))
        self.bind_port = self.sipsocket.getsockname()[1]
        self.register_packet: Packet = Packet()

        #Don't block the main thread with all the listening
        sip_listener_starter = threading.Thread(target=self.sip_listener, args=())
        sip_listener_starter.start()

    @staticmethod
    def H(data):
        return hashlib.md5(data.encode("utf-8")).hexdigest()

    @staticmethod
    def KD(secret, data):
        return SIPSession.H(secret + ":" + data)
        
    def http_auth(self, authheader, method, address):
        realm = re.findall(r'realm="(.*?)"', authheader)[0]
        uri = "sip:" + address + ":5065"
        nonce = re.findall(r'nonce="(.*?)"', authheader)[0]
        opaque = re.findall(r'opaque="(.*?)"', authheader)[0]

        if self.auth_username:
            username = self.auth_username
        else:
            username = self.username
            
        A1 = username + ":" + realm + ":" + self.password
        A2 = method + ":" + uri

        if "qop=" in authheader:
            qop = re.findall(r'qop="(.*?)"', authheader)[0]
            nc = "00000001"
            cnonce = ''.join([random.choice('0123456789abcdef') for x in range(32)])
            response = self.KD( self.H(A1), nonce + ":" + nc + ":" + cnonce + ":" + qop + ":" + self.H(A2) )
            return f'Digest username="{username}",realm="{realm}",nonce="{nonce}",uri="{uri}",response="{response}",cnonce="{cnonce}",nc={nc},qop=auth,algorithm=MD5\r\n'
        else:
            response = self.KD( self.H(A1), nonce + ":" + self.H(A2) )
            return f'Digest username="{username}",realm="{realm}",nonce="{nonce}",uri="{uri}",response="{response}",algorithm=MD5,opaque="{opaque}"'

    def answer_call(self, sip_invite, sdp):
        packet = Packet.parse(sip_invite)
        call_id = packet.get_by_name("Call-ID")
        call_from = packet.get_by_name("From")
        call_to = packet.get_by_name("To")

        reply = Packet()
        for via_heading in packet.get_many_by_name("Via"):
            reply.set_header("Via", via_heading)
        for record_route in packet.get_many_by_name("Record-Route"):
            reply.set_header("Record-Route", record_route)
        reply.set_header("Contact", f'<sip:{self.username}"@{self.ip}:{self.bind_port}')
        reply.set_header("To", call_to)
        reply.set_header("From", call_from)
        reply.set_header("Call-ID", call_id)
        reply.set_header("CSeq", "1 INVITE")
        reply.set_header("Allow", "SUBSCRIBE, NOTIFY, INVITE, ACK, CANCEL, BYE, REFER, INFO, OPTIONS, MESSAGE")
        reply.set_header("Content-Type", "application/sdp")
        reply.set_header("Supported", "replaces")
        reply.set_header("User-Agent", self.USER_AGENT)
        reply.body = sdp
        reply.status_line = "SIP/2.0 200 OK"
        self.send_packet(reply)

    def send_packet(self, packet: Packet, addr=None):
        packet.set_header("Content-Length", str(len(packet.body) if packet.body else 0), True)
        _logger.debug(">%s", packet)
        if addr is None:
            addr = (self.to_server, self.domain_port)
        self.sipsocket.sendto(str(packet).encode("utf-8"), addr)

    def send_sip_message(self, to_address, message_body):
        call_id = self.get_call_id()
        message = Packet()
        message.status_line = f"MESSAGE sip:{self.username}@{self.domain} SIP/2.0"
        message.set_header("Via", f"SIP/2.0/UDP {self.ip}:{self.bind_port};rport")
        message.set_header("Max-Forwards", "70")
        message.set_header("To", f"<sip:{to_address}>;messagetype=IM")
        message.set_header('From', f'"{self.display_name}"<sip:{self.username}@{self.domain}:{self.domain_port}>')
        message.set_header("Call-ID", call_id)
        message.set_header("CSeq", "1 MESSAGE")
        message.set_header("Allow", "SUBSCRIBE, NOTIFY, INVITE, ACK, CANCEL, BYE, REFER, INFO, OPTIONS, MESSAGE")
        message.set_header("Content-Type", "text/html")
        message.set_header("User-Agent", str(self.USER_AGENT))
        message.body = message_body

        to_server = self.domain
        self.send_packet(message, (to_server, self.account_port))
        self.sip_history[call_id] = []
        self.sip_history[call_id].append(message)
        return call_id

    def get_call_id(self):
        return ''.join([random.choice('0123456789') for _ in range(10)])
        
    def send_sip_register(self, register_frequency=600):
        self.register_packet = Packet()
        call_id = self.get_call_id()
        self.register_packet.set_header("Via", f"SIP/2.0/UDP {self.ip}:{self.bind_port};rport")
        self.register_packet.set_header("Max-Forwards", "70")
        self.register_packet.set_header("Contact", f"<sip:{self.username}@{self.ip}:{self.bind_port}>")
        self.register_packet.set_header("To", f'""<sip:{self.username}@{self.domain}:{self.domain_port}>')
        self.register_packet.set_header("From", f'"{self.display_name}"<sip:{self.username}@{self.domain}:{self.domain_port}>')
        self.register_packet.set_header("Call-ID", call_id)
        self.register_packet.set_header("CSeq", "1 REGISTER")
        self.register_packet.set_header("Expires", str(register_frequency))
        self.register_packet.set_header("Allow", "NOTIFY, INVITE, ACK, CANCEL, BYE, REFER, INFO, OPTIONS, MESSAGE")
        self.register_packet.set_header("Content-Type", "text/xml")
        self.register_packet.set_header("User-Agent", str(self.USER_AGENT))
        self.register_packet.body = '''\
<regXML>
<version>V2.0.0</version>
<regDevName>Asterisk</regDevName>
<regDevSerial>Q12345678</regDevSerial>
<regDevMacAddr>00:0c:29:12:12:12</regDevMacAddr>
</regXML>'''
        self.register_packet.status_line = f"REGISTER sip:{self.domain}:{self.account_port} SIP/2.0"

        self.to_server = self.domain

        self.sip_history[call_id] = []
        self.sip_history[call_id].append(self.register_packet)

        #Reregister to keep the session alive
        reregister_starter = threading.Thread(target=self.reregister, args=(register_frequency,))
        reregister_starter.start()
        
    def reregister(self, register_frequency):
        while True:
            _logger.info("Registering")
            self.send_packet(self.register_packet)
            time.sleep(register_frequency)
        
    def send_sip_invite(self, to_address, call_sdp):
        call_id = self.get_call_id()
        invite = Packet()
        invite.status_line = f"INVITE sip:{to_address}:{self.account_port} SIP/2.0"
        invite.set_header("Via", f"SIP/2.0/UDP {self.ip}:{self.bind_port};rport")
        invite.set_header("Max-Forwards", "70")
        invite.set_header("Contact", f"<sip:{self.username}@{self.ip}:{self.bind_port}>")
        invite.set_header("To", f"<sip:{to_address}:{self.account_port}>")
        invite.set_header("From", f'"{self.display_name}"<sip:{self.username}@{self.domain}:{self.account_port}>')
        invite.set_header("Call-ID", str(call_id))
        invite.set_header("CSeq", "1 INVITE")
        invite.set_header("Allow", "SUBSCRIBE, NOTIFY, INVITE, ACK, CANCEL, BYE, REFER, INFO, OPTIONS, MESSAGE")
        invite.set_header("Content-Type", "application/sdp")
        invite.set_header("Supported", "replaces")
        invite.set_header("User-Agent", str(self.USER_AGENT))
        invite.body = call_sdp
        self.send_packet(invite)

        self.sip_history[call_id] = []
        self.sip_history[call_id].append(invite)
        return call_id
        
    def sip_listener(self):
        try:
            #Wait and send back the auth reply
            stage = "WAITING"
            while stage == "WAITING":
                data, addr = self.sipsocket.recvfrom(2048)
                data = data.decode("utf-8")
                _logger.debug(data)

                try:
                    packet = Packet.parse(data)
                except Exception as e:
                    _logger.exception(e)
                    continue

                #Send auth response if challenged
                if packet.status_line == "SIP/2.0 401 Unauthorized":
                    _logger.info("Handling authentication")
                    authheader = packet.get_by_name("WWW-Authenticate")
                    call_id = packet.get_by_name("Call-ID")
                    cseq = packet.get_by_name("CSeq")
                    cseq_number, cseq_type = cseq.split(" ", 1)
                    call_to_full = packet.get_by_name("To")
                    call_to = re.findall(r'<sip:(.*?)>', call_to_full)[0]
                    if ":" in call_to: call_to = call_to.split(":")[0]
                    
                    #Resend the initial message but with the auth_string
                    auth_string = self.http_auth(authheader, cseq_type, call_to)
                    self.register_packet.set_header("CSeq", f"{int(cseq_number) + 1} {cseq_type}", True)

                    self.register_packet.insert(5, ("Authorization", auth_string))
                    self.send_packet(self.register_packet, addr)
                elif packet.status_line == "SIP/2.0 403 Forbidden":
                    #Likely means call was rejected
                    _logger.info("We are unauthorized")
                    self.call_rejected.fire(self, data)
                    stage = "Forbidden"
                    return False
                elif data.startswith("MESSAGE"):
                    #Extract the actual message to make things easier for devs
                    message = data.split("\r\n\r\n")[1]
                    if "<isComposing" not in message:
                        _logger.info("Message received")
                        _logger.debug(message)
                        self.message_received.fire(self, data, message)
                elif data.startswith("INVITE"):
                    _logger.info("Received invite (call)")
                    call_from = packet.get_by_name("From")
                    call_to = packet.get_by_name("To")
                    call_id = packet.get_by_name("Call-ID")

                    #Send Trying
                    trying = Packet()
                    trying.status_line = "SIP/2.0 100 Trying"
                    for (via_heading) in packet.get_many_by_name("Via"):
                        trying.set_header("Via", via_heading)
                    trying.set_header("To", call_to)
                    trying.set_header("From", call_from)
                    trying.set_header("Call-ID", call_id)
                    trying.set_header("CSeq", "1 INVITE")
                    self.send_packet(trying, addr)

                    #Even automated calls can take a second to get ready to answer
                    ringing = Packet()
                    ringing.status_line = "SIP/2.0 180 Ringing"
                    for (via_heading) in packet.get_many_by_name("Via"):
                        ringing.set_header("Via", via_heading)
                    for (record_heading) in packet.get_many_by_name("Record-Route"):
                        ringing.set_header("Record-Route", record_heading)
                    ringing.set_header("Contact", f"<sip:{self.username}@{self.ip}:{self.bind_port}>")
                    ringing.set_header("To", call_to)
                    ringing.set_header("From", call_from)
                    ringing.set_header("Call-ID", str(call_id))
                    ringing.set_header("CSeq", "1 INVITE")
                    ringing.set_header("User-Agent", str(self.USER_AGENT))
                    ringing.set_header("Allow-Events", "talk, hold")
                    self.send_packet(ringing, addr)

                    self.call_ringing.fire(self, data)
                elif data.startswith("BYE"):
                    #Do stuff when the call is ended by client
                    _logger.info("Call ended by us")
                    self.call_ended.fire(data)
                elif packet.status_line.startswith("CANCEL"):
                    #Do stuff when the call is ended by client
                    _logger.info("Call ended by caller")
                    call_from = packet.get_by_name("From")
                    call_to = packet.get_by_name("To")
                    call_id = packet.get_by_name("Call-ID")
                    cseq = packet.get_by_name("CSeq")
                    cseq_number, cseq_type = cseq.split(" ", 1)
                    reply = Packet()
                    reply.status_line = "SIP/2.0 200 OK"
                    reply.set_header("Contact", f"<sip:{self.username}@{self.ip}:{self.bind_port}>")
                    reply.set_header("To", call_to)
                    reply.set_header("From", call_from)
                    reply.set_header("Call-ID", str(call_id))
                    reply.set_header("CSeq", f"{cseq_number} CANCEL")
                    reply.set_header("User-Agent", str(self.USER_AGENT))
                    reply.set_header("Allow-Events", "talk, hold")
                    self.send_packet(reply, addr)
                    self.call_ended.fire(packet)
                elif packet.status_line == "SIP/2.0 200 OK":
                    cseq = packet.get_by_name("CSeq")
                    cseq_number, cseq_type = cseq.split(" ", 1)
                    _logger.info("OK %s", cseq_type)
                
                    #200 OK is used by REGISTER, INVITE and MESSAGE, so the code logic gets split up
                    if cseq_type == "INVITE":
                        contact_header = packet.get_by_name("Contact")
                        record_route = packet.get_by_name("Record-Route")
                        call_from = packet.get_by_name("From")
                        call_to = packet.get_by_name("To")
                        call_id = packet.get_by_name("Call-ID")

                        #Send the ACK
                        reply = Packet()
                        reply.status_line = f"ACK {contact_header} SIP/2.0"
                        reply.set_header("Via", f"SIP/2.0/UDP {self.ip}:{self.bind_port};rport")
                        reply.set_header("Max-Forwards", "70")
                        reply.set_header("Route", record_route)
                        reply.set_header("Contact", f"<sip:{self.username}@{self.ip}:{self.bind_port}>")
                        reply.set_header('To', call_to)
                        reply.set_header("From", call_from)
                        reply.set_header("Call-ID", str(call_id))
                        reply.set_header("CSeq", f"{cseq_number} ACK")
                        reply.set_header("User-Agent", str(self.USER_AGENT))
                        self.send_packet(reply, addr)
                        self.call_accepted.fire(self, packet)
                    elif cseq_type == "MESSAGE":
                        self.message_sent.fire(self, data)                    
                    elif cseq_type == "REGISTER":
                        self.call_registered.fire(self, data)
                elif packet.status_line.startswith("SIP/2.0 4"):
                    _logger.info("Error: %s", data)
                    self.call_error.fire(self, data)
                else:
                    _logger.info("Unhandled data: %s", data)
        
        except Exception as e:
            _logger.exception(e)
            
                
class EventHook:
    def __init__(self):
        self.__handlers = []

    def __iadd__(self, handler):
        self.__handlers.append(handler)
        return self

    def __isub__(self, handler):
        self.__handlers.remove(handler)
        return self

    def fire(self, *args, **keywargs):
        for handler in self.__handlers:
            handler(*args, **keywargs)

    def clearObjectHandlers(self, inObject):
        for theHandler in self.__handlers:
            if theHandler.im_self == inObject:
                self -= theHandler
                

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", help="Local IP Address", required=True)
    parser.add_argument("--password", help="Password if required")
    parser.add_argument("--username", help="Usernamew")
    parser.add_argument("--domain", help="IP/Domain to connect to")
    parser.add_argument("--debug", action="store_true", default=False, help="Print debug output")
    parser.add_argument("--name", help="Name to deploy", default="robot")
    parser.add_argument("--extension", help="Extension number", default="10000000003")
    parser.add_argument("--token", help="HA Token")
    parser.add_argument("--state-url")
    def update_state(state):
        if options.token:
            session.post(options.state_url, json={"state": state})
    options = parser.parse_args()
    session = requests.Session()
    if options.token:
        session.headers["Authorization"] = f"Bearer {options.token}"
    if options.debug:
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    else:
        logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    update_state("init")
    sip_session = SIPSession(options.ip, options.extension, options.domain, options.password, options.username, display_name=options.name)
    sip_session.call_registered += lambda *_: update_state("registered")
    sip_session.call_ringing += lambda *_: update_state("ringing")
    sip_session.call_ended += lambda *_: update_state("registered")
    sip_session.send_sip_register()

    
