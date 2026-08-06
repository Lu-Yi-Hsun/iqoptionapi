# python
from iqoptionapi.api import IQOptionAPI
import iqoptionapi.constants as OP_code
import iqoptionapi.country_id as Country
import threading
import time
import logging
import math
import operator
import itertools
import iqoptionapi.global_value as global_value
from collections import defaultdict
from collections import deque
from iqoptionapi.expiration import get_expiration_time, get_remaning_time
from datetime import datetime, timedelta


_REQUEST_COUNTER = itertools.count(1)


def nested_dict(n, type):
    if n == 1:
        return defaultdict(type)
    else:
        return defaultdict(lambda: nested_dict(n - 1, type))


def _safe_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_closed_option_amount(msg):
    for key in ("amount", "deposit", "buy_amount"):
        amount = _safe_float(msg.get(key), default=0.0)
        if amount > 0:
            return amount
    return _safe_float(msg.get("sum"), default=0.0)


def _extract_closed_option_profit(payload):
    if not isinstance(payload, dict):
        return None

    msg = payload.get("msg", payload)
    if not isinstance(msg, dict):
        return None

    if "profit_amount" in msg:
        amount = _extract_closed_option_amount(msg)
        if amount > 0:
            return _safe_float(msg.get("profit_amount")) - amount

    win = str(msg.get("win", "") or "").strip().lower()
    if not win:
        return None

    amount = _extract_closed_option_amount(msg)
    if win in ("equal", "draw"):
        return 0.0
    if win in ("loose", "loss", "lose", "lost"):
        return 0.0 - amount
    if "win_amount" in msg:
        return _safe_float(msg.get("win_amount")) - amount
    if "profit_amount" in msg:
        return _safe_float(msg.get("profit_amount")) - amount
    return None


def _new_request_id(prefix):
    return "%s-%s-%s-%s" % (
        prefix,
        threading.get_ident(),
        int(time.time() * 1000000),
        next(_REQUEST_COUNTER),
    )


def _normalize_candle(candle):
    if not isinstance(candle, dict):
        return candle
    normalized = dict(candle)
    if "high" not in normalized and "max" in normalized:
        normalized["high"] = normalized["max"]
    if "low" not in normalized and "min" in normalized:
        normalized["low"] = normalized["min"]
    if "max" not in normalized and "high" in normalized:
        normalized["max"] = normalized["high"]
    if "min" not in normalized and "low" in normalized:
        normalized["min"] = normalized["low"]
    if "volume" not in normalized:
        normalized["volume"] = 0
    return normalized


def _normalize_candles(candles):
    if not candles:
        return []
    try:
        normalized = [_normalize_candle(candle) for candle in candles]
        return sorted(normalized, key=lambda candle: int(candle.get("from", 0)))
    except Exception:
        return candles


