import datetime
import requests
import json5
import json
import time
import logging
import asyncio
import datetime
import json
import logging
import random
import time
import requests
from colorlog import ColoredFormatter
from utilities import (
  SortUpgrades,
  NumberToString,
  DailyCipherDecode,
  TextToMorseCode,
)

# ---------------------------------------------#
# Configuration Loading
# ---------------------------------------------#

# Load configuration from JSON file
with open('config.jsonc', 'r') as config_file:
  config = json5.load(config_file)

# Extract the loaded configuration
AccountsRecheckTime = config.get('AccountsRecheckTime', 300)
MaxRandomDelay = config.get('MaxRandomDelay', 120)
AccountList = config.get('AccountList', [])
telegramBotLogging = config.get('telegramBotLogging')

# ---------------------------------------------#
# Logging configuration
LOG_LEVEL = logging.DEBUG
LOG_FORMAT = "%(log_color)s[Master HamsterKombat Bot]%(reset)s[%(log_color)s%(levelname)s%(reset)s][%(log_color)s%(asctime)s%(reset)s]%(log_color)s%(message)s%(reset)s"
logging.root.setLevel(LOG_LEVEL)
formatter = ColoredFormatter(LOG_FORMAT)
stream = logging.StreamHandler()
stream.setLevel(LOG_LEVEL)
stream.setFormatter(formatter)
log = logging.getLogger("pythonConfig")
log.setLevel(LOG_LEVEL)
log.addHandler(stream)


# End of configuration
# ---------------------------------------------#


