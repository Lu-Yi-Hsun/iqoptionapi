"""Module for IQ Option API."""

import time
import json
import logging
import math
import threading
import requests
import ssl
import atexit
from collections import deque
from iqoptionapi.http.login import Login
from iqoptionapi.http.loginv2 import Loginv2
from iqoptionapi.http.logout import Logout
from iqoptionapi.http.getprofile import Getprofile
from iqoptionapi.http.auth import Auth
from iqoptionapi.http.token import Token
from iqoptionapi.http.appinit import Appinit
from iqoptionapi.http.billing import Billing
from iqoptionapi.http.buyback import Buyback
from iqoptionapi.http.changebalance import Changebalance
from iqoptionapi.http.events import Events
from iqoptionapi.ws.client import WebsocketClient
from iqoptionapi.ws.chanels.get_balances import *

from iqoptionapi.ws.chanels.ssid import Ssid
from iqoptionapi.ws.chanels.subscribe import *
from iqoptionapi.ws.chanels.unsubscribe import *
from iqoptionapi.ws.chanels.setactives import SetActives
from iqoptionapi.ws.chanels.candles import GetCandles
from iqoptionapi.ws.chanels.buyv2 import Buyv2
from iqoptionapi.ws.chanels.buyv3 import *
from iqoptionapi.ws.chanels.user import *
from iqoptionapi.ws.chanels.api_game_betinfo import Game_betinfo
from iqoptionapi.ws.chanels.instruments import Get_instruments
from iqoptionapi.ws.chanels.get_financial_information import GetFinancialInformation
from iqoptionapi.ws.chanels.strike_list import Strike_list
from iqoptionapi.ws.chanels.leaderboard import Leader_Board

from iqoptionapi.ws.chanels.traders_mood import Traders_mood_subscribe
from iqoptionapi.ws.chanels.traders_mood import Traders_mood_unsubscribe
from iqoptionapi.ws.chanels.buy_place_order_temp import Buy_place_order_temp
from iqoptionapi.ws.chanels.get_order import Get_order
from iqoptionapi.ws.chanels.get_deferred_orders import GetDeferredOrders
from iqoptionapi.ws.chanels.get_positions import *
 
from iqoptionapi.ws.chanels.get_available_leverages import Get_available_leverages
from iqoptionapi.ws.chanels.cancel_order import Cancel_order
from iqoptionapi.ws.chanels.close_position import Close_position
from iqoptionapi.ws.chanels.get_overnight_fee import Get_overnight_fee
from iqoptionapi.ws.chanels.heartbeat import Heartbeat

 
from iqoptionapi.ws.chanels.digital_option import *
from iqoptionapi.ws.chanels.api_game_getoptions import *
from iqoptionapi.ws.chanels.sell_option import Sell_Option
from iqoptionapi.ws.chanels.change_tpsl import Change_Tpsl
from iqoptionapi.ws.chanels.change_auto_margin_call import ChangeAutoMarginCall

from iqoptionapi.ws.objects.timesync import TimeSync
from iqoptionapi.ws.objects.profile import Profile
from iqoptionapi.ws.objects.candles import Candles
from iqoptionapi.ws.objects.listinfodata import ListInfoData
from iqoptionapi.ws.objects.betinfo import Game_betinfo_data
import iqoptionapi.global_value as global_value
from collections import defaultdict


_DEFAULT_HTTP_REQUEST_TIMEOUT = 30
_SENSITIVE_HTTP_KEYS = (
    "authorization",
    "cookie",
    "password",
    "set-cookie",
    "ssid",
    "token",
)


def _redact_http_mapping(value, redact_all=False):
    if value is None:
        return None
    try:
        items = value.items()
    except AttributeError:
        return "<redacted>" if redact_all else value
    return {
        key: (
            "<redacted>"
            if redact_all or any(marker in str(key).lower() for marker in _SENSITIVE_HTTP_KEYS)
            else item_value
        )
        for key, item_value in items
    }


def _redact_http_cookies(value):
    try:
        value = value.get_dict()
    except AttributeError:
        pass
    return _redact_http_mapping(value, redact_all=True)