class IQ_Option:
    __version__ = "6.8.9.1"

    def __init__(self, email, password):
        self.size = [1, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800,
                     3600, 7200, 14400, 28800, 43200, 86400, 604800, 2592000]
        self.email = email
        self.password = password
        self.suspend = 0.5
        self.thread = None
        self.subscribe_candle = []
        self.subscribe_candle_all_size = []
        self.subscribe_mood = []
        # for digit
        self.get_digital_spot_profit_after_sale_data = nested_dict(2, int)
        self.get_realtime_strike_list_temp_data = {}
        self.get_realtime_strike_list_temp_expiration = 0
        self.SESSION_HEADER = {
            "User-Agent": r"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36"}
        self.SESSION_COOKIE = {}
        self.last_operation = {
            "name": None,
            "status": None,
            "reason": None,
            "payload": None,
            "timestamp": None,
        }
        #

        # --start
        # self.connect()
        # this auto function delay too long

    # --------------------------------------------------------------------------

    def get_server_timestamp(self):
        return self.api.timesync.server_timestamp

    def _set_last_operation(self, name, status, reason=None, payload=None):
        self.last_operation = {
            "name": name,
            "status": status,
            "reason": reason,
            "payload": payload,
            "timestamp": time.time(),
        }

    def _wait_for_api_attr(self, attr_name, timeout=10):
        start = time.time()
        while getattr(self.api, attr_name) == None:
            if timeout is not None and time.time() - start >= float(timeout):
                return False
            time.sleep(min(self.suspend, 0.05))
        return True

    def get_api_diagnostics(self):
        api = getattr(self, "api", None)
        return {
            "last_operation": dict(self.last_operation),
            "websocket_last_message_error": getattr(api, "websocket_last_message_error", None),
            "closed_option_last_error": getattr(api, "closed_option_last_error", None),
            "http_last_request": getattr(api, "http_last_request", None),
            "http_last_error": getattr(api, "http_last_error", None),
        }

    def re_subscribe_stream(self):
        try:
            for ac in self.subscribe_candle:
                sp = ac.split(",")
                self.start_candles_one_stream(sp[0], sp[1])
        except:
            pass
        # -----------------
        try:
            for ac in self.subscribe_candle_all_size:
                self.start_candles_all_size_stream(ac)
        except:
            pass
        # -------------reconnect subscribe_mood
        try:
            for ac in self.subscribe_mood:
                self.start_mood_stream(ac)
        except:
            pass

    def set_session(self, header, cookie):
        self.SESSION_HEADER = header
        self.SESSION_COOKIE = cookie

    def connect(self, timeout=30):
        try:
            timeout = float(timeout)
        except (TypeError, ValueError):
            self._set_last_operation(
                "connect",
                "rejected",
                "invalid_timeout",
                {"timeout": timeout},
            )
            return False, "invalid_timeout"
        if timeout <= 0 or not math.isfinite(timeout):
            self._set_last_operation(
                "connect",
                "rejected",
                "invalid_timeout",
                {"timeout": timeout},
            )
            return False, "invalid_timeout"

        try:
            self.api.close()
        except:
            pass
            # logging.error('**warning** self.api.close() fail')

        try:
            self.api = IQOptionAPI(
                "iqoption.com", self.email, self.password, request_timeout=timeout)
        except TypeError as exc:
            if "request_timeout" not in str(exc):
                raise
            self.api = IQOptionAPI(
                "iqoption.com", self.email, self.password)
        check = None
        self.api.set_session(headers=self.SESSION_HEADER, cookies=self.SESSION_COOKIE)
        try:
            check, reason = self.api.connect()
        except Exception as exc:
            self._set_last_operation(
                "connect",
                "failed",
                type(exc).__name__,
                {"message": str(exc)},
            )
            raise

        if check == True:
            # -------------reconnect subscribe_candle
            self.re_subscribe_stream()

            # ---------for async get name: "position-changed", microserviceName
            balance_start = time.time()
            while global_value.balance_id == None:
                if timeout is not None and time.time() - balance_start > float(timeout):
                    self._set_last_operation(
                        "connect",
                        "timeout",
                        "balance_id_timeout",
                        {"timeout": timeout},
                    )
                    return False, "balance_id timeout"
                time.sleep(self.suspend)
            self.position_change_all("subscribeMessage", global_value.balance_id)
            self.order_changed_all("subscribeMessage")
            self.api.setOptions(1, True)

            """
            self.api.subscribe_position_changed(
                "position-changed", "multi-option", 2)

            self.api.subscribe_position_changed(
                "trading-fx-option.position-changed", "fx-option", 3)

            self.api.subscribe_position_changed(
                "position-changed", "crypto", 4)

            self.api.subscribe_position_changed(
                "position-changed", "forex", 5)

            self.api.subscribe_position_changed(
                "digital-options.position-changed", "digital-option", 6)

            self.api.subscribe_position_changed(
                "position-changed", "cfd", 7)
            """

            # self.get_balance_id()
            self._set_last_operation(
                "connect",
                "ok",
                None,
                {"balance_id": global_value.balance_id},
            )
            return True, None
        else:
            self._set_last_operation(
                "connect",
                "rejected",
                reason,
                {"reason": reason},
            )
            return False, reason

    # self.update_ACTIVES_OPCODE()

    def check_connect(self):
        # True/False

        if global_value.check_websocket_if_connect == 0:
            return False
        else:
            return True
        # wait for timestamp getting

    # _________________________UPDATE ACTIVES OPCODE_____________________
    def get_all_ACTIVES_OPCODE(self):
        return OP_code.ACTIVES

    def update_ACTIVES_OPCODE(self, timeout=30):
        # update from binary option
        if not self.get_ALL_Binary_ACTIVES_OPCODE(timeout=timeout):
            self._set_last_operation(
                "update_ACTIVES_OPCODE",
                "rejected",
                "binary_init_failed",
                {"timeout": timeout},
            )
            return False
        # crypto /dorex/cfd
        if not self.instruments_input_all_in_ACTIVES(timeout=timeout):
            self._set_last_operation(
                "update_ACTIVES_OPCODE",
                "rejected",
                "instruments_failed",
                {"timeout": timeout},
            )
            return False
        dicc = {}
        for lis in sorted(OP_code.ACTIVES.items(), key=operator.itemgetter(1)):
            dicc[lis[0]] = lis[1]
        OP_code.ACTIVES = dicc
        self._set_last_operation(
            "update_ACTIVES_OPCODE",
            "ok",
            None,
            {"count": len(OP_code.ACTIVES)},
        )
        return True

    def get_name_by_activeId(self, activeId):
        info = self.get_financial_information(activeId)
        try:
            return info["msg"]["data"]["active"]["name"]
        except:
            return None

    def get_financial_information(self, activeId, timeout=10):
        self.api.financial_information = None
        self.api.get_financial_information(activeId)
        if not self._wait_for_api_attr("financial_information", timeout):
            self._set_last_operation(
                "get_financial_information",
                "timeout",
                "timeout",
                {"active_id": activeId, "timeout": timeout},
            )
            return None
        self._set_last_operation(
            "get_financial_information",
            "ok",
            None,
            {"active_id": activeId},
        )
        return self.api.financial_information

    def get_leader_board(self, country, from_position, to_position, near_traders_count, user_country_id=0,
                         near_traders_country_count=0, top_country_count=0, top_count=0, top_type=2, timeout=10):
        self.api.leaderboard_deals_client = None

        country_id = Country.ID[country]
        self.api.Get_Leader_Board(country_id, user_country_id, from_position, to_position, near_traders_country_count,
                                  near_traders_count, top_country_count, top_count, top_type)
        if not self._wait_for_api_attr("leaderboard_deals_client", timeout):
            self._set_last_operation(
                "get_leader_board",
                "timeout",
                "timeout",
                {"country": country, "timeout": timeout},
            )
            return None
        self._set_last_operation(
            "get_leader_board",
            "ok",
            None,
            {"country": country},
        )
        return self.api.leaderboard_deals_client

    def get_instruments(self, type, timeout=10):
        # type="crypto"/"forex"/"cfd"
        time.sleep(self.suspend)
        self.api.instruments = None
        start_total = time.time()
        while self.api.instruments == None:
            if timeout is not None and time.time() - start_total >= float(timeout):
                self._set_last_operation(
                    "get_instruments",
                    "timeout",
                    "timeout",
                    {"type": type, "timeout": timeout},
                )
                return None
            try:
                self.api.get_instruments(type)
                start = time.time()
                while self.api.instruments == None and time.time() - start < 10:
                    if timeout is not None and time.time() - start_total >= float(timeout):
                        self._set_last_operation(
                            "get_instruments",
                            "timeout",
                            "timeout",
                            {"type": type, "timeout": timeout},
                        )
                        return None
                    time.sleep(min(self.suspend, 0.05))
            except:
                logging.error('**error** api.get_instruments need reconnect')
                self.connect()
        self._set_last_operation(
            "get_instruments",
            "ok",
            None,
            {"type": type},
        )
        return self.api.instruments

    def instruments_input_to_ACTIVES(self, type, timeout=10):
        instruments = self.get_instruments(type, timeout=timeout)
        if instruments is None:
            self._set_last_operation(
                "instruments_input_to_ACTIVES",
                "timeout",
                "instruments_timeout",
                {"type": type, "timeout": timeout},
            )
            return False
        try:
            for ins in instruments["instruments"]:
                OP_code.ACTIVES[ins["id"]] = ins["active_id"]
        except Exception:
            self._set_last_operation(
                "instruments_input_to_ACTIVES",
                "rejected",
                "invalid_response",
                {"type": type},
            )
            return False
        self._set_last_operation(
            "instruments_input_to_ACTIVES",
            "ok",
            None,
            {"type": type, "count": len(instruments["instruments"])},
        )
        return True

    def instruments_input_all_in_ACTIVES(self, timeout=10):
        for instrument_type in ("crypto", "forex", "cfd"):
            if not self.instruments_input_to_ACTIVES(instrument_type, timeout=timeout):
                self._set_last_operation(
                    "instruments_input_all_in_ACTIVES",
                    "rejected",
                    "dependency_failed",
                    {"type": instrument_type, "timeout": timeout},
                )
                return False
        self._set_last_operation(
            "instruments_input_all_in_ACTIVES",
            "ok",
            None,
            None,
        )
        return True

    def get_ALL_Binary_ACTIVES_OPCODE(self, timeout=30):
        init_info = self.get_all_init(timeout=timeout)
        if init_info is None:
            self._set_last_operation(
                "get_ALL_Binary_ACTIVES_OPCODE",
                "timeout",
                "init_timeout",
                {"timeout": timeout},
            )
            return False
        try:
            for dirr in (["binary", "turbo"]):
                for i in init_info["result"][dirr]["actives"]:
                    OP_code.ACTIVES[(init_info["result"][dirr]
                    ["actives"][i]["name"]).split(".")[1]] = int(i)
        except Exception:
            self._set_last_operation(
                "get_ALL_Binary_ACTIVES_OPCODE",
                "rejected",
                "invalid_response",
                None,
            )
            return False
        self._set_last_operation(
            "get_ALL_Binary_ACTIVES_OPCODE",
            "ok",
            None,
            None,
        )
        return True

    # _________________________self.api.get_api_option_init_all() wss______________________
    def get_all_init(self, timeout=30):

        start_total = time.time()
        while True:
            if timeout is not None and time.time() - start_total >= float(timeout):
                self._set_last_operation(
                    "get_all_init",
                    "timeout",
                    "timeout",
                    {"timeout": timeout},
                )
                return None
            self.api.api_option_init_all_result = None
            while True:
                try:
                    self.api.get_api_option_init_all()
                    break
                except:
                    if timeout is not None and time.time() - start_total >= float(timeout):
                        self._set_last_operation(
                            "get_all_init",
                            "timeout",
                            "timeout",
                            {"timeout": timeout},
                        )
                        return None
                    logging.error('**error** get_all_init need reconnect')
                    self.connect()
                    time.sleep(min(5, float(timeout)) if timeout else 5)
            start = time.time()
            while True:
                if timeout is not None and time.time() - start_total >= float(timeout):
                    self._set_last_operation(
                        "get_all_init",
                        "timeout",
                        "timeout",
                        {"timeout": timeout},
                    )
                    return None
                if time.time() - start > 30:
                    logging.error('**warning** get_all_init late 30 sec')
                    break
                try:
                    if self.api.api_option_init_all_result != None:
                        break
                except:
                    pass
                time.sleep(min(self.suspend, 0.05))
            try:
                if self.api.api_option_init_all_result["isSuccessful"] == True:
                    self._set_last_operation(
                        "get_all_init",
                        "ok",
                        None,
                        None,
                    )
                    return self.api.api_option_init_all_result
            except:
                pass

    def get_all_init_v2(self, timeout=30):
        self.api.api_option_init_all_result_v2 = None

        self.api.get_api_option_init_all_v2()
        start_t = time.time()
        while self.api.api_option_init_all_result_v2 == None:
            if timeout is not None and time.time() - start_t >= float(timeout):
                logging.error('**warning** get_all_init_v2 late 30 sec')
                self._set_last_operation(
                    "get_all_init_v2",
                    "timeout",
                    "timeout",
                    {"timeout": timeout},
                )
                return None
            time.sleep(min(self.suspend, 0.05))
        self._set_last_operation(
            "get_all_init_v2",
            "ok",
            None,
            None,
        )
        return self.api.api_option_init_all_result_v2

        # return OP_code.ACTIVES

    # ------- chek if binary/digit/cfd/stock... if open or not

    def get_all_open_time(self, timeout=30):
        # for binary option turbo and binary
        OPEN_TIME = nested_dict(3, dict)
        binary_data = self.get_all_init_v2(timeout=timeout)
        if binary_data is None:
            self._set_last_operation(
                "get_all_open_time",
                "timeout",
                "binary_init_timeout",
                {"timeout": timeout},
            )
            return None
        binary_list = ["binary", "turbo"]
        for option in binary_list:
            for actives_id in binary_data[option]["actives"]:
                active = binary_data[option]["actives"][actives_id]
                name = str(active["name"]).split(".")[1]
                if active["enabled"] == True:
                    if active["is_suspended"] == True:
                        OPEN_TIME[option][name]["open"] = False
                    else:
                        OPEN_TIME[option][name]["open"] = True
                else:
                    OPEN_TIME[option][name]["open"] = active["enabled"]

        # for digital
        digital_underlying = self.get_digital_underlying_list_data(timeout=timeout)
        if digital_underlying is None:
            self._set_last_operation(
                "get_all_open_time",
                "timeout",
                "digital_underlying_timeout",
                {"timeout": timeout},
            )
            return None
        digital_data = []
        digital_status = "ok"
        if isinstance(digital_underlying, dict):
            raw_digital_data = digital_underlying.get("underlying")
            if isinstance(raw_digital_data, list):
                digital_data = raw_digital_data
            else:
                digital_status = "missing_underlying"
        else:
            digital_status = "invalid_response"
        for digital in digital_data:
            if not isinstance(digital, dict):
                continue
            name = digital["underlying"]
            schedule = digital.get("schedule") or []
            OPEN_TIME["digital"][name]["open"] = False
            for schedule_time in schedule:
                if not isinstance(schedule_time, dict):
                    continue
                start = schedule_time["open"]
                end = schedule_time["close"]
                if start < time.time() < end:
                    OPEN_TIME["digital"][name]["open"] = True

        # for OTHER
        instrument_list = ["cfd", "forex", "crypto"]
        for instruments_type in instrument_list:
            instruments = self.get_instruments(instruments_type, timeout=timeout)
            if instruments is None:
                self._set_last_operation(
                    "get_all_open_time",
                    "timeout",
                    "instruments_timeout",
                    {"instrument_type": instruments_type, "timeout": timeout},
                )
                return None
            ins_data = instruments["instruments"]
            for detail in ins_data:
                name = detail["name"]
                schedule = detail["schedule"]
                OPEN_TIME[instruments_type][name]["open"] = False
                for schedule_time in schedule:
                    start = schedule_time["open"]
                    end = schedule_time["close"]
                    if start < time.time() < end:
                        OPEN_TIME[instruments_type][name]["open"] = True

        self._set_last_operation(
            "get_all_open_time",
            "ok",
            None,
            {"digital_status": digital_status},
        )
        return OPEN_TIME

    # --------for binary option detail

    def get_binary_option_detail(self, timeout=30):
        detail = nested_dict(2, dict)
        init_info = self.get_all_init(timeout=timeout)
        if init_info is None:
            self._set_last_operation(
                "get_binary_option_detail",
                "timeout",
                "init_timeout",
                {"timeout": timeout},
            )
            return None
        for actives in init_info["result"]["turbo"]["actives"]:
            name = init_info["result"]["turbo"]["actives"][actives]["name"]
            name = name[name.index(".") + 1:len(name)]
            detail[name]["turbo"] = init_info["result"]["turbo"]["actives"][actives]

        for actives in init_info["result"]["binary"]["actives"]:
            name = init_info["result"]["binary"]["actives"][actives]["name"]
            name = name[name.index(".") + 1:len(name)]
            detail[name]["binary"] = init_info["result"]["binary"]["actives"][actives]
        self._set_last_operation(
            "get_binary_option_detail",
            "ok",
            None,
            None,
        )
        return detail

    def get_all_profit(self, timeout=30):
        all_profit = nested_dict(2, dict)
        init_info = self.get_all_init(timeout=timeout)
        if init_info is None:
            self._set_last_operation(
                "get_all_profit",
                "timeout",
                "init_timeout",
                {"timeout": timeout},
            )
            return None
        for actives in init_info["result"]["turbo"]["actives"]:
            name = init_info["result"]["turbo"]["actives"][actives]["name"]
            name = name[name.index(".") + 1:len(name)]
            all_profit[name]["turbo"] = (
                                                100.0 -
                                                init_info["result"]["turbo"]["actives"][actives]["option"]["profit"][
                                                    "commission"]) / 100.0

        for actives in init_info["result"]["binary"]["actives"]:
            name = init_info["result"]["binary"]["actives"][actives]["name"]
            name = name[name.index(".") + 1:len(name)]
            all_profit[name]["binary"] = (
                                                 100.0 -
                                                 init_info["result"]["binary"]["actives"][actives]["option"]["profit"][
                                                     "commission"]) / 100.0
        self._set_last_operation(
            "get_all_profit",
            "ok",
            None,
            None,
        )
        return all_profit

    # ----------------------------------------

    # ______________________________________self.api.getprofile() https________________________________

    def get_profile_ansyc(self, timeout=10):
        start = time.time()
        while self.api.profile.msg == None:
            if timeout is not None and time.time() - start >= float(timeout):
                self._set_last_operation(
                    "get_profile_ansyc",
                    "timeout",
                    "timeout",
                    {"timeout": timeout},
                )
                return None
            time.sleep(min(self.suspend, 0.05))
        self._set_last_operation(
            "get_profile_ansyc",
            "ok",
            None,
            None,
        )
        return self.api.profile.msg

    """def get_profile(self):
        while True:
            try:

                respon = self.api.getprofile().json()
                time.sleep(self.suspend)

                if respon["isSuccessful"] == True:
                    return respon
            except:
                logging.error('**error** get_profile try reconnect')
                self.connect()"""

    def get_currency(self, timeout=10):
        balances_raw = self.get_balances(timeout=timeout)
        if not balances_raw:
            self._set_last_operation(
                "get_currency",
                "timeout",
                "balances_timeout",
                {"timeout": timeout},
            )
            return None
        for balance in balances_raw["msg"]:
            if balance["id"] == global_value.balance_id:
                self._set_last_operation(
                    "get_currency",
                    "ok",
                    None,
                    {"balance_id": global_value.balance_id},
                )
                return balance["currency"]
        self._set_last_operation(
            "get_currency",
            "rejected",
            "missing_balance",
            {"balance_id": global_value.balance_id},
        )
        return None

    def get_balance_id(self):
        return global_value.balance_id

    """ def get_balance(self):
        self.api.profile.balance = None
        while True:
            try:
                respon = self.get_profile()
                self.api.profile.balance = respon["result"]["balance"]
                break
            except:
                logging.error('**error** get_balance()')

            time.sleep(self.suspend)
        return self.api.profile.balance"""

    def get_balance(self, timeout=10):

        balances_raw = self.get_balances(timeout=timeout)
        if not balances_raw:
            self._set_last_operation(
                "get_balance",
                "timeout",
                "balances_timeout",
                {"timeout": timeout},
            )
            return None
        for balance in balances_raw["msg"]:
            if balance["id"] == global_value.balance_id:
                self._set_last_operation(
                    "get_balance",
                    "ok",
                    None,
                    {"balance_id": global_value.balance_id},
                )
                return balance["amount"]
        self._set_last_operation(
            "get_balance",
            "rejected",
            "missing_balance",
            {"balance_id": global_value.balance_id},
        )
        return None

    def get_balances(self, timeout=10):
        self.api.balances_raw = None
        self.api.get_balances()
        if not self._wait_for_api_attr("balances_raw", timeout):
            self._set_last_operation(
                "get_balances",
                "timeout",
                "timeout",
                {"timeout": timeout},
            )
            return None
        self._set_last_operation(
            "get_balances",
            "ok",
            None,
            None,
        )
        return self.api.balances_raw

    def get_balance_mode(self, timeout=10):
        # self.api.profile.balance_type=None
        profile = self.get_profile_ansyc(timeout=timeout)
        if not profile:
            self._set_last_operation(
                "get_balance_mode",
                "timeout",
                "profile_timeout",
                {"timeout": timeout},
            )
            return None
        for balance in profile["balances"]:
            if balance["id"] == global_value.balance_id:
                if balance["type"] == 1:
                    self._set_last_operation(
                        "get_balance_mode",
                        "ok",
                        None,
                        {"balance_id": global_value.balance_id},
                    )
                    return "REAL"
                elif balance["type"] == 4:
                    self._set_last_operation(
                        "get_balance_mode",
                        "ok",
                        None,
                        {"balance_id": global_value.balance_id},
                    )
                    return "PRACTICE"
        self._set_last_operation(
            "get_balance_mode",
            "rejected",
            "missing_balance",
            {"balance_id": global_value.balance_id},
        )
        return None

    def reset_practice_balance(self, timeout=10):
        self.api.training_balance_reset_request = None
        self.api.reset_training_balance()
        if not self._wait_for_api_attr("training_balance_reset_request", timeout):
            self._set_last_operation(
                "reset_practice_balance",
                "timeout",
                "timeout",
                {"timeout": timeout},
            )
            return None
        self._set_last_operation(
            "reset_practice_balance",
            "ok",
            None,
            None,
        )
        return self.api.training_balance_reset_request

    def position_change_all(self, Main_Name, user_balance_id):
        instrument_type = ["cfd", "forex", "crypto", "digital-option", "turbo-option", "binary-option"]
        for ins in instrument_type:
            self.api.portfolio(Main_Name=Main_Name, name="portfolio.position-changed", instrument_type=ins,
                               user_balance_id=user_balance_id)

    def order_changed_all(self, Main_Name):
        instrument_type = ["cfd", "forex", "crypto", "digital-option", "turbo-option", "binary-option"]
        for ins in instrument_type:
            self.api.portfolio(Main_Name=Main_Name, name="portfolio.order-changed", instrument_type=ins)

    def change_balance(self, Balance_MODE, timeout=10):
        def set_id(b_id):
            if global_value.balance_id != None:
                self.position_change_all("unsubscribeMessage", global_value.balance_id)

            global_value.balance_id = b_id

            self.position_change_all("subscribeMessage", b_id)

        real_id = None
        practice_id = None

        profile = self.get_profile_ansyc(timeout=timeout)
        if not profile:
            self._set_last_operation(
                "change_balance",
                "timeout",
                "profile_timeout",
                {"mode": Balance_MODE, "timeout": timeout},
            )
            return False

        for balance in profile["balances"]:
            if balance["type"] == 1:
                real_id = balance["id"]
            if balance["type"] == 4:
                practice_id = balance["id"]

        if Balance_MODE == "REAL":
            set_id(real_id)

        elif Balance_MODE == "PRACTICE":

            set_id(practice_id)

        else:
            logging.error("ERROR doesn't have this mode")
            self._set_last_operation(
                "change_balance",
                "rejected",
                "invalid_mode",
                {"mode": Balance_MODE},
            )
            return False
        self._set_last_operation(
            "change_balance",
            "ok",
            None,
            {"mode": Balance_MODE, "balance_id": global_value.balance_id},
        )
        return True

    # ________________________________________________________________________
    # _______________________        CANDLE      _____________________________
    # ________________________self.api.getcandles() wss________________________

    def get_candles(self, ACTIVES, interval, count, endtime, timeout=10):
        if ACTIVES not in OP_code.ACTIVES:
            logging.error('**error** get_candles invalid active')
            self._set_last_operation("get_candles", "rejected", "invalid_active", {"active": ACTIVES})
            return []
        try:
            if int(interval) <= 0 or int(count) <= 0:
                logging.error('**error** get_candles invalid interval/count')
                self._set_last_operation(
                    "get_candles",
                    "rejected",
                    "invalid_interval_or_count",
                    {"active": ACTIVES, "interval": interval, "count": count},
                )
                return []
        except (TypeError, ValueError):
            logging.error('**error** get_candles invalid interval/count')
            self._set_last_operation(
                "get_candles",
                "rejected",
                "invalid_interval_or_count",
                {"active": ACTIVES, "interval": interval, "count": count},
            )
            return []
        self.api.candles.candles_data = None
        req_id = _new_request_id("candles")
        start = time.time()
        while True:
            try:
                try:
                    self.api.getcandles(
                        OP_code.ACTIVES[ACTIVES], interval, count, endtime, request_id=req_id)
                except TypeError:
                    self.api.getcandles(
                        OP_code.ACTIVES[ACTIVES], interval, count, endtime)
                while self.check_connect() and self.api.candles.candles_data == None:
                    if timeout and time.time() - start >= float(timeout):
                        logging.error('**error** get_candles timeout')
                        self._set_last_operation(
                            "get_candles",
                            "timeout",
                            "timeout",
                            {"active": ACTIVES, "request_id": req_id},
                        )
                        return []
                    time.sleep(self.suspend)
                if self.api.candles.candles_data != None:
                    break
            except:
                if timeout and time.time() - start >= float(timeout):
                    logging.error('**error** get_candles timeout')
                    self._set_last_operation(
                        "get_candles",
                        "timeout",
                        "timeout",
                        {"active": ACTIVES, "request_id": req_id},
                    )
                    return []
                logging.error('**error** get_candles need reconnect')
                self.connect()

        candles = _normalize_candles(self.api.candles.candles_data)
        self._set_last_operation(
            "get_candles",
            "ok",
            None,
            {"active": ACTIVES, "interval": interval, "count": len(candles), "request_id": req_id},
        )
        return candles

    #######################################################
    # ______________________________________________________
    # _____________________REAL TIME CANDLE_________________
    # ______________________________________________________
    #######################################################

    def start_candles_stream(self, ACTIVE, size, maxdict):

        if size == "all":
            for s in self.size:
                self.full_realtime_get_candle(ACTIVE, s, maxdict)
                self.api.real_time_candles_maxdict_table[ACTIVE][s] = maxdict
            self.start_candles_all_size_stream(ACTIVE)
        elif size in self.size:
            self.api.real_time_candles_maxdict_table[ACTIVE][size] = maxdict
            self.full_realtime_get_candle(ACTIVE, size, maxdict)
            self.start_candles_one_stream(ACTIVE, size)

        else:
            logging.error(
                '**error** start_candles_stream please input right size')

    def stop_candles_stream(self, ACTIVE, size):
        if size == "all":
            return self.stop_candles_all_size_stream(ACTIVE)
        elif size in self.size:
            return self.stop_candles_one_stream(ACTIVE, size)
        else:
            logging.error(
                '**error** start_candles_stream please input right size')
            self._set_last_operation(
                "stop_candles_stream",
                "rejected",
                "invalid_size",
                {"active": ACTIVE, "size": size},
            )
            return False

    def get_realtime_candles(self, ACTIVE, size):
        if size == "all":
            try:
                return self.api.real_time_candles[ACTIVE]
            except:
                logging.error(
                    '**error** get_realtime_candles() size="all" can not get candle')
                return False
        elif size in self.size:
            try:
                return self.api.real_time_candles[ACTIVE][size]
            except:
                logging.error(
                    '**error** get_realtime_candles() size=' + str(size) + ' can not get candle')
                return False
        else:
            logging.error(
                '**error** get_realtime_candles() please input right "size"')

    def get_all_realtime_candles(self):
        return self.api.real_time_candles

    ################################################
    # ---------REAL TIME CANDLE Subset Function---------
    ################################################
    # ---------------------full dict get_candle-----------------------

    def full_realtime_get_candle(self, ACTIVE, size, maxdict):
        candles = self.get_candles(
            ACTIVE, size, maxdict, self.api.timesync.server_timestamp)
        for can in candles:
            self.api.real_time_candles[str(
                ACTIVE)][int(size)][can["from"]] = can

    # ------------------------Subscribe ONE SIZE-----------------------
    def start_candles_one_stream(self, ACTIVE, size):
        if (str(ACTIVE + "," + str(size)) in self.subscribe_candle) == False:
            self.subscribe_candle.append((ACTIVE + "," + str(size)))
        start = time.time()
        self.api.candle_generated_check[str(ACTIVE)][int(size)] = {}
        while True:
            if time.time() - start > 20:
                logging.error(
                    '**error** start_candles_one_stream late for 20 sec')
                return False
            try:
                if self.api.candle_generated_check[str(ACTIVE)][int(size)] == True:
                    return True
            except:
                pass
            try:

                self.api.subscribe(OP_code.ACTIVES[ACTIVE], size)
            except:
                logging.error('**error** start_candles_stream reconnect')
                self.connect()
            time.sleep(1)

    def stop_candles_one_stream(self, ACTIVE, size, timeout=10):
        active_id = OP_code.ACTIVES.get(ACTIVE)
        if active_id is None:
            self._set_last_operation(
                "stop_candles_one_stream",
                "rejected",
                "invalid_active",
                {"active": ACTIVE, "size": size},
            )
            return False
        if size not in self.size:
            self._set_last_operation(
                "stop_candles_one_stream",
                "rejected",
                "invalid_size",
                {"active": ACTIVE, "size": size},
            )
            return False
        if ((ACTIVE + "," + str(size)) in self.subscribe_candle) == True:
            self.subscribe_candle.remove(ACTIVE + "," + str(size))
        start = time.time()
        while True:
            if timeout is not None and time.time() - start > timeout:
                self._set_last_operation(
                    "stop_candles_one_stream",
                    "timeout",
                    "timeout",
                    {"active": ACTIVE, "size": size, "timeout": timeout},
                )
                return False
            try:
                if self.api.candle_generated_check[str(ACTIVE)][int(size)] == {}:
                    self._set_last_operation(
                        "stop_candles_one_stream",
                        "ok",
                        None,
                        {"active": ACTIVE, "size": size},
                    )
                    return True
            except:
                pass
            self.api.candle_generated_check[str(ACTIVE)][int(size)] = {}
            self.api.unsubscribe(active_id, size)
            time.sleep(self.suspend)

    # ------------------------Subscribe ALL SIZE-----------------------

    def start_candles_all_size_stream(self, ACTIVE):
        self.api.candle_generated_all_size_check[str(ACTIVE)] = {}
        if (str(ACTIVE) in self.subscribe_candle_all_size) == False:
            self.subscribe_candle_all_size.append(str(ACTIVE))
        start = time.time()
        while True:
            if time.time() - start > 20:
                logging.error('**error** fail ' + ACTIVE +
                              ' start_candles_all_size_stream late for 10 sec')
                return False
            try:
                if self.api.candle_generated_all_size_check[str(ACTIVE)] == True:
                    return True
            except:
                pass
            try:
                self.api.subscribe_all_size(OP_code.ACTIVES[ACTIVE])
            except:
                logging.error(
                    '**error** start_candles_all_size_stream reconnect')
                self.connect()
            time.sleep(1)

    def stop_candles_all_size_stream(self, ACTIVE, timeout=10):
        active_id = OP_code.ACTIVES.get(ACTIVE)
        if active_id is None:
            self._set_last_operation(
                "stop_candles_all_size_stream",
                "rejected",
                "invalid_active",
                {"active": ACTIVE},
            )
            return False
        if (str(ACTIVE) in self.subscribe_candle_all_size) == True:
            self.subscribe_candle_all_size.remove(str(ACTIVE))
        start = time.time()
        while True:
            if timeout is not None and time.time() - start > timeout:
                self._set_last_operation(
                    "stop_candles_all_size_stream",
                    "timeout",
                    "timeout",
                    {"active": ACTIVE, "timeout": timeout},
                )
                return False
            try:
                if self.api.candle_generated_all_size_check[str(ACTIVE)] == {}:
                    self._set_last_operation(
                        "stop_candles_all_size_stream",
                        "ok",
                        None,
                        {"active": ACTIVE},
                    )
                    return True
            except:
                pass
            self.api.candle_generated_all_size_check[str(ACTIVE)] = {}
            self.api.unsubscribe_all_size(active_id)
            time.sleep(self.suspend)

    # ------------------------top_assets_updated---------------------------------------------

    def subscribe_top_assets_updated(self, instrument_type):
        self.api.Subscribe_Top_Assets_Updated(instrument_type)

    def unsubscribe_top_assets_updated(self, instrument_type):
        self.api.Unsubscribe_Top_Assets_Updated(instrument_type)

    def get_top_assets_updated(self, instrument_type):
        if instrument_type in self.api.top_assets_updated_data:
            return self.api.top_assets_updated_data[instrument_type]
        else:
            return None

    # ------------------------commission_________
    # instrument_type: "binary-option"/"turbo-option"/"digital-option"/"crypto"/"forex"/"cfd"
    def subscribe_commission_changed(self, instrument_type):

        self.api.Subscribe_Commission_Changed(instrument_type)

    def unsubscribe_commission_changed(self, instrument_type):
        self.api.Unsubscribe_Commission_Changed(instrument_type)

    def get_commission_change(self, instrument_type):
        return self.api.subscribe_commission_changed_data[instrument_type]

    # -----------------------------------------------

    # -----------------traders_mood----------------------

    def start_mood_stream(self, ACTIVES, timeout=20):
        active_id = OP_code.ACTIVES.get(ACTIVES)
        if active_id is None:
            self._set_last_operation(
                "start_mood_stream",
                "rejected",
                "invalid_active",
                {"active": ACTIVES},
            )
            return False
        if ACTIVES not in self.subscribe_mood:
            self.subscribe_mood.append(ACTIVES)

        start = time.time()
        while True:
            if timeout is not None and time.time() - start > timeout:
                self._set_last_operation(
                    "start_mood_stream",
                    "timeout",
                    "timeout",
                    {"active": ACTIVES, "timeout": timeout},
                )
                return False
            self.api.subscribe_Traders_mood(active_id)
            try:
                self.api.traders_mood[active_id]
                self._set_last_operation(
                    "start_mood_stream",
                    "ok",
                    None,
                    {"active": ACTIVES},
                )
                return True
            except:
                time.sleep(self.suspend)

    def stop_mood_stream(self, ACTIVES):
        active_id = OP_code.ACTIVES.get(ACTIVES)
        if active_id is None:
            self._set_last_operation(
                "stop_mood_stream",
                "rejected",
                "invalid_active",
                {"active": ACTIVES},
            )
            return False
        if ACTIVES in self.subscribe_mood:
            self.subscribe_mood.remove(ACTIVES)
        self.api.unsubscribe_Traders_mood(active_id)
        self._set_last_operation(
            "stop_mood_stream",
            "ok",
            None,
            {"active": ACTIVES},
        )
        return True

    def get_traders_mood(self, ACTIVES):
        # return highter %
        return self.api.traders_mood[OP_code.ACTIVES[ACTIVES]]

    def get_all_traders_mood(self):
        # return highter %
        return self.api.traders_mood

    ##############################################################################################

    def check_win(self, id_number, timeout=10):
        # 'win':win money 'equal':no win no loose   'loose':loose money
        start = time.time()
        while True:
            try:
                listinfodata_dict = self.api.listinfodata.get(id_number)
                if listinfodata_dict["game_state"] == 1:
                    break
            except:
                pass
            if timeout is not None and time.time() - start >= float(timeout):
                self._set_last_operation(
                    "check_win",
                    "pending",
                    "timeout",
                    {"id": id_number, "timeout": timeout},
                )
                return None
            time.sleep(min(self.suspend, 0.05))
        self.api.listinfodata.delete(id_number)
        self._set_last_operation(
            "check_win",
            "resolved",
            None,
            {"id": id_number, "win": listinfodata_dict["win"]},
        )
        return listinfodata_dict["win"]

    def check_win_v2(self, id_number, polling_time, timeout=30):
        start = time.time()
        while True:
            if timeout is not None and time.time() - start >= float(timeout):
                self._set_last_operation(
                    "check_win_v2",
                    "pending",
                    "timeout",
                    {"id": id_number, "timeout": timeout},
                )
                return None
            check, data = self.get_betinfo(id_number, timeout=timeout)
            if not check or data is None:
                time.sleep(polling_time)
                continue
            win = data["result"]["data"][str(id_number)]["win"]
            if check and win != "":
                try:
                    profit = data["result"]["data"][str(id_number)]["profit"] - data["result"]["data"][str(id_number)][
                        "deposit"]
                    self._set_last_operation(
                        "check_win_v2",
                        "resolved",
                        None,
                        {"id": id_number, "profit": profit},
                    )
                    return profit
                except:
                    pass
            time.sleep(polling_time)

    def check_win_v3(self, id_number, timeout=10):
        start = time.time()
        while True:
            try:
                payload = self.get_async_order(id_number)["option-closed"]
                if payload != {}:
                    profit = _extract_closed_option_profit(payload)
                    if profit is not None:
                        self._set_last_operation(
                            "check_win_v3",
                            "resolved",
                            None,
                            {"id": id_number, "profit": profit},
                        )
                        return profit
            except:
                pass
            if timeout is not None and time.time() - start >= float(timeout):
                self._set_last_operation(
                    "check_win_v3",
                    "pending",
                    "timeout",
                    {"id": id_number, "timeout": timeout},
                )
                return None
            time.sleep(min(self.suspend, 0.05))

    def check_win_v4(self, id_number, timeout=1):
        """Compatível com versões modernas da API.

        - timeout <= 0: mantém polling continuo.
        - timeout > 0: aguarda ate `timeout` segundos e retorna (False, None) se nao houver resolucao.

        Retorno:
            tuple[bool, float|None]: (resolvido, lucro).
        """
        try:
            timeout = None if timeout is None else float(timeout)
        except (TypeError, ValueError):
            self._set_last_operation(
                "check_win_v4",
                "rejected",
                "invalid_timeout",
                {"id": id_number, "timeout": timeout},
            )
            return False, None

        end_time = None
        if timeout is not None and timeout > 0:
            end_time = time.monotonic() + timeout

        while True:
            payload = None
            closed = getattr(self.api, "socket_option_closed", None)
            if isinstance(closed, dict):
                payload = closed.get(id_number)
                if payload is None:
                    payload = closed.get(str(id_number))
                if payload is None:
                    try:
                        payload = closed.get(int(id_number))
                    except (TypeError, ValueError):
                        payload = None

            profit = _extract_closed_option_profit(payload)
            if profit is not None:
                self._set_last_operation(
                    "check_win_v4",
                    "resolved",
                    "socket_option_closed",
                    {"id": id_number, "profit": profit},
                )
                return True, profit

            try:
                payload = self.api.order_async[int(id_number)].get("option-closed")
            except Exception:
                payload = None

            profit = _extract_closed_option_profit(payload)
            if profit is not None:
                self._set_last_operation(
                    "check_win_v4",
                    "resolved",
                    "option_closed",
                    {"id": id_number, "profit": profit},
                )
                return True, profit

            if end_time is not None and time.monotonic() >= end_time:
                self._set_last_operation(
                    "check_win_v4",
                    "pending",
                    "timeout",
                    {"id": id_number},
                )
                return False, None

            sleep_time = self.suspend
            if end_time is not None:
                sleep_time = max(0.0, min(self.suspend, end_time - time.monotonic()))
            if sleep_time:
                time.sleep(sleep_time)

    # -------------------get infomation only for binary option------------------------

    def get_betinfo(self, id_number, timeout=10):
        # INPUT:int
        deadline = None
        if timeout and float(timeout) > 0:
            deadline = time.monotonic() + float(timeout)
        while True:
            self.api.game_betinfo.isSuccessful = None
            start = time.time()
            try:
                self.api.get_betinfo(id_number)
            except:
                logging.error(
                    '**error** def get_betinfo  self.api.get_betinfo reconnect')
                self.connect()
            while self.api.game_betinfo.isSuccessful == None:
                if deadline is not None and time.monotonic() >= deadline:
                    logging.error('**error** get_betinfo timeout')
                    return False, None
                if time.time() - start > 10:
                    logging.error(
                        '**error** get_betinfo time out need reconnect')
                    self.connect()
                    self.api.get_betinfo(id_number)
                    start = time.time()
                time.sleep(self.suspend)
            if self.api.game_betinfo.isSuccessful == True:
                return self.api.game_betinfo.isSuccessful, self.api.game_betinfo.dict
            else:
                return self.api.game_betinfo.isSuccessful, None

    def get_optioninfo(self, limit, timeout=10):
        self.api.api_game_getoptions_result = None
        self.api.get_options(limit)
        start = time.time()
        while self.api.api_game_getoptions_result == None:
            if timeout is not None and time.time() - start > float(timeout):
                self._set_last_operation(
                    "get_optioninfo",
                    "timeout",
                    "timeout",
                    {"limit": limit, "timeout": timeout},
                )
                return None
            time.sleep(min(self.suspend, 0.05))

        self._set_last_operation(
            "get_optioninfo",
            "ok",
            None,
            {"limit": limit},
        )
        return self.api.api_game_getoptions_result

    def get_optioninfo_v2(self, limit, timeout=10):
        self.api.get_options_v2_data = None
        self.api.get_options_v2(limit, "binary,turbo")
        start = time.time()
        while self.api.get_options_v2_data == None:
            if timeout is not None and time.time() - start > float(timeout):
                self._set_last_operation(
                    "get_optioninfo_v2",
                    "timeout",
                    "timeout",
                    {"limit": limit, "timeout": timeout},
                )
                return None
            time.sleep(min(self.suspend, 0.05))

        self._set_last_operation(
            "get_optioninfo_v2",
            "ok",
            None,
            {"limit": limit},
        )
        return self.api.get_options_v2_data

    # __________________________BUY__________________________

    # __________________FOR OPTION____________________________

    def buy_multi(self, price, ACTIVES, ACTION, expirations, timeout=5):
        if len(price) == len(ACTIVES) == len(ACTION) == len(expirations):
            self.api.buy_multi_option = {}
            buy_len = len(price)
            request_ids = []
            for idx in range(buy_len):
                active_id = OP_code.ACTIVES.get(ACTIVES[idx])
                if active_id is None:
                    self._set_last_operation(
                        "buy_multi",
                        "rejected",
                        "invalid_active",
                        {"active": ACTIVES[idx], "index": idx},
                    )
                    return [None] * buy_len
                req_id = _new_request_id("buymulti")
                request_ids.append(req_id)
                self.api.buyv3(
                    price[idx], active_id, ACTION[idx], expirations[idx], req_id)
            start_t = time.time()
            while any(req_id not in self.api.buy_multi_option for req_id in request_ids):
                if timeout is not None and time.time() - start_t >= float(timeout):
                    logging.error('**warning** buy_multi late 5 sec')
                    self._set_last_operation(
                        "buy_multi",
                        "timeout",
                        "timeout",
                        {"request_ids": request_ids, "timeout": timeout},
                    )
                    return [None] * buy_len
                time.sleep(0.01)
            buy_id = []
            for key in request_ids:
                try:
                    value = self.api.buy_multi_option[key]
                    buy_id.append(value["id"])
                except:
                    buy_id.append(None)

            self._set_last_operation(
                "buy_multi",
                "ok",
                None,
                {"request_ids": request_ids, "count": buy_len},
            )
            return buy_id
        else:
            logging.error('buy_multi error please input all same len')
            self._set_last_operation(
                "buy_multi",
                "rejected",
                "invalid_lengths",
                {
                    "price": len(price),
                    "actives": len(ACTIVES),
                    "actions": len(ACTION),
                    "expirations": len(expirations),
                },
            )
            return None

    def get_remaning(self, duration):
        for remaning in get_remaning_time(self.api.timesync.server_timestamp):
            if remaning[0] == duration:
                return remaning[1]
        logging.error('get_remaning(self,duration) ERROR duration')
        return "ERROR duration"

    def buy_by_raw_expirations(self, price, active, direction, option, expired, timeout=5):
        active_id = OP_code.ACTIVES.get(active)
        if active_id is None:
            self._set_last_operation(
                "buy_by_raw_expirations",
                "rejected",
                "invalid_active",
                {"active": active},
            )
            return False, None
        try:
            timeout = None if timeout is None else float(timeout)
        except (TypeError, ValueError):
            self._set_last_operation(
                "buy_by_raw_expirations",
                "rejected",
                "invalid_timeout",
                {"active": active, "timeout": timeout},
            )
            return False, None

        self.api.buy_multi_option = {}
        self.api.buy_successful = None
        req_id = _new_request_id("buyraw")
        self.api.buy_multi_option[req_id] = {"id": None}
        self.api.buyv3_by_raw_expired(
            price, active_id, direction, option, expired, request_id=req_id)
        start_t = time.time()
        id = None
        self.api.result = None
        while self.api.result == None or id == None:
            try:
                if "message" in self.api.buy_multi_option[req_id].keys():
                    logging.error(
                        '**warning** buy' + str(self.api.buy_multi_option[req_id]["message"]))
                    self._set_last_operation(
                        "buy_by_raw_expirations",
                        "rejected",
                        "broker_message",
                        self.api.buy_multi_option[req_id],
                    )
                    return False, self.api.buy_multi_option[req_id]["message"]
            except:
                pass
            try:
                id = self.api.buy_multi_option[req_id]["id"]
            except:
                pass
            if timeout is not None and time.time() - start_t >= timeout:
                logging.error('**warning** buy late %s sec', timeout)
                self._set_last_operation(
                    "buy_by_raw_expirations",
                    "timeout",
                    "timeout",
                    {"request_id": req_id, "timeout": timeout},
                )
                return False, None
            time.sleep(0.01)

        self._set_last_operation(
            "buy_by_raw_expirations",
            "ok",
            None,
            {"request_id": req_id, "id": self.api.buy_multi_option[req_id]["id"]},
        )
        return self.api.result, self.api.buy_multi_option[req_id]["id"]

    def buy(self, price, ACTIVES, ACTION, expirations, timeout=5):
        active_id = OP_code.ACTIVES.get(ACTIVES)
        if active_id is None:
            self._set_last_operation(
                "buy",
                "rejected",
                "invalid_active",
                {"active": ACTIVES},
            )
            return False, None
        try:
            timeout = None if timeout is None else float(timeout)
        except (TypeError, ValueError):
            self._set_last_operation(
                "buy",
                "rejected",
                "invalid_timeout",
                {"active": ACTIVES, "timeout": timeout},
            )
            return False, None
        self.api.buy_multi_option = {}
        self.api.buy_successful = None
        req_id = _new_request_id("buy")
        self.api.buy_multi_option[req_id] = {"id": None}
        self.api.buyv3(
            price, active_id, ACTION, expirations, req_id)
        start_t = time.time()
        id = None
        self.api.result = None
        while self.api.result == None or id == None:
            try:
                if "message" in self.api.buy_multi_option[req_id].keys():
                    self._set_last_operation(
                        "buy",
                        "rejected",
                        "broker_message",
                        self.api.buy_multi_option[req_id],
                    )
                    return False, self.api.buy_multi_option[req_id]["message"]
            except:
                pass
            try:
                id = self.api.buy_multi_option[req_id]["id"]
            except:
                pass
            if timeout is not None and time.time() - start_t >= timeout:
                logging.error('**warning** buy late %s sec', timeout)
                self._set_last_operation(
                    "buy",
                    "timeout",
                    "timeout",
                    {"request_id": req_id, "timeout": timeout},
                )
                return False, None
            time.sleep(0.01)

        self._set_last_operation(
            "buy",
            "ok",
            None,
            {"request_id": req_id, "id": self.api.buy_multi_option[req_id]["id"]},
        )
        return self.api.result, self.api.buy_multi_option[req_id]["id"]

    def sell_option(self, options_ids, timeout=10):
        self.api.sold_options_respond = None
        self.api.sell_option(options_ids)
        start = time.time()
        while self.api.sold_options_respond == None:
            if timeout is not None and time.time() - start > float(timeout):
                self._set_last_operation(
                    "sell_option",
                    "timeout",
                    "timeout",
                    {"options_ids": options_ids, "timeout": timeout},
                )
                return None
            time.sleep(min(self.suspend, 0.05))
        self._set_last_operation(
            "sell_option",
            "ok",
            None,
            {"options_ids": options_ids},
        )
        return self.api.sold_options_respond

    # __________________for Digital___________________

    def get_digital_underlying_list_data(self, timeout=30):
        self.api.underlying_list_data = None
        self.api.get_digital_underlying()
        start_t = time.time()
        while self.api.underlying_list_data == None:
            if timeout is not None and time.time() - start_t >= float(timeout):
                logging.error(
                    '**warning** get_digital_underlying_list_data late 30 sec')
                self._set_last_operation(
                    "get_digital_underlying_list_data",
                    "timeout",
                    "timeout",
                    {"timeout": timeout},
                )
                return None
            time.sleep(min(self.suspend, 0.05))

        self._set_last_operation(
            "get_digital_underlying_list_data",
            "ok",
            None,
            None,
        )
        return self.api.underlying_list_data

    def get_strike_list(self, ACTIVES, duration, timeout=10):
        self.api.strike_list = None
        self.api.get_strike_list(ACTIVES, duration)
        ans = {}
        start = time.time()
        while self.api.strike_list == None:
            if timeout is not None and time.time() - start > float(timeout):
                self._set_last_operation(
                    "get_strike_list",
                    "timeout",
                    "timeout",
                    {"active": ACTIVES, "duration": duration, "timeout": timeout},
                )
                return None, None
            time.sleep(min(self.suspend, 0.05))
        try:
            for data in self.api.strike_list["msg"]["strike"]:
                temp = {}
                temp["call"] = data["call"]["id"]
                temp["put"] = data["put"]["id"]
                ans[("%.6f" % (float(data["value"]) * 10e-7))] = temp
        except:
            logging.error('**error** get_strike_list read problem...')
            self._set_last_operation(
                "get_strike_list",
                "rejected",
                "invalid_response",
                {"active": ACTIVES, "duration": duration},
            )
            return self.api.strike_list, None
        self._set_last_operation(
            "get_strike_list",
            "ok",
            None,
            {"active": ACTIVES, "duration": duration, "count": len(ans)},
        )
        return self.api.strike_list, ans

    def subscribe_strike_list(self, ACTIVE, expiration_period):
        self.api.subscribe_instrument_quites_generated(
            ACTIVE, expiration_period)

    def unsubscribe_strike_list(self, ACTIVE, expiration_period):
        del self.api.instrument_quites_generated_data[ACTIVE]
        self.api.unsubscribe_instrument_quites_generated(
            ACTIVE, expiration_period)

    def get_instrument_quites_generated_data(self, ACTIVE, duration, timeout=10):
        start = time.time()
        while self.api.instrument_quotes_generated_raw_data[ACTIVE][duration * 60] == {}:
            if timeout is not None and time.time() - start >= float(timeout):
                self._set_last_operation(
                    "get_instrument_quites_generated_data",
                    "timeout",
                    "timeout",
                    {"active": ACTIVE, "duration": duration, "timeout": timeout},
                )
                return None
            time.sleep(min(self.suspend, 0.05))
        self._set_last_operation(
            "get_instrument_quites_generated_data",
            "ok",
            None,
            {"active": ACTIVE, "duration": duration},
        )
        return self.api.instrument_quotes_generated_raw_data[ACTIVE][duration * 60]

    def get_realtime_strike_list(self, ACTIVE, duration, timeout=10):
        start = time.time()
        while True:
            if not self.api.instrument_quites_generated_data[ACTIVE][duration * 60]:
                if timeout is not None and time.time() - start >= float(timeout):
                    self._set_last_operation(
                        "get_realtime_strike_list",
                        "timeout",
                        "quotes_timeout",
                        {"active": ACTIVE, "duration": duration, "timeout": timeout},
                    )
                    return None
                time.sleep(min(self.suspend, 0.05))
            else:
                break
        """
        strike_list dict: price:{call:id,put:id}
        """
        ans = {}
        now_timestamp = self.api.instrument_quites_generated_timestamp[ACTIVE][duration * 60]

        while ans == {}:
            if timeout is not None and time.time() - start >= float(timeout):
                self._set_last_operation(
                    "get_realtime_strike_list",
                    "timeout",
                    "strike_timeout",
                    {"active": ACTIVE, "duration": duration, "timeout": timeout},
                )
                return None
            if self.get_realtime_strike_list_temp_data == {} or now_timestamp != self.get_realtime_strike_list_temp_expiration:
                raw_data, strike_list = self.get_strike_list(ACTIVE, duration, timeout=timeout)
                if raw_data is None or strike_list is None:
                    self._set_last_operation(
                        "get_realtime_strike_list",
                        "timeout",
                        "strike_list_timeout",
                        {"active": ACTIVE, "duration": duration, "timeout": timeout},
                    )
                    return None
                self.get_realtime_strike_list_temp_expiration = raw_data["msg"]["expiration"]
                self.get_realtime_strike_list_temp_data = strike_list
            else:
                strike_list = self.get_realtime_strike_list_temp_data

            profit = self.api.instrument_quites_generated_data[ACTIVE][duration * 60]
            for price_key in strike_list:
                try:
                    side_data = {}
                    for side_key in strike_list[price_key]:
                        detail_data = {}
                        profit_d = profit[strike_list[price_key][side_key]]
                        detail_data["profit"] = profit_d
                        detail_data["id"] = strike_list[price_key][side_key]
                        side_data[side_key] = detail_data
                    ans[price_key] = side_data
                except:
                    pass
            if ans == {}:
                time.sleep(min(self.suspend, 0.05))

        self._set_last_operation(
            "get_realtime_strike_list",
            "ok",
            None,
            {"active": ACTIVE, "duration": duration, "count": len(ans)},
        )
        return ans

    def get_digital_current_profit(self, ACTIVE, duration):
        profit = self.api.instrument_quites_generated_data[ACTIVE][duration * 60]
        for key in profit:
            if key.find("SPT") != -1:
                return profit[key]
        return False

    # thank thiagottjv
    # https://github.com/Lu-Yi-Hsun/iqoptionapi/issues/65#issuecomment-513998357

    def buy_digital_spot(self, active, amount, action, duration, timeout=30):
        # Expiration time need to be formatted like this: YYYYMMDDHHII
        # And need to be on GMT time

        # Type - P or C
        if action == 'put':
            action = 'P'
        elif action == 'call':
            action = 'C'
        else:
            logging.error('buy_digital_spot active error')
            self._set_last_operation(
                "buy_digital_spot",
                "rejected",
                "invalid_action",
                {"active": active, "action": action, "duration": duration},
            )
            return -1
        try:
            duration = int(duration)
            amount = float(amount)
        except (TypeError, ValueError):
            self._set_last_operation(
                "buy_digital_spot",
                "rejected",
                "invalid_amount_or_duration",
                {"active": active, "amount": amount, "duration": duration},
            )
            return False, None
        try:
            timeout = None if timeout is None else float(timeout)
        except (TypeError, ValueError):
            self._set_last_operation(
                "buy_digital_spot",
                "rejected",
                "invalid_timeout",
                {"active": active, "timeout": timeout},
            )
            return False, None
        if not active or duration <= 0 or amount <= 0:
            self._set_last_operation(
                "buy_digital_spot",
                "rejected",
                "invalid_input",
                {"active": active, "amount": amount, "duration": duration},
            )
            return False, None
        # doEURUSD201907191250PT5MPSPT
        timestamp = int(self.api.timesync.server_timestamp)
        if duration == 1:
            exp, _ = get_expiration_time(timestamp, duration)
        else:
            now_date = datetime.fromtimestamp(
                timestamp) + timedelta(minutes=1, seconds=30)
            while True:
                if now_date.minute % duration == 0 and time.mktime(now_date.timetuple()) - timestamp > 30:
                    break
                now_date = now_date + timedelta(minutes=1)
            exp = time.mktime(now_date.timetuple())

        dateFormated = str(datetime.utcfromtimestamp(
            exp).strftime("%Y%m%d%H%M"))
        instrument_id = "do" + active + dateFormated + \
                        "PT" + str(duration) + "M" + action + "SPT"
        self.api.digital_option_placed_id = None

        self.api.place_digital_option(instrument_id, amount)
        start_t = time.time()
        while self.api.digital_option_placed_id == None:
            if timeout is not None and time.time() - start_t > float(timeout):
                logging.error('buy_digital_spot loss digital_option_placed_id')
                self._set_last_operation(
                    "buy_digital_spot",
                    "timeout",
                    "timeout",
                    {"instrument_id": instrument_id, "timeout": timeout},
                )
                return False, None
            time.sleep(0.01)
        placed_id = self.api.digital_option_placed_id
        order_id = None
        if isinstance(placed_id, int) and not isinstance(placed_id, bool):
            order_id = placed_id
        elif isinstance(placed_id, str) and placed_id.strip():
            order_id = placed_id.strip()
        elif isinstance(placed_id, dict):
            for key in ("id", "position_id", "order_id"):
                value = placed_id.get(key)
                if isinstance(value, int) and not isinstance(value, bool):
                    order_id = value
                    break
                if isinstance(value, str) and value.strip():
                    order_id = value.strip()
                    break
        if order_id is not None:
            self._set_last_operation(
                "buy_digital_spot",
                "ok",
                None,
                {"instrument_id": instrument_id, "id": order_id},
            )
            return True, order_id
        else:
            self._set_last_operation(
                "buy_digital_spot",
                "rejected",
                "broker_message",
                {"instrument_id": instrument_id, "response": self.api.digital_option_placed_id},
            )
            return False, self.api.digital_option_placed_id

    def get_digital_spot_profit_after_sale(self, position_id, timeout=10):
        def get_instrument_id_to_bid(data, instrument_id):
            for row in data["msg"]["quotes"]:
                if row["symbols"][0] == instrument_id:
                    return row["price"]["bid"]
            return None

        # Author:Lu-Yi-Hsun 2019/11/04
        # email:yihsun1992@gmail.com
        # Source code reference
        # https://github.com/Lu-Yi-Hsun/Decompiler-IQ-Option/blob/master/Source%20Code/5.27.0/sources/com/iqoption/dto/entity/position/Position.java#L564
        start = time.time()
        while self.get_async_order(position_id)["position-changed"] == {}:
            if timeout is not None and time.time() - start >= float(timeout):
                self._set_last_operation(
                    "get_digital_spot_profit_after_sale",
                    "timeout",
                    "position_changed_timeout",
                    {"position_id": position_id, "timeout": timeout},
                )
                return None
            time.sleep(min(self.suspend, 0.05))
        # ___________________/*position*/_________________
        position = self.get_async_order(position_id)["position-changed"]["msg"]
        # doEURUSD201911040628PT1MPSPT
        # z mean check if call or not
        if "MPSPT" in position["instrument_id"]:
            z = False
        elif "MCSPT" in position["instrument_id"]:
            z = True
        else:
            logging.error(
                'get_digital_spot_profit_after_sale position error' + str(position["instrument_id"]))
            self._set_last_operation(
                "get_digital_spot_profit_after_sale",
                "rejected",
                "invalid_instrument_id",
                {"position_id": position_id, "instrument_id": position["instrument_id"]},
            )
            return None

        ACTIVES = position['raw_event']['instrument_underlying']
        amount = max(position['raw_event']["buy_amount"], position['raw_event']["sell_amount"])
        start_duration = position["instrument_id"].find("PT") + 2
        end_duration = start_duration + \
                       position["instrument_id"][start_duration:].find("M")

        duration = int(position["instrument_id"][start_duration:end_duration])
        z2 = False

        getAbsCount = position['raw_event']["count"]
        instrumentStrikeValue = position['raw_event']["instrument_strike_value"] / 1000000.0
        spotLowerInstrumentStrike = position['raw_event']["extra_data"]["lower_instrument_strike"] / 1000000.0
        spotUpperInstrumentStrike = position['raw_event']["extra_data"]["upper_instrument_strike"] / 1000000.0

        aVar = position['raw_event']["extra_data"]["lower_instrument_id"]
        aVar2 = position['raw_event']["extra_data"]["upper_instrument_id"]
        getRate = position['raw_event']["currency_rate"]

        # ___________________/*position*/_________________
        instrument_quites_generated_data = self.get_instrument_quites_generated_data(
            ACTIVES, duration, timeout=timeout)
        if instrument_quites_generated_data is None:
            self._set_last_operation(
                "get_digital_spot_profit_after_sale",
                "timeout",
                "quotes_timeout",
                {"position_id": position_id, "active": ACTIVES, "duration": duration},
            )
            return None

        # https://github.com/Lu-Yi-Hsun/Decompiler-IQ-Option/blob/master/Source%20Code/5.5.1/sources/com/iqoption/dto/entity/position/Position.java#L493
        f_tmp = get_instrument_id_to_bid(
            instrument_quites_generated_data, aVar)
        # f is bidprice of lower_instrument_id ,f2 is bidprice of upper_instrument_id
        if f_tmp != None:
            self.get_digital_spot_profit_after_sale_data[position_id]["f"] = f_tmp
            f = f_tmp
        else:
            f = self.get_digital_spot_profit_after_sale_data[position_id]["f"]

        f2_tmp = get_instrument_id_to_bid(
            instrument_quites_generated_data, aVar2)
        if f2_tmp != None:
            self.get_digital_spot_profit_after_sale_data[position_id]["f2"] = f2_tmp
            f2 = f2_tmp
        else:
            f2 = self.get_digital_spot_profit_after_sale_data[position_id]["f2"]

        if (spotLowerInstrumentStrike != instrumentStrikeValue) and f != None and f2 != None:

            if (spotLowerInstrumentStrike > instrumentStrikeValue or instrumentStrikeValue > spotUpperInstrumentStrike):
                if z:
                    instrumentStrikeValue = (spotUpperInstrumentStrike - instrumentStrikeValue) / abs(
                        spotUpperInstrumentStrike - spotLowerInstrumentStrike)
                    f = abs(f2 - f)
                else:
                    instrumentStrikeValue = (instrumentStrikeValue - spotUpperInstrumentStrike) / abs(
                        spotUpperInstrumentStrike - spotLowerInstrumentStrike)
                    f = abs(f2 - f)

            elif z:
                f += ((instrumentStrikeValue - spotLowerInstrumentStrike) /
                      (spotUpperInstrumentStrike - spotLowerInstrumentStrike)) * (f2 - f)
            else:
                instrumentStrikeValue = (spotUpperInstrumentStrike - instrumentStrikeValue) / (
                        spotUpperInstrumentStrike - spotLowerInstrumentStrike)
                f -= f2
            f = f2 + (instrumentStrikeValue * f)

        if z2:
            pass
        if f != None:
            # price=f/getRate
            # https://github.com/Lu-Yi-Hsun/Decompiler-IQ-Option/blob/master/Source%20Code/5.27.0/sources/com/iqoption/dto/entity/position/Position.java#L603
            price = (f / getRate)
            # getAbsCount Reference
            # https://github.com/Lu-Yi-Hsun/Decompiler-IQ-Option/blob/master/Source%20Code/5.27.0/sources/com/iqoption/dto/entity/position/Position.java#L450
            profit = price * getAbsCount - amount
            self._set_last_operation(
                "get_digital_spot_profit_after_sale",
                "ok",
                None,
                {"position_id": position_id, "profit": profit},
            )
            return profit
        else:
            self._set_last_operation(
                "get_digital_spot_profit_after_sale",
                "rejected",
                "missing_bid",
                {"position_id": position_id},
            )
            return None

    def buy_digital(self, amount, instrument_id, timeout=30):
        self.api.digital_option_placed_id = None
        self.api.place_digital_option(instrument_id, amount)
        start_t = time.time()
        while self.api.digital_option_placed_id == None:
            if timeout is not None and time.time() - start_t > float(timeout):
                logging.error('buy_digital loss digital_option_placed_id')
                self._set_last_operation(
                    "buy_digital",
                    "timeout",
                    "timeout",
                    {"instrument_id": instrument_id, "timeout": timeout},
                )
                return False, None
            time.sleep(0.01)
        self._set_last_operation(
            "buy_digital",
            "ok",
            None,
            {"instrument_id": instrument_id, "id": self.api.digital_option_placed_id},
        )
        return True, self.api.digital_option_placed_id

    def close_digital_option(self, position_id, timeout=30):
        self.api.result = None
        start_t = time.time()
        while self.get_async_order(position_id)["position-changed"] == {}:
            if timeout is not None and time.time() - start_t > float(timeout):
                logging.error('close_digital_option loss position-changed')
                self._set_last_operation(
                    "close_digital_option",
                    "timeout",
                    "position_changed_timeout",
                    {"position_id": position_id, "timeout": timeout},
                )
                return False
            time.sleep(0.01)
        position_changed = self.get_async_order(position_id)["position-changed"]["msg"]
        self.api.close_digital_option(position_changed["external_id"])
        start_t = time.time()
        while self.api.result == None:
            if timeout is not None and time.time() - start_t > float(timeout):
                logging.error('close_digital_option loss result')
                self._set_last_operation(
                    "close_digital_option",
                    "timeout",
                    "result_timeout",
                    {"position_id": position_id, "timeout": timeout},
                )
                return False
            time.sleep(0.01)
        self._set_last_operation(
            "close_digital_option",
            "ok",
            None,
            {"position_id": position_id, "result": self.api.result},
        )
        return self.api.result

    def check_win_digital(self, buy_order_id, polling_time, timeout=30):
        start = time.time()
        while True:
            if timeout is not None and time.time() - start >= float(timeout):
                self._set_last_operation(
                    "check_win_digital",
                    "pending",
                    "timeout",
                    {"order_id": buy_order_id, "timeout": timeout},
                )
                return None
            time.sleep(polling_time)
            data = self.get_digital_position(buy_order_id, timeout=timeout)
            if not data:
                continue

            if data["msg"]["position"]["status"] == "closed":
                if data["msg"]["position"]["close_reason"] == "default":
                    profit = data["msg"]["position"]["pnl_realized"]
                    self._set_last_operation(
                        "check_win_digital",
                        "resolved",
                        "default",
                        {"order_id": buy_order_id, "profit": profit},
                    )
                    return profit
                elif data["msg"]["position"]["close_reason"] == "expired":
                    profit = data["msg"]["position"]["pnl_realized"] - data["msg"]["position"]["buy_amount"]
                    self._set_last_operation(
                        "check_win_digital",
                        "resolved",
                        "expired",
                        {"order_id": buy_order_id, "profit": profit},
                    )
                    return profit

    def check_win_digital_v2(self, buy_order_id, timeout=30):
        try:
            timeout = None if timeout is None else float(timeout)
        except (TypeError, ValueError):
            self._set_last_operation(
                "check_win_digital_v2",
                "rejected",
                "invalid_timeout",
                {"order_id": buy_order_id, "timeout": timeout},
            )
            return False, None

        start = time.time()
        while self.get_async_order(buy_order_id)["position-changed"] == {}:
            if timeout is not None and time.time() - start >= timeout:
                self._set_last_operation(
                    "check_win_digital_v2",
                    "pending",
                    "timeout",
                    {"order_id": buy_order_id, "timeout": timeout},
                )
                return False, None
            time.sleep(min(self.suspend, 0.05))
        order_data = self.get_async_order(buy_order_id)["position-changed"]["msg"]
        if order_data != None:
            if order_data["status"] == "closed":
                if order_data["close_reason"] == "expired":
                    profit = order_data["close_profit"] - order_data["invest"]
                    self._set_last_operation(
                        "check_win_digital_v2",
                        "resolved",
                        "expired",
                        {"order_id": buy_order_id, "profit": profit},
                    )
                    return True, profit
                elif order_data["close_reason"] == "default":
                    profit = order_data["pnl_realized"]
                    self._set_last_operation(
                        "check_win_digital_v2",
                        "resolved",
                        "default",
                        {"order_id": buy_order_id, "profit": profit},
                    )
                    return True, profit
            else:
                self._set_last_operation(
                    "check_win_digital_v2",
                    "pending",
                    "open",
                    {"order_id": buy_order_id, "status": order_data.get("status")},
                )
                return False, None
        else:
            self._set_last_operation(
                "check_win_digital_v2",
                "pending",
                "missing_data",
                {"order_id": buy_order_id},
            )
            return False, None

    # ----------------------------------------------------------
    # -----------------BUY_for__Forex__&&__stock(cfd)__&&__ctrpto

    def buy_order(self,
                  instrument_type, instrument_id,
                  side, amount, leverage,
                  type, limit_price=None, stop_price=None,

                  stop_lose_kind=None, stop_lose_value=None,
                  take_profit_kind=None, take_profit_value=None,

                  use_trail_stop=False, auto_margin_call=False,
                  use_token_for_commission=False, timeout=30):
        self.api.buy_order_id = None
        self.api.buy_order(
            instrument_type=instrument_type, instrument_id=instrument_id,
            side=side, amount=amount, leverage=leverage,
            type=type, limit_price=limit_price, stop_price=stop_price,
            stop_lose_value=stop_lose_value, stop_lose_kind=stop_lose_kind,
            take_profit_value=take_profit_value, take_profit_kind=take_profit_kind,
            use_trail_stop=use_trail_stop, auto_margin_call=auto_margin_call,
            use_token_for_commission=use_token_for_commission
        )

        start_t = time.time()
        while self.api.buy_order_id == None:
            if timeout is not None and time.time() - start_t >= float(timeout):
                self._set_last_operation(
                    "buy_order",
                    "timeout",
                    "buy_order_id_timeout",
                    {"instrument_type": instrument_type, "instrument_id": instrument_id, "timeout": timeout},
                )
                return False, None
            time.sleep(min(self.suspend, 0.05))
        check, data = self.get_order(self.api.buy_order_id, timeout=timeout)
        if not check or data is None:
            self._set_last_operation(
                "buy_order",
                "rejected",
                "order_lookup_failed",
                {"order_id": self.api.buy_order_id},
            )
            return False, None
        while data["status"] == "pending_new":
            if timeout is not None and time.time() - start_t >= float(timeout):
                self._set_last_operation(
                    "buy_order",
                    "timeout",
                    "pending_new_timeout",
                    {"order_id": self.api.buy_order_id, "timeout": timeout},
                )
                return False, None
            check, data = self.get_order(self.api.buy_order_id, timeout=timeout)
            if not check or data is None:
                self._set_last_operation(
                    "buy_order",
                    "rejected",
                    "order_lookup_failed",
                    {"order_id": self.api.buy_order_id},
                )
                return False, None
            time.sleep(min(self.suspend, 1))

        if check:
            if data["status"] != "rejected":
                self._set_last_operation(
                    "buy_order",
                    "ok",
                    None,
                    {"order_id": self.api.buy_order_id, "status": data.get("status")},
                )
                return True, self.api.buy_order_id
            else:
                self._set_last_operation(
                    "buy_order",
                    "rejected",
                    "broker_rejected",
                    {"order_id": self.api.buy_order_id, "reject_status": data.get("reject_status")},
                )
                return False, data["reject_status"]
        else:
            self._set_last_operation(
                "buy_order",
                "rejected",
                "order_lookup_failed",
                {"order_id": self.api.buy_order_id},
            )
            return False, None

    def change_auto_margin_call(self, ID_Name, ID, auto_margin_call, timeout=10):
        self.api.auto_margin_call_changed_respond = None
        self.api.change_auto_margin_call(ID_Name, ID, auto_margin_call)
        if not self._wait_for_api_attr("auto_margin_call_changed_respond", timeout):
            self._set_last_operation(
                "change_auto_margin_call",
                "timeout",
                "timeout",
                {"id_name": ID_Name, "id": ID, "timeout": timeout},
            )
            return False, None
        if self.api.auto_margin_call_changed_respond["status"] == 2000:
            self._set_last_operation(
                "change_auto_margin_call",
                "ok",
                None,
                {"id_name": ID_Name, "id": ID},
            )
            return True, self.api.auto_margin_call_changed_respond
        else:
            self._set_last_operation(
                "change_auto_margin_call",
                "rejected",
                "broker_status",
                {"id_name": ID_Name, "id": ID, "status": self.api.auto_margin_call_changed_respond.get("status")},
            )
            return False, self.api.auto_margin_call_changed_respond

    def change_order(self, ID_Name, order_id,
                     stop_lose_kind, stop_lose_value,
                     take_profit_kind, take_profit_value,
                     use_trail_stop, auto_margin_call, timeout=10):
        check = True
        if ID_Name == "position_id":
            check, order_data = self.get_order(order_id, timeout=timeout)
            if not check or order_data is None:
                logging.error('change_order fail to get position_id')
                self._set_last_operation(
                    "change_order",
                    "rejected",
                    "position_lookup_failed",
                    {"order_id": order_id},
                )
                return False, None
            position_id = order_data["position_id"]
            ID = position_id
        elif ID_Name == "order_id":
            ID = order_id
        else:
            logging.error('change_order input error ID_Name')
            self._set_last_operation(
                "change_order",
                "rejected",
                "invalid_id_name",
                {"id_name": ID_Name, "order_id": order_id},
            )
            return False, None

        if check:
            self.api.tpsl_changed_respond = None
            self.api.change_order(
                ID_Name=ID_Name, ID=ID,
                stop_lose_kind=stop_lose_kind, stop_lose_value=stop_lose_value,
                take_profit_kind=take_profit_kind, take_profit_value=take_profit_value,
                use_trail_stop=use_trail_stop)
            self.change_auto_margin_call(
                ID_Name=ID_Name, ID=ID, auto_margin_call=auto_margin_call, timeout=timeout)
            if not self._wait_for_api_attr("tpsl_changed_respond", timeout):
                self._set_last_operation(
                    "change_order",
                    "timeout",
                    "timeout",
                    {"id_name": ID_Name, "id": ID, "timeout": timeout},
                )
                return False, None
            if self.api.tpsl_changed_respond["status"] == 2000:
                self._set_last_operation(
                    "change_order",
                    "ok",
                    None,
                    {"id_name": ID_Name, "id": ID},
                )
                return True, self.api.tpsl_changed_respond["msg"]
            else:
                self._set_last_operation(
                    "change_order",
                    "rejected",
                    "broker_status",
                    {"id_name": ID_Name, "id": ID, "status": self.api.tpsl_changed_respond.get("status")},
                )
                return False, self.api.tpsl_changed_respond
        else:
            logging.error('change_order fail to get position_id')
            self._set_last_operation(
                "change_order",
                "rejected",
                "position_lookup_failed",
                {"order_id": order_id},
            )
            return False, None

    def get_async_order(self, buy_order_id):
        # name': 'position-changed', 'microserviceName': "portfolio"/"digital-options"
        return self.api.order_async[buy_order_id]

    def get_order(self, buy_order_id, timeout=10):
        # self.api.order_data["status"]
        # reject:you can not get this order
        # pending_new:this order is working now
        # filled:this order is ok now
        # new
        self.api.order_data = None
        self.api.get_order(buy_order_id)
        start_t = time.time()
        while self.api.order_data == None:
            if timeout and time.time() - start_t >= float(timeout):
                logging.error('**error** get_order timeout')
                return False, None
            time.sleep(self.suspend)
        if self.api.order_data["status"] == 2000:
            return True, self.api.order_data["msg"]
        else:
            return False, None

    def get_pending(self, instrument_type, timeout=10):
        self.api.deferred_orders = None
        self.api.get_pending(instrument_type)
        start_t = time.time()
        while self.api.deferred_orders == None:
            if timeout and time.time() - start_t >= float(timeout):
                logging.error('**error** get_pending timeout')
                return False, None
            time.sleep(self.suspend)
        if self.api.deferred_orders["status"] == 2000:
            return True, self.api.deferred_orders["msg"]
        else:
            return False, None

    # this function is heavy
    def get_positions(self, instrument_type, timeout=10):
        self.api.positions = None
        self.api.get_positions(instrument_type)
        start_t = time.time()
        while self.api.positions == None:
            if timeout and time.time() - start_t >= float(timeout):
                logging.error('**error** get_positions timeout')
                return False, None
            time.sleep(self.suspend)
        if self.api.positions["status"] == 2000:
            return True, self.api.positions["msg"]
        else:
            return False, None

    def get_position(self, buy_order_id, timeout=10):
        self.api.position = None
        check, order_data = self.get_order(buy_order_id)
        if not check or order_data is None:
            return False, None
        position_id = order_data["position_id"]
        self.api.get_position(position_id)
        start_t = time.time()
        while self.api.position == None:
            if timeout and time.time() - start_t >= float(timeout):
                logging.error('**error** get_position timeout')
                return False, None
            time.sleep(self.suspend)
        if self.api.position["status"] == 2000:
            return True, self.api.position["msg"]
        else:
            return False, None

    # this function is heavy

    def get_digital_position_by_position_id(self, position_id, timeout=10):
        self.api.position = None
        self.api.get_digital_position(position_id)
        if not self._wait_for_api_attr("position", timeout):
            self._set_last_operation(
                "get_digital_position_by_position_id",
                "timeout",
                "timeout",
                {"position_id": position_id, "timeout": timeout},
            )
            return None
        self._set_last_operation(
            "get_digital_position_by_position_id",
            "ok",
            None,
            {"position_id": position_id},
        )
        return self.api.position

    def get_digital_position(self, order_id, timeout=10):
        self.api.position = None
        start = time.time()
        while self.get_async_order(order_id)["position-changed"] == {}:
            if timeout is not None and time.time() - start >= float(timeout):
                self._set_last_operation(
                    "get_digital_position",
                    "timeout",
                    "position_changed_timeout",
                    {"order_id": order_id, "timeout": timeout},
                )
                return None
            time.sleep(min(self.suspend, 0.05))
        position_id = self.get_async_order(order_id)["position-changed"]["msg"]["external_id"]
        self.api.get_digital_position(position_id)
        if not self._wait_for_api_attr("position", timeout):
            self._set_last_operation(
                "get_digital_position",
                "timeout",
                "position_timeout",
                {"order_id": order_id, "position_id": position_id, "timeout": timeout},
            )
            return None
        self._set_last_operation(
            "get_digital_position",
            "ok",
            None,
            {"order_id": order_id, "position_id": position_id},
        )
        return self.api.position

    def get_position_history(self, instrument_type, timeout=10):
        self.api.position_history = None
        self.api.get_position_history(instrument_type)
        if not self._wait_for_api_attr("position_history", timeout):
            self._set_last_operation(
                "get_position_history",
                "timeout",
                "timeout",
                {"instrument_type": instrument_type, "timeout": timeout},
            )
            return False, None

        if self.api.position_history["status"] == 2000:
            self._set_last_operation(
                "get_position_history",
                "ok",
                None,
                {"instrument_type": instrument_type},
            )
            return True, self.api.position_history["msg"]
        else:
            self._set_last_operation(
                "get_position_history",
                "rejected",
                "broker_status",
                {"instrument_type": instrument_type, "status": self.api.position_history.get("status")},
            )
            return False, None

    def get_position_history_v2(self, instrument_type, limit, offset, start, end, timeout=10):
        # instrument_type=crypto forex fx-option multi-option cfd digital-option turbo-option
        self.api.position_history_v2 = None
        self.api.get_position_history_v2(
            instrument_type, limit, offset, start, end)
        if not self._wait_for_api_attr("position_history_v2", timeout):
            self._set_last_operation(
                "get_position_history_v2",
                "timeout",
                "timeout",
                {"instrument_type": instrument_type, "timeout": timeout},
            )
            return False, None

        if self.api.position_history_v2["status"] == 2000:
            self._set_last_operation(
                "get_position_history_v2",
                "ok",
                None,
                {"instrument_type": instrument_type, "limit": limit, "offset": offset},
            )
            return True, self.api.position_history_v2["msg"]
        else:
            self._set_last_operation(
                "get_position_history_v2",
                "rejected",
                "broker_status",
                {"instrument_type": instrument_type, "status": self.api.position_history_v2.get("status")},
            )
            return False, None

    def get_available_leverages(self, instrument_type, actives="", timeout=10):
        self.api.available_leverages = None
        if actives == "":
            self.api.get_available_leverages(instrument_type, "")
        else:
            if actives not in OP_code.ACTIVES:
                self._set_last_operation(
                    "get_available_leverages",
                    "rejected",
                    "invalid_active",
                    {"instrument_type": instrument_type, "active": actives},
                )
                return False, None
            self.api.get_available_leverages(
                instrument_type, OP_code.ACTIVES[actives])
        if not self._wait_for_api_attr("available_leverages", timeout):
            self._set_last_operation(
                "get_available_leverages",
                "timeout",
                "timeout",
                {"instrument_type": instrument_type, "active": actives, "timeout": timeout},
            )
            return False, None
        if self.api.available_leverages["status"] == 2000:
            self._set_last_operation(
                "get_available_leverages",
                "ok",
                None,
                {"instrument_type": instrument_type, "active": actives},
            )
            return True, self.api.available_leverages["msg"]
        else:
            self._set_last_operation(
                "get_available_leverages",
                "rejected",
                "broker_status",
                {"instrument_type": instrument_type, "status": self.api.available_leverages.get("status")},
            )
            return False, None

    def cancel_order(self, buy_order_id, timeout=10):
        self.api.order_canceled = None
        self.api.cancel_order(buy_order_id)
        if not self._wait_for_api_attr("order_canceled", timeout):
            self._set_last_operation(
                "cancel_order",
                "timeout",
                "timeout",
                {"order_id": buy_order_id, "timeout": timeout},
            )
            return False
        if self.api.order_canceled["status"] == 2000:
            self._set_last_operation(
                "cancel_order",
                "ok",
                None,
                {"order_id": buy_order_id},
            )
            return True
        else:
            self._set_last_operation(
                "cancel_order",
                "rejected",
                "broker_status",
                {"order_id": buy_order_id, "status": self.api.order_canceled.get("status")},
            )
            return False

    def close_position(self, position_id, timeout=10):
        check, data = self.get_order(position_id, timeout=timeout)
        if check and data is not None and data["position_id"] != None:
            self.api.close_position_data = None
            self.api.close_position(data["position_id"])
            if not self._wait_for_api_attr("close_position_data", timeout):
                self._set_last_operation(
                    "close_position",
                    "timeout",
                    "timeout",
                    {"position_id": position_id, "timeout": timeout},
                )
                return False
            if self.api.close_position_data["status"] == 2000:
                self._set_last_operation(
                    "close_position",
                    "ok",
                    None,
                    {"position_id": position_id},
                )
                return True
            else:
                self._set_last_operation(
                    "close_position",
                    "rejected",
                    "broker_status",
                    {"position_id": position_id, "status": self.api.close_position_data.get("status")},
                )
                return False
        else:
            self._set_last_operation(
                "close_position",
                "rejected",
                "missing_position",
                {"position_id": position_id},
            )
            return False

    def close_position_v2(self, position_id, timeout=10):
        start = time.time()
        while self.get_async_order(position_id) == None:
            if timeout is not None and time.time() - start >= float(timeout):
                self._set_last_operation(
                    "close_position_v2",
                    "timeout",
                    "position_timeout",
                    {"position_id": position_id, "timeout": timeout},
                )
                return False
            time.sleep(min(self.suspend, 0.05))
        position_changed = self.get_async_order(position_id)
        self.api.close_position_data = None
        self.api.close_position(position_changed["id"])
        if not self._wait_for_api_attr("close_position_data", timeout):
            self._set_last_operation(
                "close_position_v2",
                "timeout",
                "close_timeout",
                {"position_id": position_id, "timeout": timeout},
            )
            return False
        if self.api.close_position_data["status"] == 2000:
            self._set_last_operation(
                "close_position_v2",
                "ok",
                None,
                {"position_id": position_id},
            )
            return True
        else:
            self._set_last_operation(
                "close_position_v2",
                "rejected",
                "broker_status",
                {"position_id": position_id, "status": self.api.close_position_data.get("status")},
            )
            return False

    def get_overnight_fee(self, instrument_type, active, timeout=10):
        if active not in OP_code.ACTIVES:
            self._set_last_operation(
                "get_overnight_fee",
                "rejected",
                "invalid_active",
                {"instrument_type": instrument_type, "active": active},
            )
            return False, None
        self.api.overnight_fee = None
        self.api.get_overnight_fee(instrument_type, OP_code.ACTIVES[active])
        if not self._wait_for_api_attr("overnight_fee", timeout):
            self._set_last_operation(
                "get_overnight_fee",
                "timeout",
                "timeout",
                {"instrument_type": instrument_type, "active": active, "timeout": timeout},
            )
            return False, None
        if self.api.overnight_fee["status"] == 2000:
            self._set_last_operation(
                "get_overnight_fee",
                "ok",
                None,
                {"instrument_type": instrument_type, "active": active},
            )
            return True, self.api.overnight_fee["msg"]
        else:
            self._set_last_operation(
                "get_overnight_fee",
                "rejected",
                "broker_status",
                {"instrument_type": instrument_type, "status": self.api.overnight_fee.get("status")},
            )
            return False, None

    def get_option_open_by_other_pc(self):
        return self.api.socket_option_opened

    def del_option_open_by_other_pc(self, id):
        del self.api.socket_option_opened[id]

    # -----------------------------------------------------------------

    def opcode_to_name(self, opcode):
        return list(OP_code.ACTIVES.keys())[list(OP_code.ACTIVES.values()).index(opcode)]

    # name:
    # "live-deal-binary-option-placed"
    # "live-deal-digital-option"
    def subscribe_live_deal(self, name, active, _type, buffersize):
        if name not in ("live-deal-binary-option-placed", "live-deal-digital-option", "live-deal"):
            self._set_last_operation(
                "subscribe_live_deal",
                "rejected",
                "invalid_name",
                {"name": name, "active": active, "type": _type},
            )
            return False
        active_id = OP_code.ACTIVES.get(active)
        if active_id is None:
            self._set_last_operation(
                "subscribe_live_deal",
                "rejected",
                "invalid_active",
                {"name": name, "active": active, "type": _type},
            )
            return False
        try:
            buffersize = int(buffersize)
        except (TypeError, ValueError):
            self._set_last_operation(
                "subscribe_live_deal",
                "rejected",
                "invalid_buffersize",
                {"name": name, "active": active, "type": _type, "buffersize": buffersize},
            )
            return False
        if buffersize <= 0:
            self._set_last_operation(
                "subscribe_live_deal",
                "rejected",
                "invalid_buffersize",
                {"name": name, "active": active, "type": _type, "buffersize": buffersize},
            )
            return False
        self.api.live_deal_data[name][active][_type] = deque(list(), buffersize)
        self.api.Subscribe_Live_Deal(name, active_id, _type)
        self._set_last_operation(
            "subscribe_live_deal",
            "ok",
            None,
            {"name": name, "active": active, "type": _type, "buffersize": buffersize},
        )
        return True
        """
        self.api.live_deal_data[name][active][_type]=deque(list(),buffersize) 

        while len(self.api.live_deal_data[name][active][_type])==0:
            self.api.Subscribe_Live_Deal(name,active_id,_type)
            time.sleep(1)
        """

    def unscribe_live_deal(self, name, active, _type):
        if name not in ("live-deal-binary-option-placed", "live-deal-digital-option", "live-deal"):
            self._set_last_operation(
                "unscribe_live_deal",
                "rejected",
                "invalid_name",
                {"name": name, "active": active, "type": _type},
            )
            return False
        active_id = OP_code.ACTIVES.get(active)
        if active_id is None:
            self._set_last_operation(
                "unscribe_live_deal",
                "rejected",
                "invalid_active",
                {"name": name, "active": active, "type": _type},
            )
            return False
        self.api.Unscribe_Live_Deal(name, active_id, _type)
        try:
            self.api.live_deal_data[name][active][_type].clear()
        except Exception:
            pass
        self._set_last_operation(
            "unscribe_live_deal",
            "ok",
            None,
            {"name": name, "active": active, "type": _type},
        )
        return True
        """

        while len(self.api.live_deal_data[name][active][_type])!=0:
            self.api.Unscribe_Live_Deal(name,active_id,_type)
            del self.api.live_deal_data[name][active][_type]
            time.sleep(1)
        """

    def get_live_deal(self, name, active, _type):
        return self.api.live_deal_data[name][active][_type]

    def pop_live_deal(self, name, active, _type):
        try:
            value = self.api.live_deal_data[name][active][_type].pop()
        except IndexError:
            self._set_last_operation(
                "pop_live_deal",
                "empty",
                "empty",
                {"name": name, "active": active, "type": _type},
            )
            return None
        self._set_last_operation(
            "pop_live_deal",
            "ok",
            None,
            {"name": name, "active": active, "type": _type},
        )
        return value

    def clear_live_deal(self, name, active, _type, buffersize):
        try:
            buffersize = int(buffersize)
        except (TypeError, ValueError):
            self._set_last_operation(
                "clear_live_deal",
                "rejected",
                "invalid_buffersize",
                {"name": name, "active": active, "type": _type, "buffersize": buffersize},
            )
            return False
        if buffersize <= 0:
            self._set_last_operation(
                "clear_live_deal",
                "rejected",
                "invalid_buffersize",
                {"name": name, "active": active, "type": _type, "buffersize": buffersize},
            )
            return False
        self.api.live_deal_data[name][active][_type] = deque(
            list(), buffersize)
        self._set_last_operation(
            "clear_live_deal",
            "ok",
            None,
            {"name": name, "active": active, "type": _type, "buffersize": buffersize},
        )
        return True

    def get_user_profile_client(self, user_id, timeout=10):
        self.api.user_profile_client = None
        self.api.Get_User_Profile_Client(user_id)
        if not self._wait_for_api_attr("user_profile_client", timeout):
            self._set_last_operation(
                "get_user_profile_client",
                "timeout",
                "timeout",
                {"user_id": user_id, "timeout": timeout},
            )
            return None

        self._set_last_operation(
            "get_user_profile_client",
            "ok",
            None,
            {"user_id": user_id},
        )
        return self.api.user_profile_client

    def request_leaderboard_userinfo_deals_client(self, user_id, country_id, timeout=10):
        self.api.leaderboard_userinfo_deals_client = None

        start = time.time()
        while True:
            try:
                if self.api.leaderboard_userinfo_deals_client["isSuccessful"] == True:
                    break
            except:
                pass
            if timeout is not None and time.time() - start >= float(timeout):
                self._set_last_operation(
                    "request_leaderboard_userinfo_deals_client",
                    "timeout",
                    "timeout",
                    {"user_id": user_id, "country_id": country_id, "timeout": timeout},
                )
                return None
            self.api.Request_Leaderboard_Userinfo_Deals_Client(
                user_id, country_id)
            time.sleep(min(0.2, self.suspend))

        self._set_last_operation(
            "request_leaderboard_userinfo_deals_client",
            "ok",
            None,
            {"user_id": user_id, "country_id": country_id},
        )
        return self.api.leaderboard_userinfo_deals_client

    def get_users_availability(self, user_id, timeout=10):
        self.api.users_availability = None

        start = time.time()
        while self.api.users_availability == None:
            if timeout is not None and time.time() - start >= float(timeout):
                self._set_last_operation(
                    "get_users_availability",
                    "timeout",
                    "timeout",
                    {"user_id": user_id, "timeout": timeout},
                )
                return None
            self.api.Get_Users_Availability(user_id)
            time.sleep(min(0.2, self.suspend))
        self._set_last_operation(
            "get_users_availability",
            "ok",
            None,
            {"user_id": user_id},
        )
        return self.api.users_availability
