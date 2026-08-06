"""Module for IQ option candles websocket chanel."""

from iqoptionapi.ws.chanels.base import Base
import time

class GetCandles(Base):
    """Class for IQ option candles websocket chanel."""
    # pylint: disable=too-few-public-methods

    name = "sendMessage"

    def __call__(self, active_id, interval, count,endtime, request_id=""):
        """Method to send message to candles websocket chanel.

        :param active_id: The active/asset identifier.
        :param duration: The candle duration (timeframe for the candles).
        :param amount: The number of candles you want to have
        """
        #thank SeanStayn share new request
        #https://github.com/n1nj4z33/iqoptionapi/issues/88
        data = {"name":"get-candles",
                "version":"2.0",
                "body":{
                        "active_id":int(active_id),
                        "size":interval,#time size sample:if interval set 1 mean get time 0~1 candle 
                        "to":int(endtime),   #int(self.api.timesync.server_timestamp),
                        "count":count#get how many candle
                        }
                }

        self.send_websocket_request(self.name, data, request_id=str(request_id))