def _normalize_http_request_timeout(timeout):
    try:
        timeout = float(timeout)
    except (TypeError, ValueError):
        raise ValueError("request_timeout must be a positive number")
    if timeout <= 0 or not math.isfinite(timeout):
        raise ValueError("request_timeout must be a positive number")
    return timeout


def nested_dict(n, type):
    if n == 1:
        return defaultdict(type)
    else:
        return defaultdict(lambda: nested_dict(n-1, type))


# InsecureRequestWarning: Unverified HTTPS request is being made.
# Adding certificate verification is strongly advised.
# See: https://urllib3.readthedocs.org/en/latest/security.html
requests.packages.urllib3.disable_warnings()  # pylint: disable=no-member


class IQOptionAPI(object):  # pylint: disable=too-many-instance-attributes
    """Class for communication with IQ Option API."""
     
    # pylint: disable=too-many-public-methods
    # Runtime state is initialized in __init__. Keeping mutable caches on the
    # class object makes independent broker sessions leak data into each other.

    def __init__(self, host, username, password, proxies=None, request_timeout=_DEFAULT_HTTP_REQUEST_TIMEOUT):
        """
        :param str host: The hostname or ip address of a IQ Option server.
        :param str username: The username of a IQ Option server.
        :param str password: The password of a IQ Option server.
        :param dict proxies: (optional) The http request proxies.
        :param float request_timeout: (optional) Timeout for HTTP requests.
        """
        self.https_url = "https://{host}/api".format(host=host)
        self.wss_url = "wss://{host}/echo/websocket".format(host=host)
        self.websocket_client = None
        self._send_lock = threading.Lock()
        self.websocket_last_message_error = None
        self.closed_option_last_error = None
        self.http_last_request = None
        self.http_last_error = None
        self.socket_option_opened = {}
        self.socket_option_closed = {}
        self.timesync = TimeSync()
        self.profile = Profile()
        self.candles = Candles()
        self.listinfodata = ListInfoData()
        self.api_option_init_all_result = []
        self.api_option_init_all_result_v2 = []
        self.underlying_list_data = None
        self.position_changed = None
        self.instrument_quites_generated_data = nested_dict(2, dict)
        self.instrument_quotes_generated_raw_data = nested_dict(2, dict)
        self.instrument_quites_generated_timestamp = nested_dict(2, dict)
        self.strike_list = None
        self.leaderboard_deals_client = None
        self.order_async = nested_dict(2, dict)
        self.game_betinfo = Game_betinfo_data()
        self.instruments = None
        self.financial_information = None
        self.buy_id = None
        self.buy_order_id = None
        self.traders_mood = {}
        self.order_data = None
        self.positions = None
        self.position = None
        self.deferred_orders = None
        self.position_history = None
        self.position_history_v2 = None
        self.available_leverages = None
        self.order_canceled = None
        self.close_position_data = None
        self.overnight_fee = None
        self.digital_option_placed_id = None
        self.live_deal_data = nested_dict(3, deque)
        self.subscribe_commission_changed_data = nested_dict(2, dict)
        self.real_time_candles = nested_dict(3, dict)
        self.real_time_candles_maxdict_table = nested_dict(2, dict)
        self.candle_generated_check = nested_dict(2, dict)
        self.candle_generated_all_size_check = nested_dict(1, dict)
        self.api_game_getoptions_result = None
        self.sold_options_respond = None
        self.tpsl_changed_respond = None
        self.auto_margin_call_changed_respond = None
        self.top_assets_updated_data = {}
        self.get_options_v2_data = None
        self.buy_multi_result = None
        self.buy_multi_option = {}
        self.result = None
        self.training_balance_reset_request = None
        self.balances_raw = None
        self.user_profile_client = None
        self.leaderboard_userinfo_deals_client = None
        self.users_availability = None
        self.session = requests.Session()
        self.session.verify = False
        self.session.trust_env = False
        self.username = username
        self.password = password
        self.proxies = proxies
        self.request_timeout = _normalize_http_request_timeout(request_timeout)
        # is used to determine if a buyOrder was set  or failed. If
        # it is None, there had been no buy order yet or just send.
        # If it is false, the last failed
        # If it is true, the last buy order was successful
        self.buy_successful = None

    def prepare_http_url(self, resource):
        """Construct http url from resource url.

        :param resource: The instance of
            :class:`Resource <iqoptionapi.http.resource.Resource>`.

        :returns: The full url to IQ Option http resource.
        """
        return "/".join((self.https_url, resource.url))

    def send_http_request(self, resource, method, data=None, params=None, headers=None):  # pylint: disable=too-many-arguments
        """Send http request to IQ Option server.

        :param resource: The instance of
            :class:`Resource <iqoptionapi.http.resource.Resource>`.
        :param str method: The http request method.
        :param dict data: (optional) The http request data.
        :param dict params: (optional) The http request params.
        :param dict headers: (optional) The http request headers.

        :returns: The instance of :class:`Response <requests.Response>`.
        """
        logger = logging.getLogger(__name__)
        url = self.prepare_http_url(resource)

        logger.debug(url)
        self.http_last_request = {
            "method": method,
            "url": url,
            "timeout": self.request_timeout,
        }
        self.http_last_error = None

        try:
            response = self.session.request(method=method,
                                            url=url,
                                            data=data,
                                            params=params,
                                            headers=headers,
                                            proxies=self.proxies,
                                            timeout=self.request_timeout)
            response.raise_for_status()
        except Exception as exc:
            self.http_last_error = {
                "type": type(exc).__name__,
                "message": str(exc),
                "method": method,
                "url": url,
                "timeout": self.request_timeout,
            }
            raise
        logger.debug(response)
        logger.debug(response.text)
        logger.debug("response headers: %s", _redact_http_mapping(response.headers))
        logger.debug("response cookies: %s", _redact_http_cookies(response.cookies))
        return response

    def send_http_request_v2(self, url, method, data=None, params=None, headers=None):  # pylint: disable=too-many-arguments
        """Send http request to IQ Option server.

        :param resource: The instance of
            :class:`Resource <iqoptionapi.http.resource.Resource>`.
        :param str method: The http request method.
        :param dict data: (optional) The http request data.
        :param dict params: (optional) The http request params.
        :param dict headers: (optional) The http request headers.

        :returns: The instance of :class:`Response <requests.Response>`.
        """
        logger = logging.getLogger(__name__)

        logger.debug(
            "%s: %s headers: %s cookies: %s",
            method,
            url,
            _redact_http_mapping(self.session.headers),
            _redact_http_mapping(self.session.cookies.get_dict(), redact_all=True),
        )
        self.http_last_request = {
            "method": method,
            "url": url,
            "timeout": self.request_timeout,
        }
        self.http_last_error = None
        
        try:
            response = self.session.request(method=method,
                                            url=url,
                                            data=data,
                                            params=params,
                                            headers=headers,
                                            proxies=self.proxies,
                                            timeout=self.request_timeout)
        except Exception as exc:
            self.http_last_error = {
                "type": type(exc).__name__,
                "message": str(exc),
                "method": method,
                "url": url,
                "timeout": self.request_timeout,
            }
            raise
        logger.debug(response)
        logger.debug(response.text)
        logger.debug("response headers: %s", _redact_http_mapping(response.headers))
        logger.debug("response cookies: %s", _redact_http_cookies(response.cookies))

        #response.raise_for_status()
        return response

    @property
    def websocket(self):
        """Property to get websocket.

        :returns: The instance of :class:`WebSocket <websocket.WebSocket>`.
        """
        return self.websocket_client.wss

    def send_websocket_request(self, name, msg, request_id="",no_force_send=True):
        """Send websocket request to IQ Option server.

        :param str name: The websocket request name.
        :param dict msg: The websocket request msg.
        """
        
        logger = logging.getLogger(__name__)

        data = json.dumps(dict(name=name,
                               msg=msg, request_id=request_id))
         
         
        send_lock = getattr(self, "_send_lock", None)
        if send_lock is None:
            self._send_lock = threading.Lock()
            send_lock = self._send_lock
        with send_lock:
            while (global_value.ssl_Mutual_exclusion or global_value.ssl_Mutual_exclusion_write) and no_force_send:
                time.sleep(0.001)
            global_value.ssl_Mutual_exclusion_write=True
            try:
                self.websocket.send(data)
                logger.debug(data)
            finally:
                global_value.ssl_Mutual_exclusion_write=False
        
    @property
    def logout(self):
        """Property for get IQ Option http login resource.

        :returns: The instance of :class:`Login
            <iqoptionapi.http.login.Login>`.
        """
        return Logout(self)
    
    @property
    def login(self):
        """Property for get IQ Option http login resource.

        :returns: The instance of :class:`Login
            <iqoptionapi.http.login.Login>`.
        """
        return Login(self)

    @property
    def loginv2(self):
        """Property for get IQ Option http loginv2 resource.

        :returns: The instance of :class:`Loginv2
            <iqoptionapi.http.loginv2.Loginv2>`.
        """
        return Loginv2(self)

    @property
    def auth(self):
        """Property for get IQ Option http auth resource.

        :returns: The instance of :class:`Auth
            <iqoptionapi.http.auth.Auth>`.
        """
        return Auth(self)

    @property
    def appinit(self):
        """Property for get IQ Option http appinit resource.

        :returns: The instance of :class:`Appinit
            <iqoptionapi.http.appinit.Appinit>`.
        """
        return Appinit(self)

    @property
    def token(self):
        """Property for get IQ Option http token resource.

        :returns: The instance of :class:`Token
            <iqoptionapi.http.auth.Token>`.
        """
        return Token(self)

    # @property
    # def profile(self):
    #     """Property for get IQ Option http profile resource.

    #     :returns: The instance of :class:`Profile
    #         <iqoptionapi.http.profile.Profile>`.
    #     """
    #     return Profile(self)
    def reset_training_balance(self):
        # sendResults True/False
        # {"name":"sendMessage","request_id":"142","msg":{"name":"reset-training-balance","version":"2.0"}}
         
        self.send_websocket_request(name="sendMessage",msg={"name": "reset-training-balance",
                                    "version": "2.0"})
      

    @property
    def changebalance(self):
        """Property for get IQ Option http changebalance resource.

        :returns: The instance of :class:`Changebalance
            <iqoptionapi.http.changebalance.Changebalance>`.
        """
        return Changebalance(self)
    @property
    def events(self):
        return Events(self)
    @property
    def billing(self):
        """Property for get IQ Option http billing resource.

        :returns: The instance of :class:`Billing
            <iqoptionapi.http.billing.Billing>`.
        """
        return Billing(self)

    @property
    def buyback(self):
        """Property for get IQ Option http buyback resource.

        :returns: The instance of :class:`Buyback
            <iqoptionapi.http.buyback.Buyback>`.
        """
        return Buyback(self)