class HamsterKombatAccount:
  def __init__(self, AccountData):
    self.account_name = AccountData["account_name"]
    self.Authorization = AccountData["Authorization"]
    self.UserAgent = AccountData["UserAgent"]
    self.Proxy = AccountData["Proxy"]
    self.config = AccountData["config"]
    self.isAndroidDevice = "Android" in self.UserAgent
    self.balanceCoins = 0
    self.availableTaps = 0
    self.maxTaps = 0
    self.ProfitPerHour = 0
    self.earnPassivePerHour = 0
    self.SpendTokens = 0
    self.account_data = None
    self.telegram_chat_id = AccountData["telegram_chat_id"]

  def SendTelegramLog(self, message, level):
    print(message)
    if (
        not telegramBotLogging["is_active"]
        or self.telegram_chat_id == ""
        or telegramBotLogging["bot_token"] == ""
    ):
      return

    if (
        level not in telegramBotLogging["messages"]
        or telegramBotLogging["messages"][level] is False
    ):
      return

    requests.get(
      f"https://api.telegram.org/bot{telegramBotLogging['bot_token']}/sendMessage?chat_id={self.telegram_chat_id}&text={message}"
    )

  # Sending sync request
  def UpgradesForBuyRequest(self):
    url = "https://api.hamsterkombat.io/clicker/upgrades-for-buy"
    headers = {
      "Access-Control-Request-Headers": "authorization",
      "Access-Control-Request-Method": "POST",
    }

    # Send OPTIONS request
    self.HttpRequest(url, headers, "OPTIONS", 204)

    headers = {
      "Authorization": self.Authorization,
    }

    # Send POST request
    return self.HttpRequest(url, headers, "POST", 200)

  # Get list of upgrades to buy
  def HttpRequest(self, url, headers, method="POST", validStatusCodes=200, payload=None):
    """
    Returns:
        Union[Any, bool]: Description of what the return value represents.
    """

    # Default headers
    defaultHeaders = {
      "Accept": "*/*",
      "Connection": "keep-alive",
      "Host": "api.hamsterkombat.io",
      "Origin": "https://hamsterkombat.io",
      "Referer": "https://hamsterkombat.io/",
      "Sec-Fetch-Dest": "empty",
      "Sec-Fetch-Mode": "cors",
      "Sec-Fetch-Site": "same-site",
      "User-Agent": self.UserAgent,
    }

    # Add default headers for Android devices to avoid detection, Not needed for iOS devices
    if self.isAndroidDevice:
      defaultHeaders["HTTP_SEC_CH_UA_PLATFORM"] = '"Android"'
      defaultHeaders["HTTP_SEC_CH_UA_MOBILE"] = "?1"
      defaultHeaders["HTTP_SEC_CH_UA"] = '"Android WebView";v="125", "Chromium";v="125", "Not.A/Brand";v="24"'
      defaultHeaders["HTTP_X_REQUESTED_WITH"] = "org.telegram.messenger.web"

    # Add and replace new headers to default headers
    for key, value in headers.items():
      defaultHeaders[key] = value

    try:
      if method == "POST":
        response = requests.post(url, headers=headers, data=payload, proxies=self.Proxy)
      elif method == "OPTIONS":
        response = requests.options(url, headers=headers, proxies=self.Proxy)
      else:
        log.error(f"[{self.account_name}] Invalid method: {method}")
        self.SendTelegramLog(f"[{self.account_name}] Invalid method: {method}", "http_errors")
        return False

      if response.status_code != validStatusCodes:
        log.error(f"[{self.account_name}] Status code is not {validStatusCodes}")
        log.error(f"[{self.account_name}] Response: {response.text}")
        self.SendTelegramLog(f"[{self.account_name}] Status code is not {validStatusCodes}", "http_errors")
        return False

      if method == "OPTIONS":
        return True

      return response.json()
    except Exception as e:
      log.error(f"[{self.account_name}] Error: {e}")
      self.SendTelegramLog(f"[{self.account_name}] Error: {e}", "http_errors")
      return False

  # Send HTTP requests
  def syncRequest(self):
    url = "https://api.hamsterkombat.io/clicker/sync"
    headers = {
      "Access-Control-Request-Headers": self.Authorization,
      "Access-Control-Request-Method": "POST",
    }

    # Send OPTIONS request
    self.HttpRequest(url, headers, "OPTIONS", 204)

    headers = {
      "Authorization": self.Authorization,
    }

    # Send POST request
    return self.HttpRequest(url, headers, "POST", 200)

  # Buy an upgrade
  def BuyUpgradeRequest(self, UpgradeId):
    url = "https://api.hamsterkombat.io/clicker/buy-upgrade"
    headers = {
      "Access-Control-Request-Headers": "authorization,content-type",
      "Access-Control-Request-Method": "POST",
    }

    # Send OPTIONS request
    self.HttpRequest(url, headers, "OPTIONS", 204)

    headers = {
      "Authorization": self.Authorization,
      "Content-Type": "application/json",
      "Accept": "application/json",
    }

    payload = json.dumps({
      "upgradeId": UpgradeId,
      "timestamp": int(datetime.datetime.now().timestamp() * 1000),
    })

    # Send POST request
    return self.HttpRequest(url, headers, "POST", 200, payload)

  # Tap the hamster
  def TapRequest(self, tap_count):
    url = "https://api.hamsterkombat.io/clicker/tap"
    headers = {
      "Access-Control-Request-Headers": "authorization,content-type",
      "Access-Control-Request-Method": "POST",
    }

    # Send OPTIONS request
    self.HttpRequest(url, headers, "OPTIONS", 204)

    headers = {
      "Accept": "application/json",
      "Authorization": self.Authorization,
      "Content-Type": "application/json",
    }

    payload = json.dumps({
      "timestamp": int(datetime.datetime.now().timestamp() * 1000),
      "availableTaps": 0,
      "count": int(tap_count),
    })

    # Send POST request
    return self.HttpRequest(url, headers, "POST", 200, payload)

  # Get list of boosts to buy
  def BoostsToBuyListRequest(self):
    url = "https://api.hamsterkombat.io/clicker/boosts-for-buy"
    headers = {
      "Access-Control-Request-Headers": "authorization",
      "Access-Control-Request-Method": "POST",
    }

    # Send OPTIONS request
    self.HttpRequest(url, headers, "OPTIONS", 204)

    headers = {
      "Authorization": self.Authorization,
    }

    # Send POST request
    return self.HttpRequest(url, headers, "POST", 200)

  # Buy a boost
  def BuyBoostRequest(self, boost_id):
    url = "https://api.hamsterkombat.io/clicker/buy-boost"
    headers = {
      "Access-Control-Request-Headers": "authorization,content-type",
      "Access-Control-Request-Method": "POST",
    }

    # Send OPTIONS request
    self.HttpRequest(url, headers, "OPTIONS", 204)

    headers = {
      "Accept": "application/json",
      "Authorization": self.Authorization,
      "Content-Type": "application/json",
    }

    payload = json.dumps({
      "boostId": boost_id,
      "timestamp": int(datetime.datetime.now().timestamp() * 1000),
    })

    # Send POST request
    return self.HttpRequest(url, headers, "POST", 200, payload)

  def getAccountData(self):
    account_data = self.syncRequest()
    if account_data is None or account_data is False:
      log.error(f"[{self.account_name}] Unable to get account data.")
      self.SendTelegramLog(
        f"[{self.account_name}] Unable to get account data.", "other_errors"
      )
      return False

    if "clickerUser" not in account_data:
      log.error(f"[{self.account_name}] Invalid account data.")
      self.SendTelegramLog(
        f"[{self.account_name}] Invalid account data.", "other_errors"
      )
      return False

    if "balanceCoins" not in account_data["clickerUser"]:
      log.error(f"[{self.account_name}] Invalid balance coins.")
      self.SendTelegramLog(
        f"[{self.account_name}] Invalid balance coins.", "other_errors"
      )
      return False

    self.account_data = account_data
    self.balanceCoins = account_data["clickerUser"]["balanceCoins"]
    self.availableTaps = account_data["clickerUser"]["availableTaps"]
    self.maxTaps = account_data["clickerUser"]["maxTaps"]
    self.earnPassivePerHour = account_data["clickerUser"]["earnPassivePerHour"]

    return account_data

  def BuyFreeTapBoostIfAvailable(self):
    log.info(f"[{self.account_name}] Checking for free tap boost...")

    BoostList = self.BoostsToBuyListRequest()
    if not (isinstance(BoostList, dict) and "boostsForBuy" in BoostList):
      log.error(f"[{self.account_name}] Failed to get boosts list.")
      log.error(f"[{self.account_name}] BoostList value: {BoostList} (type: {type(BoostList)})")
      self.SendTelegramLog(
        f"[{self.account_name}] Failed to get boosts list.", "other_errors"
      )
      return None

    BoostForTapList = None
    for boost in BoostList["boostsForBuy"]:
      if boost["price"] == 0 and boost["id"] == "BoostFullAvailableTaps":
        BoostForTapList = boost
        break

    if (
        BoostForTapList is not None
        and "price" in BoostForTapList
        and "cooldownSeconds" in BoostForTapList
        and BoostForTapList["price"] == 0
        and BoostForTapList["cooldownSeconds"] == 0
    ):
      log.info(f"[{self.account_name}] Free boost found, attempting to buy...")
      time.sleep(5)
      self.BuyBoostRequest(BoostForTapList["id"])
      log.info(f"[{self.account_name}] Free boost bought successfully")
      return True
    else:
      log.info(f"\033[1;34m[{self.account_name}] No free boosts available\033[0m")

    return False

  def MeTelegramRequest(self):
    url = "https://api.hamsterkombat.io/auth/me-telegram"
    headers = {
      "Access-Control-Request-Headers": "authorization",
      "Access-Control-Request-Method": "POST",
    }

    # Send OPTIONS request
    self.HttpRequest(url, headers, "OPTIONS", 204)

    headers = {
      "Authorization": self.Authorization,
    }

    # Send POST request
    return self.HttpRequest(url, headers, "POST", 200)

  def ListTasksRequest(self):
    url = "https://api.hamsterkombat.io/clicker/list-tasks"
    headers = {
      "Access-Control-Request-Headers": "authorization",
      "Access-Control-Request-Method": "POST",
    }

    # Send OPTIONS request
    self.HttpRequest(url, headers, "OPTIONS", 204)

    headers = {
      "Authorization": self.Authorization,
    }

    # Send POST request
    return self.HttpRequest(url, headers, "POST", 200)

  def GetListAirDropTasksRequest(self):
    url = "https://api.hamsterkombat.io/clicker/list-airdrop-tasks"
    headers = {
      "Access-Control-Request-Headers": "authorization",
      "Access-Control-Request-Method": "POST",
    }

    # Send OPTIONS request
    self.HttpRequest(url, headers, "OPTIONS", 204)

    headers = {
      "Authorization": self.Authorization,
    }

    # Send POST request
    return self.HttpRequest(url, headers, "POST", 200)

  def GetAccountConfigRequest(self):
    url = "https://api.hamsterkombat.io/clicker/config"
    headers = {
      "Access-Control-Request-Headers": "authorization",
      "Access-Control-Request-Method": "POST",
    }

    # Send OPTIONS request
    self.HttpRequest(url, headers, "OPTIONS", 204)

    headers = {
      "Authorization": self.Authorization,
    }

    # Send POST request
    return self.HttpRequest(url, headers, "POST", 200)

  def ClaimDailyCipherRequest(self, DailyCipher):
    url = "https://api.hamsterkombat.io/clicker/claim-daily-cipher"
    headers = {
      "Access-Control-Request-Headers": "authorization,content-type",
      "Access-Control-Request-Method": "POST",
    }

    # Send OPTIONS request
    self.HttpRequest(url, headers, "OPTIONS", 204)

    headers = {
      "Accept": "application/json",
      "Authorization": self.Authorization,
      "Content-Type": "application/json",
    }

    payload = json.dumps(
      {
        "cipher": DailyCipher,
      }
    )

    # Send POST request
    return self.HttpRequest(url, headers, "POST", 200, payload)

  def CheckTaskRequest(self, task_id):
    url = "https://api.hamsterkombat.io/clicker/check-task"
    headers = {
      "Access-Control-Request-Headers": "authorization,content-type",
      "Access-Control-Request-Method": "POST",
    }

    # Send OPTIONS request
    self.HttpRequest(url, headers, "OPTIONS", 204)

    headers = {
      "Accept": "application/json",
      "Authorization": self.Authorization,
      "Content-Type": "application/json",
    }

    payload = json.dumps(
      {
        "taskId": task_id,
      }
    )

    # Send POST request
    return self.HttpRequest(url, headers, "POST", 200, payload)

  def BuyBestCard(self):
    log.info(f"[{self.account_name}] Checking for best card...")
    time.sleep(2)
    upgradesResponse = self.UpgradesForBuyRequest()
    if not (isinstance(upgradesResponse, dict) and "upgradesForBuy" in upgradesResponse):
      log.error(f"[{self.account_name}] Failed to get upgrades list.")
      log.error(f"[{self.account_name}] tasksResponse value: {upgradesResponse} (type: {type(upgradesResponse)})")
      self.SendTelegramLog(
        f"[{self.account_name}] Failed to get upgrades list.", "other_errors"
      )
      return False

    upgrades = [
      item
      for item in upgradesResponse["upgradesForBuy"]
      if not item["isExpired"]
         and item["isAvailable"]
         and item["profitPerHourDelta"] > 0
    ]

    if len(upgrades) == 0:
      log.warning(f"[{self.account_name}] No upgrades available.")
      return False

    balanceCoins = int(self.balanceCoins)
    log.info(f"[{self.account_name}] Searching for the best upgrades...")

    selected_upgrades = SortUpgrades(
      upgrades, 999999999999
    )  # Set max budget to a high number
    if len(selected_upgrades) == 0:
      log.warning(f"[{self.account_name}] No upgrades available.")
      return False

    log.info(
      f"[{self.account_name}] Best upgrade is {selected_upgrades[0]['name']} with profit {selected_upgrades[0]['profitPerHourDelta']} and price {NumberToString(selected_upgrades[0]['price'])}, Level: {selected_upgrades[0]['level']}"
    )

    if balanceCoins < selected_upgrades[0]["price"]:
      log.warning(
        f"[{self.account_name}] Balance is too low to buy the best card."
      )

      self.SendTelegramLog(
        f"[{self.account_name}] Balance is too low to buy the best card, Best card: {selected_upgrades[0]['name']} with profit {selected_upgrades[0]['profitPerHourDelta']} and price {NumberToString(selected_upgrades[0]['price'])}, Level: {selected_upgrades[0]['level']}",
        "upgrades",
      )
      return False

    if (
        "cooldownSeconds" in selected_upgrades[0]
        and selected_upgrades[0]["cooldownSeconds"] > 0
    ):
      log.warning(f"[{self.account_name}] Best card is on cooldown...")
      if selected_upgrades[0]["cooldownSeconds"] > 300:
        self.SendTelegramLog(
          f"[{self.account_name}] Best card is on cooldown for more than 5 minutes, Best card: {selected_upgrades[0]['name']} with profit {selected_upgrades[0]['profitPerHourDelta']} and price {NumberToString(selected_upgrades[0]['price'])}, Level: {selected_upgrades[0]['level']}",
          "upgrades",
        )
        return False
      log.info(
        f"[{self.account_name}] Waiting for {selected_upgrades[0]['cooldownSeconds']} seconds, Cooldown will be completed in {selected_upgrades[0]['cooldownSeconds']} seconds..."
      )
      time.sleep(selected_upgrades[0]["cooldownSeconds"] + 1)

    log.info(f"[{self.account_name}] Attempting to buy the best card...")
    time.sleep(2)
    upgradesResponse = self.BuyUpgradeRequest(selected_upgrades[0]["id"])
    if upgradesResponse is None:
      log.error(f"[{self.account_name}] Failed to buy the best card.")
      self.SendTelegramLog(
        f"[{self.account_name}] Failed to buy the best card.", "other_errors"
      )
      return False

    log.info(f"[{self.account_name}] Best card bought successfully")
    time.sleep(3)
    balanceCoins -= selected_upgrades[0]["price"]
    self.balanceCoins = balanceCoins
    self.ProfitPerHour += selected_upgrades[0]["profitPerHourDelta"]
    self.SpendTokens += selected_upgrades[0]["price"]
    self.earnPassivePerHour += selected_upgrades[0]["profitPerHourDelta"]

    log.info(
      f"[{self.account_name}] Best card purchase completed successfully, Your profit per hour increased by {NumberToString(self.ProfitPerHour)} coins, Spend tokens: {NumberToString(self.SpendTokens)}"
    )

    self.SendTelegramLog(
      f"[{self.account_name}] Bought {selected_upgrades[0]['name']} with profit {selected_upgrades[0]['profitPerHourDelta']} and price {NumberToString(selected_upgrades[0]['price'])}, Level: {selected_upgrades[0]['level']}",
      "upgrades",
    )

    return True

  def Start(self):
    self.StartAccount()
    AccountBasicData = self.getBasicAccountData()
    if not AccountBasicData:
      self.HandleError("Unable to get account basic data.")
      return

    self.logAccountInfo(AccountBasicData)
    AccountConfigData = self.getAccountConfigData()
    if not AccountConfigData:
      self.HandleError("Unable to get account config data.")
      return

    DailyCipher = self.decode_daily_cipher(AccountConfigData)
    if not self.GetAccountDataStatus():
      return

    self.LogAccountBalance()
    upgradesResponse = self.GetUpgrades()
    if not upgradesResponse:
      self.HandleError("Failed to get upgrades list.")
      return

    tasksResponse = self.GetTasks()
    if not tasksResponse:
      self.HandleError("Failed to get tasks list.")
      return

    airdropTasksResponse = self.GetAirdropTasks()
    if not airdropTasksResponse:
      self.HandleError("Failed to get airdrop tasks list.")
      return

    self.AutoTap(DailyCipher, AccountConfigData)
    self.AutoGetDailyTask(tasksResponse)
    self.AutoGetTask(tasksResponse)
    self.AutoFreeTapBoost()
    self.SyncAccountData()
    self.AutoUpgrade()

  def StartAccount(self):
    log.info(f"[{self.account_name}] Starting account...")

  def getBasicAccountData(self):
    log.info(f"[{self.account_name}] Getting basic account data...")
    return self.MeTelegramRequest()

  def HandleError(self, message):
    log.error(f"[{self.account_name}] {message}")
    self.SendTelegramLog(f"[{self.account_name}] {message}", "other_errors")

  def logAccountInfo(self, AccountBasicData):
    log.info(
      f"\033[1;35m[{self.account_name}] Account ID: {AccountBasicData['telegramUser']['id']}, Account detected as bot: {AccountBasicData['telegramUser']['isBot']}\033[0m")
    self.SendTelegramLog(
      f"[{self.account_name}] Account ID: {AccountBasicData['telegramUser']['id']}, Account detected as bot: {AccountBasicData['telegramUser']['isBot']}",
      "account_info"
    )

  def getAccountConfigData(self):
    log.info(f"[{self.account_name}] Getting account config data...")
    return self.GetAccountConfigRequest()

  def decode_daily_cipher(self, AccountConfigData):
    DailyCipher = ""
    if (
        self.config["auto_get_daily_cipher"]
        and "dailyCipher" in AccountConfigData
        and "cipher" in AccountConfigData["dailyCipher"]
    ):
      log.info(f"[{self.account_name}] Decoding daily cipher...")
      DailyCipher = DailyCipherDecode(AccountConfigData["dailyCipher"]["cipher"])
      MorseCode = TextToMorseCode(DailyCipher)
      log.info(
        f"\033[1;34m[{self.account_name}] Daily cipher: {DailyCipher} and Morse code: {MorseCode}\033[0m"
      )
    return DailyCipher

  def GetAccountDataStatus(self):
    log.info(f"[{self.account_name}] Getting account data...")
    return self.getAccountData() is not False

  def LogAccountBalance(self):
    log.info(
      f"[{self.account_name}] Account Balance Coins: {NumberToString(self.balanceCoins)}, Available Taps: {self.availableTaps}, Max Taps: {self.maxTaps}"
    )

  def GetUpgrades(self):
    log.info(f"[{self.account_name}] Getting account upgrades...")
    return self.UpgradesForBuyRequest()

  def GetTasks(self):
    log.info(f"[{self.account_name}] Getting account tasks...")
    tasksResponse = self.ListTasksRequest()
    if not (isinstance(tasksResponse, dict) and "tasks" in tasksResponse):
      log.error(f"[{self.account_name}] tasksResponse value: {tasksResponse} (type: {type(tasksResponse)})")
      return None
    return tasksResponse

  def GetAirdropTasks(self):
    log.info(f"[{self.account_name}] Getting account airdrop tasks...")
    return self.GetListAirDropTasksRequest()

  def AutoTap(self, DailyCipher, AccountConfigData):
    if self.config["auto_tap"]:
      log.info(f"[{self.account_name}] Starting to tap...")
      time.sleep(2)
      self.TapRequest(self.availableTaps)
      log.info(f"[{self.account_name}] Tapping completed successfully.")

    if self.config["auto_get_daily_cipher"] and DailyCipher != "":
      if AccountConfigData["dailyCipher"]["isClaimed"]:
        log.info(
          f"\033[1;34m[{self.account_name}] Daily cipher already claimed.\033[0m"
        )
      else:
        log.info(f"[{self.account_name}] Attempting to claim daily cipher...")
        time.sleep(2)
        self.ClaimDailyCipherRequest(DailyCipher)
        log.info(f"[{self.account_name}] Daily cipher claimed successfully.")
        self.SendTelegramLog(
          f"[{self.account_name}] Daily cipher claimed successfully. Text was: {DailyCipher}, Morse code was: {TextToMorseCode(DailyCipher)}",
          "daily_cipher",
        )

  def AutoGetDailyTask(self, tasksResponse):
    if not self.config["auto_get_daily_task"]:
      return

    log.info(f"[{self.account_name}] Checking for daily task...")
    streak_days = next((task for task in tasksResponse["tasks"] if task["id"] == "streak_days"), None)
    if streak_days is None:
      log.error(f"[{self.account_name}] Failed to get daily task.")
      return

    if streak_days["isCompleted"]:
      log.info(
        f"\033[1;34m[{self.account_name}] Daily task already completed.\033[0m"
      )
    else:
      log.info(f"[{self.account_name}] Attempting to complete daily task...")
      day = streak_days["days"]
      rewardCoins = streak_days["rewardCoins"]
      time.sleep(2)
      self.CheckTaskRequest("streak_days")
      log.info(
        f"[{self.account_name}] Daily task completed successfully, Day: {day}, Reward coins: {NumberToString(rewardCoins)}"
      )
      self.SendTelegramLog(
        f"[{self.account_name}] Daily task completed successfully, Day: {day}, Reward coins: {NumberToString(rewardCoins)}",
        "daily_task",
      )

  def AutoGetTask(self, tasksResponse):
    if not self.config["auto_get_task"]:
      return

    log.info(f"[{self.account_name}] Checking for available task...")
    selected_task = None
    for task in tasksResponse["tasks"]:
      link = task.get("link", "")
      if not task["isCompleted"] and "https://" in link:
        log.info(
          f"[{self.account_name}] Attempting to complete Youtube Or Twitter task..."
        )
        selected_task = task["id"]
        rewardCoins = task["rewardCoins"]
        time.sleep(2)
        self.CheckTaskRequest(selected_task)
        log.info(
          f"[{self.account_name}] Task completed - id: {selected_task}, Reward coins: {NumberToString(rewardCoins)}"
        )
        self.SendTelegramLog(
          f"[{self.account_name}] Task completed - id: {selected_task}, Reward coins: {NumberToString(rewardCoins)}",
          "daily_task",
        )
      if selected_task is None:
        log.info(f"\033[1;34m[{self.account_name}] Tasks already done\033[0m")

  def AutoFreeTapBoost(self):
    if not (self.config["auto_tap"] and self.config["auto_free_tap_boost"] and self.BuyFreeTapBoostIfAvailable()):
      return

    log.info(f"[{self.account_name}] Starting to tap with free boost...")
    time.sleep(2)
    self.TapRequest(self.availableTaps)
    log.info(f"[{self.account_name}] Tapping with free boost completed successfully.")

  def SyncAccountData(self):
    if self.config["auto_tap"]:
      self.getAccountData()
      log.info(
        f"[{self.account_name}] Account Balance Coins: {NumberToString(self.balanceCoins)}, Available Taps: {self.availableTaps}, Max Taps: {self.maxTaps}"
      )

  def AutoUpgrade(self):
    if not self.config["auto_upgrade"]:
      log.error(f"[{self.account_name}] Auto upgrade is disabled.")
      return

    self.ProfitPerHour = 0
    self.SpendTokens = 0

    if self.config["wait_for_best_card"]:
      self.BuyBestCards()
      return

    if self.balanceCoins < self.config["auto_upgrade_start"]:
      log.warning(f"[{self.account_name}] Balance is too low to start buying upgrades.")
      return

    while self.balanceCoins >= self.config["auto_upgrade_min"]:
      log.info(f"[{self.account_name}] Checking for upgrades...")
      time.sleep(2)
      upgradesResponse = self.UpgradesForBuyRequest()
      if not (isinstance(upgradesResponse, dict) and "upgradesForBuy" in upgradesResponse):
        log.error(f"[{self.account_name}] Failed to get upgrades list.")
        log.error(f"[{self.account_name}] tasksResponse value: {upgradesResponse} (type: {type(upgradesResponse)})")
        self.SendTelegramLog(
          f"[{self.account_name}] Failed to get upgrades list.",
          "other_errors",
        )
        return

      upgrades = [
        item
        for item in upgradesResponse["upgradesForBuy"]
        if not item["isExpired"]
           and item["isAvailable"]
           and item["profitPerHourDelta"] > 0
           and ("cooldownSeconds" not in item or item["cooldownSeconds"] == 0)
      ]

      if len(upgrades) == 0:
        log.warning(f"[{self.account_name}] No upgrades available.")
        return

      balanceCoins = int(self.balanceCoins)
      log.info(f"[{self.account_name}] Searching for the best upgrades...")

      selected_upgrades = SortUpgrades(upgrades, balanceCoins)
      if len(selected_upgrades) == 0:
        log.warning(f"[{self.account_name}] No upgrades available.")
        return

      log.info(
        f"[{self.account_name}] Best upgrade is {selected_upgrades[0]['name']} with profit {selected_upgrades[0]['profitPerHourDelta']} and price {NumberToString(selected_upgrades[0]['price'])}, Level: {selected_upgrades[0]['level']}"
      )

      balanceCoins -= selected_upgrades[0]["price"]

      log.info(f"[{self.account_name}] Attempting to buy an upgrade...")
      time.sleep(2)
      upgradesResponse = self.BuyUpgradeRequest(selected_upgrades[0]["id"])
      if upgradesResponse is None:
        log.error(f"[{self.account_name}] Failed to buy an upgrade.")
        return

      log.info(f"[{self.account_name}] Upgrade bought successfully")
      self.SendTelegramLog(
        f"[{self.account_name}] Bought {selected_upgrades[0]['name']} with profit {selected_upgrades[0]['profitPerHourDelta']} and price {NumberToString(selected_upgrades[0]['price'])}, Level: {selected_upgrades[0]['level']}",
        "upgrades",
      )
      time.sleep(5)
      self.balanceCoins = balanceCoins
      self.ProfitPerHour += selected_upgrades[0]["profitPerHourDelta"]
      self.SpendTokens += selected_upgrades[0]["price"]
      self.earnPassivePerHour += selected_upgrades[0]["profitPerHourDelta"]

    log.info(f"[{self.account_name}] Upgrades purchase completed successfully.")
    self.getAccountData()
    log.info(
      f"[{self.account_name}] Final account balance: {NumberToString(self.balanceCoins)} coins, Your profit per hour is {NumberToString(self.earnPassivePerHour)} (+{NumberToString(self.ProfitPerHour)}), Spent: {NumberToString(self.SpendTokens)}"
    )
    self.SendTelegramLog(
      f"[{self.account_name}] Final account balance: {NumberToString(self.balanceCoins)} coins, Your profit per hour is {NumberToString(self.earnPassivePerHour)} (+{NumberToString(self.ProfitPerHour)}), Spent: {NumberToString(self.SpendTokens)}",
      "account_info",
    )

  def BuyBestCards(self):
    while True:
      if not self.BuyBestCard():
        break

    self.getAccountData()
    log.info(
      f"[{self.account_name}] Final account balance: {NumberToString(self.balanceCoins)} coins, Your profit per hour is {NumberToString(self.earnPassivePerHour)} (+{NumberToString(self.ProfitPerHour)}), Spent: {NumberToString(self.SpendTokens)}"
    )
    self.SendTelegramLog(
      f"[{self.account_name}] Final account balance: {NumberToString(self.balanceCoins)} coins, Your profit per hour is {NumberToString(self.earnPassivePerHour)} (+{NumberToString(self.ProfitPerHour)}), Spent: {NumberToString(self.SpendTokens)}",
      "upgrades",
    )

