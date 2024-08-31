from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import requests
import json

class Crawler:

    def __init__(self):
        self.target_url = "https://ana-blue-hangar-tour.resv.jp/reserve/calendar.php?x=1725019750"
        self.target_XFullpaths = [
            ("/html/body/div/div[3]/div[3]/div[3]/div[2]/table/tbody/tr[3]/td[3]", "9/6"),
            ("/html/body/div/div[3]/div[3]/div[3]/div[2]/table/tbody/tr[2]/td[7]", "9/7"),
            ("/html/body/div/div[3]/div[3]/div[3]/div[2]/table/tbody/tr[2]/td[6]", "9/10")
        ]  # 複数のXPathを日付情報とともにリストに追加
        self.available_slots = {}
        self.webhook_url = "https://hooks.slack.com/services/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"  # ここにSlackのWebhook URLを設定
        self.last_notification_time = time.time()  # 最後の動作確認通知の時間を記録

        # ヘッドレスモードのChromeブラウザを設定
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        self.driver = webdriver.Chrome(options=chrome_options)

    def execute_crawl(self):
        while True:
            print("実行中...")
            self.driver.get(self.target_url)
            
            for xpath, date in self.target_XFullpaths:
                try:
                    # 明示的な待機を追加して、指定したXPathの要素が現れるまで待機する
                    target_element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )
                    print(f"Processing slots for {date} (XPath: {xpath})")
                    
                    # 残枠情報を含む要素を解析
                    self.check_slots(target_element, date)
                    
                except Exception as e:
                    print(f"Failed to find element for XPath {xpath}: {e}")

            # 残枠情報を表示し、Slackに通知
            self.display_and_notify_available_slots()

            # 40分ごとに動作確認メッセージを送信
            if time.time() - self.last_notification_time >= 40 * 60:
                self.send_operation_check_notification()
                self.last_notification_time = time.time()

            # 10秒おきに繰り返す
            time.sleep(60)

    def check_slots(self, element, date):
        # target_elementの子要素から残枠情報を取得
        time_elements = element.find_elements(By.CLASS_NAME, "data-month")
        print(f"Time elements found for {date}: {len(time_elements)}")

        for time_element in time_elements:
            zannsu_element = time_element.find_element(By.CLASS_NAME, "zannsu")
            if zannsu_element:
                time_range = time_element.find_element(By.CLASS_NAME, "data-month-block").text.split()[-1]
                remaining_slots = zannsu_element.text.strip()
                if remaining_slots.isdigit() and int(remaining_slots) > 0:
                    self.add_available_slot(date, time_range, remaining_slots)

    def add_available_slot(self, date, time_range, remaining_slots):
        if date not in self.available_slots:
            self.available_slots[date] = {}
        self.available_slots[date][time_range] = remaining_slots

    def display_and_notify_available_slots(self):
        if self.available_slots:
            message = "[残枠情報]\n 残枠があります\n\n"
            for date, slots in self.available_slots.items():
                for time_range, remaining_slots in slots.items():
                    message += f"日付：{date}\n時間帯：{time_range}\n残枠：{remaining_slots}\n\n"

            print(message)
            self.send_slack_notification(message)
        else:
            print("\n[残枠情報]\n 残枠はありません\n")

    def send_slack_notification(self, message):
        payload = {
            "text": f"@channel\n{message}",
            "link_names": 1
        }
        response = requests.post(self.webhook_url, data=json.dumps(payload),
                                 headers={'Content-Type': 'application/json'})
        if response.status_code != 200:
            print(f"Failed to send notification: {response.status_code}, {response.text}")

    def send_operation_check_notification(self):
        message = "[動作確認]\n 現在のすべての要素を表示します。\n\n"
        for date, slots in self.available_slots.items():
            for time_range, remaining_slots in slots.items():
                message += f"日付：{date}\n時間帯：{time_range}\n残枠：{remaining_slots}\n\n"

        if not self.available_slots:
            message += "残枠はありません\n\n"

        print(message)
        self.send_slack_notification(message)

    def close(self):
        self.driver.quit()

if __name__ == "__main__":
    crawler = Crawler()
    crawler.execute_crawl()
    crawler.close()