# ------------------------------------------------------------------------

    @property
    def getprofile(self):
        """Property for get IQ Option http getprofile resource.

        :returns: The instance of :class:`Login
            <iqoptionapi.http.getprofile.Getprofile>`.
        """
        return Getprofile(self)
# for active code ...
    @property
    def get_balances(self):
        """Property for get IQ Option http getprofile resource.

        :returns: The instance of :class:`Login
            <iqoptionapi.http.getprofile.Getprofile>`.
        """
        return Get_Balances(self)

    @property
    def get_instruments(self):
        return Get_instruments(self)

    @property
    def get_financial_information(self):
        return GetFinancialInformation(self)
# ----------------------------------------------------------------------------

    @property
    def ssid(self):
        """Property for get IQ Option websocket ssid chanel.

        :returns: The instance of :class:`Ssid
            <iqoptionapi.ws.chanels.ssid.Ssid>`.
        """
        return Ssid(self)
# --------------------------------------------------------------------------------
    @property
    def Subscribe_Live_Deal(self):
        return Subscribe_live_deal(self)
    @property
    def Unscribe_Live_Deal(self):
        return Unscribe_live_deal(self)
# --------------------------------------------------------------------------------
# trader mood

    @property
    def subscribe_Traders_mood(self):
        return Traders_mood_subscribe(self)

    @property
    def unsubscribe_Traders_mood(self):
        return Traders_mood_unsubscribe(self)

