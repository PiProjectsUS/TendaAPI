import datetime
import threading
import time
import requests
import base64

from colorama import Fore


class TendaError(Exception):
    pass


class TendaManager(object):

    __AUTH_URL = 'http://{}/login/Auth'
    __GET_QOS = 'http://{}/goform/getQos'
    __SET_QOS = 'http://{}/goform/setQos'
    __REBOOT_URL = 'http://{}/goform/sysReboot'
    __WIFI_SETTINGS_URL = 'http://{}/goform/getWifi'
    __COOKIE = ''

    live_updater = False
    last_online_devices = []
    online_log = {}
    blacklist = []
    last_reset = datetime.datetime.today().strftime('%Y-%m-%d')

    def __init__(self, ip_address, password):
        self.IP = ip_address
        self.PASSWORD = password
        self.__AUTH_URL = self.__AUTH_URL.format(ip_address)
        self.__GET_QOS = self.__GET_QOS.format(ip_address)
        self.__SET_QOS = self.__SET_QOS.format(ip_address)
        self.__REBOOT_URL = self.__REBOOT_URL.format(ip_address)
        self.do_login()

    def __encodeB64(self, string):
        return base64.b64encode(string.encode()).decode("utf-8")

    def __bake_requests(self):
        return {
            'Cookie': 'bLanguage=en; {}'.format(self.__COOKIE),
            'DNT': '1',
            'Host': '%s' % (self.IP),
            'Referrer': 'http://%s/index.html' % (self.IP)
        }

    def do_login(self):
        form_data = {
            'password': self.__encodeB64(self.PASSWORD)
        }
        try:
            response = requests.post(self.__AUTH_URL, form_data, allow_redirects=False)
        except requests.exceptions.RequestException as e:
            raise TendaError(e)

        if 'Set-Cookie' in response.headers:
            self.__COOKIE = response.headers['Set-Cookie'].split(';')[0]
        else:
            raise TendaError('Authentication Failed')

    def track_online_run(self):
        self.live_updater = True
        t1 = threading.Thread(target=self.track_online)
        t1.start()

    def track_online(self):
        while True:
            self.reset_day()
            self.get_online_devices_with_stats()
            time.sleep(7.5)

    def reset_day(self):
        if datetime.datetime.today().strftime('%Y-%m-%d') != self.last_reset:
            self.online_log = {}
            self.last_reset = datetime.datetime.today().strftime('%Y-%m-%d')

    def get_online_devices_with_stats(self):
        request_headers = self.__bake_requests()

        params = {
            'modules': 'onlineList'
        }

        response = requests.get(
            self.__GET_QOS, params, headers=request_headers, allow_redirects=False)

        if response.status_code == 302:
            self.do_login()
            return self.get_online_devices_with_stats()
        else:
            online = response.json()['onlineList']
            if self.live_updater:
                for device in online:
                    download = float(device['qosListDownSpeed'])
                    upload = float(device['qosListUpSpeed'])

                    # Haven't seen this client yet
                    if device['qosListIP'] not in self.online_log:
                        # Client is active
                        if download > 0 or upload > 0:
                            data = {
                                "Access": device['qosListAccess'],
                                "ConnectionType": device['qosListConnectType'],
                                'DownloadLimit': float(device['qosListDownLimit']),
                                'DownloadSpeed': float(device['qosListDownSpeed']),
                                'Hostname': device['qosListHostname'],
                                'IP': device['qosListIP'],
                                'MAC': device['qosListMac'],
                                'Manufacturer': device['qosListManufacturer'],
                                'Named': device['qosListRemark'],
                                'UploadLimit': float(device['qosListUpLimit']),
                                'UploadSpeed': float(device['qosListUpSpeed']),
                                "ConnectTime": device['qoslistConnetTime'],
                                "Status": "Online",
                                "TotalTimeToday": 0,
                                "TmpTotalTimeToday": 0,
                                "FirstSeen": time.time(),
                                "LastSeen": time.time()
                            }
                            self.online_log[device['qosListIP']] = data
                            print(device['qosListMac'])
                            print(Fore.BLUE + "Detected new client online [" + device['qosListIP'] + " - " + device['qosListRemark'] + "] [" + device['qosListDownSpeed'] + "/" + device['qosListUpSpeed'] + "]" + Fore.RESET)
                        else:  # Client is not active
                            pass
                    else:  # Client we have seen
                        # Client is active
                        if download > 0 or upload > 0:
                            self.online_log[device['qosListIP']]['Access'] = device['qosListAccess']
                            self.online_log[device['qosListIP']]['DownloadLimit'] = float(device['qosListDownLimit'])
                            self.online_log[device['qosListIP']]['DownloadSpeed'] = float(device['qosListDownSpeed'])
                            self.online_log[device['qosListIP']]['UploadLimit'] = float(device['qosListUpLimit'])
                            self.online_log[device['qosListIP']]['UploadSpeed'] = float(device['qosListUpSpeed'])
                            self.online_log[device['qosListIP']]['LastSeen'] = time.time()
                            if self.online_log[device['qosListIP']]['Status'] == "Online":
                                self.online_log[device['qosListIP']]['TmpTotalTimeToday'] = self.online_log[device['qosListIP']]['TotalTimeToday'] + (time.time() - self.online_log[device['qosListIP']]['FirstSeen'])
                                print(Fore.YELLOW + "Client Updated [" + device['qosListIP'] + " - " + device['qosListRemark'] + "] [TTT: " + str(self.online_log[device['qosListIP']]['TmpTotalTimeToday']) + "] [Time: " + str(time.time() - self.online_log[device['qosListIP']]['FirstSeen']) + "]" + Fore.RESET)
                            else:
                                self.online_log[device['qosListIP']]['Status'] = "Online"
                                self.online_log[device['qosListIP']]['FirstSeen'] = time.time()
                                self.online_log[device['qosListIP']]['TmpTotalTimeToday'] = self.online_log[device['qosListIP']]['TotalTimeToday'] + (time.time() - self.online_log[device['qosListIP']]['FirstSeen'])
                                print(Fore.GREEN + "Client reconnected [" + device['qosListIP'] + " - " + device['qosListRemark'] + "] [TTT: " + str(self.online_log[device['qosListIP']]['TmpTotalTimeToday']) + "]" + Fore.RESET)

                        elif self.online_log[device['qosListIP']]['FirstSeen'] != 0:  # Client is not active
                            ts = time.time() - self.online_log[device['qosListIP']]['LastSeen']
                            if ts > 300:
                                self.online_log[device['qosListIP']]['FirstSeen'] = 0
                                self.online_log[device['qosListIP']]['TotalTimeToday'] += ts
                                print(Fore.RED + "Client Offline [" + device['qosListIP'] + " - " + device['qosListRemark'] + "] [TT: " + str(self.online_log[device['qosListIP']]['TotalTimeToday']) + "]" + Fore.RESET)
                                self.online_log[device['qosListIP']]['Status'] = "Offline"

            self.last_online_devices = online
            return online

    def get_black_list(self):
        request_headers = self.__bake_requests()

        params = {
            'modules': 'macFilter'
        }

        response = requests.get(
            self.__GET_QOS, params, headers=request_headers, allow_redirects=False)

        if response.status_code == 302:
            self.do_login()
            return self.get_black_list()
        else:
            bl = response.json()['macFilter']['macFilterList']
            return bl

    def block_device(self, mac_address):
        if mac_address.casefold() not in self.blacklist:
            self.blacklist.append(mac_address.casefold())
            return self.run_block_list()
        return False

    def unblock_device(self, mac_address):
        if mac_address.casefold() in self.blacklist:
            self.blacklist.remove(mac_address.casefold())
            return self.run_block_list()
        return False

    def run_block_list(self):
        onl_list = ''
        ofl_list = ''
        request_headers = self.__bake_requests()
        online_list = self.get_online_devices_with_stats()

        for device in online_list:
            if device['qosListMac'].casefold() in self.blacklist:
                ofl_list += '{}\t{}\t{}\t{}\t{}\t{}\n'.format(
                    device['qosListHostname'], device['qosListRemark'], device['qosListMac'], '0', '0', 'false')
            else:
                onl_list += '{}\t{}\t{}\t{}\t{}\t{}\n'.format(
                    device['qosListHostname'], device['qosListRemark'], device['qosListMac'], '99999', '99999', 'true')

        form_data = {
            'module1': 'onlineList',
            'onlineList': onl_list,
            'module2': 'macFilter',
            'macFilterList': ofl_list
        }

        response = requests.post(self.__SET_QOS, data=form_data,
                                 headers=request_headers, allow_redirects=False)

        err = response.json()['errCode']
        if err == '0':
            return True

        return False