async def StartAccount(account):
  account.Start()

async def RunAccounts():
  accounts = [HamsterKombatAccount(account) for account in AccountList]

  for account in accounts:
    account.SendTelegramLog(
      f"[{account.account_name}] Hamster Kombat Auto farming bot started successfully.",
      "general_info"
    )

  while True:
    log.info("\033[1;33mStarting all accounts...\033[0m")

    # Start all accounts asynchronously
    await asyncio.gather(*[StartAccount(account) for account in accounts])

    if AccountsRecheckTime < 1 and MaxRandomDelay < 1:
      log.error("AccountsRecheckTime and MaxRandomDelay values are set to 0, bot will close now.")
      return

    if MaxRandomDelay > 0:
      randomDelay = random.randint(1, MaxRandomDelay)
      log.error(f"Sleeping for {randomDelay} seconds because of random delay...")
      await asyncio.sleep(randomDelay)

    if AccountsRecheckTime > 0:
      log.error(f"Rechecking all accounts in {AccountsRecheckTime} seconds...")
      await asyncio.sleep(AccountsRecheckTime)


def WelcomeMessage() -> None:
  log.info("------------------------------------------------------------------------")
  log.info("------------------------------------------------------------------------")
  log.info("\033[1;32mWelcome to [Master Hamster Kombat] Auto farming bot...\033[0m")
  log.info("\033[1;34mProject Github: https://github.com/masterking32/MasterHamsterKombatBot\033[0m")
  log.info("\033[1;33mDeveloped by: MasterkinG32\033[0m")
  log.info("\033[1;35mVersion: 2.0\033[0m")
  log.info("\033[1;36mTo stop the bot, press Ctrl + C\033[0m")
  log.info("------------------------------------------------------------------------")
  log.info("------------------------------------------------------------------------")


def main():
  WelcomeMessage()
  time.sleep(2)
  try:
    asyncio.run(RunAccounts())
  except KeyboardInterrupt:
    log.error("Stopping Master Hamster Kombat Auto farming bot...")


if __name__ == "__main__":
  main()