# --------------------------------------------------------------------------------
# --------------------------subscribe&unsubscribe---------------------------------
# --------------------------------------------------------------------------------
    @property
    def subscribe(self):
        "candle-generated"
        """Property for get IQ Option websocket subscribe chanel.

        :returns: The instance of :class:`Subscribe
            <iqoptionapi.ws.chanels.subscribe.Subscribe>`.
        """
        return Subscribe(self)

    @property
    def subscribe_all_size(self):
        return Subscribe_candles(self)

    @property
    def unsubscribe(self):
        """Property for get IQ Option websocket unsubscribe chanel.

        :returns: The instance of :class:`Unsubscribe
            <iqoptionapi.ws.chanels.unsubscribe.Unsubscribe>`.
        """
        return Unsubscribe(self)

    @property
    def unsubscribe_all_size(self):
        return Unsubscribe_candles(self)


    def portfolio(self,Main_Name,name,instrument_type,user_balance_id="",limit=1,offset=0,request_id=""):
        #Main name:"unsubscribeMessage"/"subscribeMessage"/"sendMessage"(only for portfolio.get-positions")
        #name:"portfolio.order-changed"/"portfolio.get-positions"/"portfolio.position-changed"
        #instrument_type="cfd"/"forex"/"crypto"/"digital-option"/"turbo-option"/"binary-option"
        logger = logging.getLogger(__name__)
        M_name=Main_Name
        request_id=str(request_id)
        if name=="portfolio.order-changed":               
            msg={"name": name,
                    "version": "1.0",
                    "params": {
                        "routingFilters": {"instrument_type": str(instrument_type)}
                    }
                    }
                               
        elif name=="portfolio.get-positions":                
            msg={"name": name,
                    "version": "3.0",
                    "body": {
                            "instrument_type": str(instrument_type),
                            "limit":int(limit),
                            "offset":int(offset)
                        }
                    }
                              
             
        elif name=="portfolio.position-changed": 
            msg={"name": name,
                "version": "2.0",
                "params": {
                    "routingFilters": {"instrument_type": str(instrument_type),
                                        "user_balance_id":user_balance_id    
                               
                                      }
                          }
                }
         
        self.send_websocket_request(name=M_name,msg=msg,request_id=request_id)
        
    def set_user_settings(self,balanceId,request_id=""):
        #Main name:"unsubscribeMessage"/"subscribeMessage"/"sendMessage"(only for portfolio.get-positions")
        #name:"portfolio.order-changed"/"portfolio.get-positions"/"portfolio.position-changed"
        #instrument_type="cfd"/"forex"/"crypto"/"digital-option"/"turbo-option"/"binary-option"
       
        msg={"name": "set-user-settings",
            "version": "1.0",
            "body": {
                    "name":"traderoom_gl_common",
                    "version":3,
                    "config":{
                                "balanceId":balanceId

                                }

                    }
            }
        self.send_websocket_request(name="sendMessage",msg=msg,request_id=str(request_id))
    



    def subscribe_position_changed(self, name, instrument_type, request_id):
        # instrument_type="multi-option","crypto","forex","cfd"
        # name="position-changed","trading-fx-option.position-changed",digital-options.position-changed
        msg={"name": name,
            "version": "1.0",
            "params": {
                        "routingFilters": {"instrument_type": str(instrument_type)}

                        }
            }
        self.send_websocket_request(name="subscribeMessage",msg=msg,request_id=str(request_id))

    def setOptions(self, request_id, sendResults):
        # sendResults True/False
       
        msg={"sendResults": sendResults}

         
        self.send_websocket_request(name="setOptions",msg=msg,request_id=str(request_id))
    
    @property
    def Subscribe_Top_Assets_Updated(self):
        return Subscribe_top_assets_updated(self)

    @property
    def Unsubscribe_Top_Assets_Updated(self):
        return Unsubscribe_top_assets_updated(self)

    @property
    def Subscribe_Commission_Changed(self):
        return Subscribe_commission_changed(self)
    @property
    def Unsubscribe_Commission_Changed(self):
        return Unsubscribe_commission_changed(self)
        
# --------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------

    @property
    def setactives(self):
        """Property for get IQ Option websocket setactives chanel.

        :returns: The instance of :class:`SetActives
            <iqoptionapi.ws.chanels.setactives.SetActives>`.
        """
        return SetActives(self)
    
    @property
    def Get_Leader_Board(self):
        return Leader_Board(self)
    
    @property
    def getcandles(self):
        """Property for get IQ Option websocket candles chanel.

        :returns: The instance of :class:`GetCandles
            <iqoptionapi.ws.chanels.candles.GetCandles>`.
        """
        return GetCandles(self)

    def get_api_option_init_all(self):
        self.send_websocket_request(name="api_option_init_all",msg="")

    def get_api_option_init_all_v2(self):
     
        msg={"name": "get-initialization-data",
                                    "version": "3.0",
                                    "body": {}
                                    }
        self.send_websocket_request(name="sendMessage",msg=msg)
# -------------get information-------------

    @property
    def get_betinfo(self):
        return Game_betinfo(self)

    @property
    def get_options(self):
        return Get_options(self)
    @property
    def get_options_v2(self):
        return Get_options_v2(self)

# ____________for_______binary_______option_____________

    @property
    def buyv3(self):
        return Buyv3(self)
    @property
    def buyv3_by_raw_expired(self):
        return Buyv3_by_raw_expired(self)

    @property
    def buy(self):
        """Property for get IQ Option websocket buyv2 request.

        :returns: The instance of :class:`Buyv2
            <iqoptionapi.ws.chanels.buyv2.Buyv2>`.
        """
        self.buy_successful = None
        return Buyv2(self)

    @property
    def sell_option(self):
        return Sell_Option(self)
# ____________________for_______digital____________________

    def get_digital_underlying(self):
        msg={"name": "get-underlying-list",
                                    "version": "2.0",
                                    "body": {"type": "digital-option"}
                                    }
        self.send_websocket_request(name="sendMessage",msg=msg)
    @property
    def get_strike_list(self):
        return Strike_list(self)

    @property
    def subscribe_instrument_quites_generated(self):
        return Subscribe_Instrument_Quites_Generated(self)

    @property
    def unsubscribe_instrument_quites_generated(self):
        return Unsubscribe_Instrument_Quites_Generated(self)

    @property
    def place_digital_option(self):
        return Digital_options_place_digital_option(self)

    @property
    def close_digital_option(self):
        return Digital_options_close_position(self)

# ____BUY_for__Forex__&&__stock(cfd)__&&__ctrpto_____
    @property
    def buy_order(self):
        return Buy_place_order_temp(self)

    @property
    def change_order(self):
        return Change_Tpsl(self)

    @property
    def change_auto_margin_call(self):
        return ChangeAutoMarginCall(self)

    @property
    def get_order(self):
        return Get_order(self)

    @property
    def get_pending(self):
        return GetDeferredOrders(self)

    @property
    def get_positions(self):
        return Get_positions(self)

    @property
    def get_position(self):
        return Get_position(self)
    @property
    def get_digital_position(self):
        return Get_digital_position(self)
    @property
    def get_position_history(self):
        return Get_position_history(self)

    @property
    def get_position_history_v2(self):
        return Get_position_history_v2(self)

    @property
    def get_available_leverages(self):
        return Get_available_leverages(self)

    @property
    def cancel_order(self):
        return Cancel_order(self)

    @property
    def close_position(self):
        return Close_position(self)

    @property
    def get_overnight_fee(self):
        return Get_overnight_fee(self)
# -------------------------------------------------------

    @property
    def heartbeat(self):
        return Heartbeat(self)
# -------------------------------------------------------

    def set_session(self,cookies,headers):

        """Method to set session cookies."""

        self.session.headers.update(headers)
         
        self.session.cookies.clear_session_cookies()
        requests.utils.add_dict_to_cookiejar(self.session.cookies, cookies)
        
    def start_websocket(self):
        global_value.check_websocket_if_connect = None
        global_value.check_websocket_if_error=False
        global_value.websocket_error_reason=None
         
        self.websocket_client = WebsocketClient(self)

        self.websocket_thread = threading.Thread(target=self.websocket.run_forever, kwargs={'sslopt': {
                                                 "check_hostname": False, "cert_reqs": ssl.CERT_NONE, "ca_certs": "cacert.pem"}})  # for fix pyinstall error: cafile, capath and cadata cannot be all omitted
        self.websocket_thread.daemon = True
        self.websocket_thread.start()
        start = time.time()
        while True:
            try:
                if global_value.check_websocket_if_error:
                    return False,global_value.websocket_error_reason
                if global_value.check_websocket_if_connect == 0 :
                    return False,"Websocket connection closed."
                elif global_value.check_websocket_if_connect == 1:
                    return True,None
            except:
                pass

            if time.time() - start > 30:
                return False,"Websocket connection timeout."
            time.sleep(0.05)
    def get_ssid(self):
        response=None
        try:
            response = self.login(self.username, self.password)  # pylint: disable=not-callable
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(e)
            return e
        return response
    def send_ssid(self):
        self.profile.msg=None
        self.ssid(global_value.SSID)  # pylint: disable=not-callable
        start = time.time()
        while self.profile.msg==None:
            if time.time() - start > 30:
                return False
            time.sleep(0.05)
        if self.profile.msg==False:
            return False
        else:
            return True
    def connect(self):
        
        global_value.ssl_Mutual_exclusion=False
        global_value.ssl_Mutual_exclusion_write=False
        """Method for connection to IQ Option API."""
        try:
            self.close()
        except:
            pass
        check_websocket,websocket_reason=self.start_websocket()
         
        if check_websocket==False:
            return check_websocket,websocket_reason

        #doing temp ssid reconnect for speed up
        if global_value.SSID!=None:
            
            check_ssid=self.send_ssid()
           
            if check_ssid==False:
                #ssdi time out need reget,if sent error ssid,the weksocket will close by iqoption server
                response=self.get_ssid()
                try:
                    global_value.SSID = response.cookies["ssid"]     
                except:
                    return False,response.text
                atexit.register(self.logout)
                self.start_websocket()
                self.send_ssid()
         
        #the ssid is None need get ssid
        else:
            response=self.get_ssid()
            try:
               global_value.SSID = response.cookies["ssid"]
            except:
                self.close()
                return False,response.text
            atexit.register(self.logout)
            self.send_ssid()
        
        #set ssis cookie
        requests.utils.add_dict_to_cookiejar(self.session.cookies, {"ssid":global_value.SSID})
        

        self.timesync.server_timestamp = None
        start = time.time()
        while True:
            try:
                if self.timesync.server_timestamp != None:
                    break
            except:
                pass
            if time.time() - start > 30:
                return False,"timeSync timeout"
            time.sleep(0.05)
        return True,None

    def close(self):
        websocket = getattr(getattr(self, "websocket_client", None), "wss", None)
        if websocket is not None:
            websocket.close()
        websocket_thread = getattr(self, "websocket_thread", None)
        if websocket_thread is not None and websocket_thread.is_alive():
            websocket_thread.join(timeout=5)

    def websocket_alive(self):
        websocket_thread = getattr(self, "websocket_thread", None)
        return websocket_thread is not None and websocket_thread.is_alive()

    @property
    def Get_User_Profile_Client(self):
        return Get_user_profile_client(self)
    @property
    def Request_Leaderboard_Userinfo_Deals_Client(self):
        return Request_leaderboard_userinfo_deals_client(self)
    @property
    def Get_Users_Availability(self):
        return Get_users_availability(self)
