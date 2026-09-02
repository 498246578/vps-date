import json
import os
import requests
import hmac
import hashlib
import base64
import urllib.parse
import time
import calendar
from datetime import datetime

def parse_expire_datetime(value):
    """兼容 YYYY-MM-DD 和 YYYY-MM-DDTHH:MM:SS / YYYY-MM-DD HH:MM:SS"""
    if not value:
        return None
    value = value.strip().replace('T', ' ')
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"无法识别的到期时间: {value}")


class NotificationManager:
    def __init__(self):
        self.config_file = 'config.json'
        self.config = self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_file):
            default_config = {
                "telegram": {"enabled": False, "bot_token": "", "chat_id": ""}
            }
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
            return default_config
        
        with open(self.config_file, 'r') as f:
            return json.load(f)

    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)

    def setup_telegram(self):
        print("\n=== Telegram配置 ===")
        enabled = input("启用Telegram通知? (y/n): ").lower() == 'y'
        self.config['telegram']['enabled'] = enabled
        
        if enabled:
            self.config['telegram']['bot_token'] = input("Bot Token: ")
            self.config['telegram']['chat_id'] = input("Chat ID: ")
        self.save_config()
        print("Telegram配置已保存！")

    def send_telegram(self, message):
        """发送Telegram通知"""
        try:
            if not self.config['telegram']['enabled']:
                return
                
            bot_token = self.config['telegram']['bot_token']
            chat_id = self.config['telegram']['chat_id']
            
            # 添加详情链接到消息末尾
            base_url = self.config.get('web_dashboard_url', 'https://woniu336.github.io/vps-date')
            message += f"\n\n👉 查看详情：{base_url}"
            
            # 发送消息到Telegram
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, json=data)
            response.raise_for_status()
            
        except Exception as e:
            print(f"发送Telegram通知失败: {str(e)}")

class VPSManager:
    def __init__(self):
        self.vps_file = 'index.html'
        self.vps_data = self.load_vps_data()
        self.currencies = ['USD', 'EUR', 'CNY', 'CAD']
        self.exchange_rates = {}  # 添加汇率存储
        self.notification = NotificationManager()

    def load_vps_data(self):
        try:
            with open(self.vps_file, 'r', encoding='utf-8') as f:
                content = f.read()
                start = content.find('const vpsServices = [')
                end = content.find('];', start) + 1
                vps_str = content[start:end].replace('const vpsServices = ', '')
                return json.loads(vps_str)
        except Exception as e:
            print(f"Load data failed: {e}")
            return []

    def save_vps_data(self):
        try:
            with open(self.vps_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            start = content.find('const vpsServices = [')
            end = content.find('];', start) + 1
            new_content = (
                content[:start] + 
                'const vpsServices = ' + 
                json.dumps(self.vps_data, ensure_ascii=False, indent=4) +
                content[end:]
            )
            
            with open(self.vps_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print("\n保存成功！")
            
            # 添加变更通知
            message = "VPS信息已更新\n"
            message += f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            message += f"当前监控: {len(self.vps_data)}台服务器"
            self.send_notification(message)
            
        except Exception as e:
            print(f"\n保存失败: {e}")

    def list_vps(self):
        print("\nVPS列表:")
        print("-" * 60)
        for i, vps in enumerate(self.vps_data, 1):
            cycle_label = '年' if vps.get('billingCycle') == 'year' else '月'
            if 'expireDate' in vps:
                expire_info = vps['expireDate']
            elif 'monthlyExpireDay' in vps:
                expire_info = f"每月{vps['monthlyExpireDay']}号"
            else:
                expire_info = "未设置"
            print(f"{i}. {vps['name']} - {vps['cost']} {vps['currency']}/{cycle_label} - 到期: {expire_info}")
        print("-" * 60)

    def edit_vps(self):
        self.list_vps()
        try:
            idx = int(input("\n请输入要修改的序号: ")) - 1
            if not (0 <= idx < len(self.vps_data)):
                print("无效的序号！")
                return

            vps = self.vps_data[idx]
            print(f"\n正在修改: {vps['name']}")
            print("\n直接回车保持原值")

            changes = {}

            name = input(f"Name ({vps['name']}): ")
            if name:
                changes['name'] = name.strip()

            cost_str = input(f"费用 ({vps['cost']}): ")
            if cost_str:
                try:
                    changes['cost'] = float(cost_str)
                except ValueError:
                    print("费用格式无效，保持原值")

            print("\n可选币种:", end='')
            for i, curr in enumerate(self.currencies, 1):
                print(f" {i}.{curr}", end='')
            print('')
            curr_input = input(f"\n请选择币种 (当前: {vps['currency']}): ")
            if curr_input:
                try:
                    curr_idx = int(curr_input) - 1
                    if 0 <= curr_idx < len(self.currencies):
                        changes['currency'] = self.currencies[curr_idx]
                except ValueError:
                    print("币种选择无效，保持原值")

            current_cycle = vps.get('billingCycle', 'month')
            cycle_input = input(f"计费周期 (当前: {current_cycle}) [month/year]: ").strip().lower()
            if cycle_input in ('month', 'm'):
                changes['billingCycle'] = 'month'
            elif cycle_input in ('year', 'y'):
                changes['billingCycle'] = 'year'
            elif cycle_input:
                print("无效的计费周期，保持原值")
            new_cycle = changes.get('billingCycle', current_cycle)

            if new_cycle == 'year':
                current_expire = vps.get('expireDate', '')
                date = input(f"到期时间 (当前: {current_expire}) [YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS]: ")
                if date:
                    try:
                        dt = parse_expire_datetime(date)
                        if dt.hour or dt.minute or dt.second:
                            changes['expireDate'] = dt.strftime('%Y-%m-%dT%H:%M:%S')
                        else:
                            changes['expireDate'] = dt.strftime('%Y-%m-%d')
                    except ValueError as ve:
                        print(f"Invalid date format: {ve}")
            else:
                current_day = vps.get('monthlyExpireDay', '')
                day_str = input(f"每月续费日 (当前: {current_day}): ")
                if day_str:
                    try:
                        day = int(day_str)
                        if 1 <= day <= 31:
                            changes['monthlyExpireDay'] = day
                        else:
                            print("Day must be between 1-31")
                    except ValueError:
                        print("Invalid day format")

                current_time = vps.get('expireTime', '')
                time_input = input(f"到期时间 (当前: {current_time}) [HH:MM:SS, 可空]: ").strip()
                if time_input:
                    changes['expireTime'] = time_input

            current_ssl = vps.get('sslExpireDate', '')
            ssl_input = input(f"SSL证书到期时间 (当前: {current_ssl}) [可空]: ").strip()
            if ssl_input:
                changes['sslExpireDate'] = ssl_input

            current_note = vps.get('note', '')
            note_input = input(f"备注 (当前: {current_note}) [可空]: ").strip()
            if note_input:
                changes['note'] = note_input

            url = input(f"URL ({vps['url']}): ")
            if url:
                changes['url'] = url

            if changes:
                new_vps = vps.copy()
                new_vps.update(changes)
                self.vps_data[idx] = new_vps
                self.save_vps_data()
                print("\nUpdated successfully!")
            else:
                print("\nNo changes made")

        except Exception as e:
            print(f"\nEdit failed: {str(e)}")

    def add_vps(self):
        try:
            print("\n添加新VPS")
            name = input("Name: ")  # 使用英文提示VPS名称
            if not name:
                print("名称不能为空！")
                return

            try:
                cost = float(input("费用: "))
            except ValueError:
                print("费用格式无效！")
                return

            # Currency selection
            print("\n可选币种:", end='')
            for i, curr in enumerate(self.currencies, 1):
                print(f" {i}.{curr}", end='')
            print('')

            try:
                curr_idx = int(input("\n请选择币种: ")) - 1
                if not (0 <= curr_idx < len(self.currencies)):
                    print("无效的币种选择！")
                    return
                currency = self.currencies[curr_idx]
            except ValueError:
                print("选择无效！")
                return

            # Billing cycle
            cycle = input("\n计费周期 (1:月付 2:年付) [1]: ").strip() or '1'
            billing_cycle = 'year' if cycle == '2' else 'month'

            expire_info = {'billingCycle': billing_cycle}
            if billing_cycle == 'year':
                date = input("到期时间 (YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS): ")
                try:
                    dt = parse_expire_datetime(date)
                    if dt.hour or dt.minute or dt.second:
                        expire_info['expireDate'] = dt.strftime('%Y-%m-%dT%H:%M:%S')
                    else:
                        expire_info['expireDate'] = dt.strftime('%Y-%m-%d')
                except ValueError as ve:
                    print(f"Invalid date format: {ve}")
                    return
            else:
                try:
                    day = int(input("每月续费日 (1-31): "))
                    if not (1 <= day <= 31):
                        print("Day must be between 1-31!")
                        return
                    expire_info['monthlyExpireDay'] = day
                except ValueError:
                    print("Invalid day format!")
                    return
                expire_time = input("到期时间 (HH:MM:SS, 可空): ").strip()
                if expire_time:
                    expire_info['expireTime'] = expire_time

            ssl_expire = input("SSL证书到期时间 (可空): ").strip()
            note = input("备注 (可空): ").strip()
            url = input("Management URL: ")

            new_vps = {
                'name': name,
                'cost': cost,
                'currency': currency,
                'url': url,
                **expire_info
            }
            if ssl_expire:
                new_vps['sslExpireDate'] = ssl_expire
            if note:
                new_vps['note'] = note

            self.vps_data.append(new_vps)
            self.save_vps_data()
            print("\nAdded successfully!")

        except Exception as e:
            print(f"\nAdd failed: {str(e)}")

    def delete_vps(self):
        self.list_vps()
        try:
            idx = int(input("\n请输入要删除的序号: ")) - 1
            if 0 <= idx < len(self.vps_data):
                vps = self.vps_data.pop(idx)
                print(f"\n已删除: {vps['name']}")
                self.save_vps_data()
            else:
                print("无效的序号！")
        except Exception as e:
            print(f"\n删除失败: {str(e)}")

    @staticmethod
    def add_billing_cycle(expire_date, billing_cycle):
        """在保留时间的前提下增加一个月或一年，并兼容月底日期。"""
        if billing_cycle == 'year':
            year = expire_date.year + 1
            day = min(expire_date.day, calendar.monthrange(year, expire_date.month)[1])
            return expire_date.replace(year=year, day=day)

        month_index = expire_date.year * 12 + expire_date.month
        year, zero_based_month = divmod(month_index, 12)
        month = zero_based_month + 1
        day = min(expire_date.day, calendar.monthrange(year, month)[1])
        return expire_date.replace(year=year, month=month, day=day)

    def renew_vps(self):
        """将选中服务器的明确到期时间顺延一个计费周期。"""
        self.list_vps()
        try:
            idx = int(input("\n请输入要续费的序号: ")) - 1
            if not (0 <= idx < len(self.vps_data)):
                print("无效的序号！")
                return

            vps = self.vps_data[idx]
            billing_cycle = vps.get('billingCycle', 'month')
            current_expire = vps.get('expireDate')

            if current_expire:
                expire_date = parse_expire_datetime(current_expire)
            elif billing_cycle == 'month' and vps.get('monthlyExpireDay'):
                now = datetime.now()
                day = min(vps['monthlyExpireDay'], calendar.monthrange(now.year, now.month)[1])
                hour, minute, second = 0, 0, 0
                if vps.get('expireTime'):
                    try:
                        hour, minute, second = map(int, vps['expireTime'].split(':'))
                    except (TypeError, ValueError):
                        print("到期时间格式无效，应为 HH:MM:SS")
                        return
                expire_date = datetime(now.year, now.month, day, hour, minute, second)
                if expire_date < now:
                    expire_date = self.add_billing_cycle(expire_date, 'month')
            else:
                print("该服务器没有可用于续费的到期时间，请先通过“修改VPS”设置。")
                return

            renewed_date = self.add_billing_cycle(expire_date, billing_cycle)
            cycle_label = '一年' if billing_cycle == 'year' else '一个月'
            print(f"\n{vps['name']}: {expire_date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"续费{cycle_label}后: {renewed_date.strftime('%Y-%m-%d %H:%M:%S')}")
            if input("确认续费？[y/N]: ").strip().lower() not in ('y', 'yes'):
                print("已取消续费。")
                return

            vps['expireDate'] = renewed_date.strftime('%Y-%m-%dT%H:%M:%S')
            if billing_cycle == 'month':
                vps['monthlyExpireDay'] = renewed_date.day
                vps['expireTime'] = renewed_date.strftime('%H:%M:%S')
            self.save_vps_data()
            print(f"\n续费成功：{vps['name']} → {vps['expireDate']}")
        except ValueError as e:
            print(f"\n续费失败: {e}")

    def push_to_github(self):
        try:
            os.system('git add .')
            os.system(f'git commit -m "Update VPS data: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"')
            os.system('git push')
            print("\n推送成功！")
        except Exception as e:
            print(f"\n推送失败: {str(e)}")

    def notification_menu(self):
        while True:
            print("\n=== 通知设置 ===")
            print("1. 配置Telegram通知")
            print("2. 发送测试通知")
            print("0. 返回主菜单")
            
            choice = input("\n请选择操作: ")
            
            if choice == '1':
                self.notification.setup_telegram()
            elif choice == '2':
                self.send_test_notification()
            elif choice == '0':
                break
            else:
                print("无效的选择！")

    def send_test_notification(self):
        message = "VPS监控系统通知\n"
        message += f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        message += f"监控服务器数量: {len(self.vps_data)} 台"
        
        results = []
        if self.notification.config['telegram']['enabled']:
            self.notification.send_telegram(message)
            results.append("Telegram: 已发送")
        
        if not results:
            print("未启用任何通知方式！")
        else:
            print("\n".join(results))

    def check_expiring_vps(self):
        """检查即将到期的VPS"""
        expiring_vps = []
        for vps in self.vps_data:
            if 'expireDate' in vps:
                expire_date = parse_expire_datetime(vps['expireDate'])
                days_left = (expire_date - datetime.now()).days
                if 0 < days_left <= 3:
                    expiring_vps.append(f"{vps['name']}: 还有{days_left}天到期")
            elif 'monthlyExpireDay' in vps:
                today = datetime.now()
                expire_day = vps['monthlyExpireDay']
                next_expire = datetime(today.year, today.month, expire_day)
                if today.day > expire_day:
                    if today.month == 12:
                        next_expire = datetime(today.year + 1, 1, expire_day)
                    else:
                        next_expire = datetime(today.year, today.month + 1, expire_day)
                days_left = (next_expire - today).days
                if 0 < days_left <= 3:
                    expiring_vps.append(f"{vps['name']}: 还有{days_left}天到期")

        if expiring_vps:
            message = "VPS到期提醒\n"
            message += f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            message += "\n".join(expiring_vps)
            self.send_notification(message)

    def send_notification(self, message):
        """统一的通知发送函数"""
        if self.notification.config['telegram']['enabled']:
            self.notification.send_telegram(message)

    def update_exchange_rates(self):
        """更新汇率信息"""
        try:
            print("\n正在更新汇率...")
            # 使用免费的汇率API
            base_currency = 'USD'  # 使用美元作为基准货币
            api_url = f"https://api.exchangerate-api.com/v4/latest/{base_currency}"
            
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()
            
            # 更新汇率数据
            self.exchange_rates = {
                'USD': data['rates']['CNY'],  # 转换为人民币汇率
                'EUR': data['rates']['CNY'] / data['rates']['EUR'],
                'CNY': 1.0,  # 基准货币
                'CAD': data['rates']['CNY'] / data['rates']['CAD']
            }
            
            # 保存汇率到JS文件
            js_content = f"""const exchangeRates = {json.dumps(self.exchange_rates, indent=4)};"""
            with open('exchange_rates.js', 'w', encoding='utf-8') as f:
                f.write(js_content)
            
            # 显示更新后的汇率
            print("\n当前汇率（相对于CNY）：")
            for currency, rate in self.exchange_rates.items():
                print(f"{currency}: {rate:.4f}")
            
            # 发送通知
            message = "💱 汇率更新通知\n\n"
            message += "当前汇率（相对于CNY）：\n"
            for currency, rate in self.exchange_rates.items():
                message += f"{currency}: {rate:.4f}\n"
            self.send_notification(message)
            
            print("\n汇率更新成功！")
            return True
            
        except Exception as e:
            error_msg = f"更新汇率失败: {str(e)}"
            print(error_msg)
            return False

    def show_menu(self):
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            print("\n=== VPS到期监控 ===")
            print()
            print("1. 查看VPS列表")
            print("2. 添加VPS")
            print("3. 删除VPS")
            print("4. 修改VPS")
            print("5. 推送到GitHub")
            print("6. 通知设置")
            print("7. 更新汇率")
            print("8. 续费一个周期")
            print("0. 退出")
            print()
            print("=" * 20)
            
            choice = input("\n请选择操作: ").strip()
            
            if choice == '1':
                self.list_vps()
            elif choice == '2':
                self.add_vps()
            elif choice == '3':
                self.delete_vps()
            elif choice == '4':
                self.edit_vps()
            elif choice == '5':
                self.push_to_github()
            elif choice == '6':
                self.notification_menu()
            elif choice == '7':
                self.update_exchange_rates()
            elif choice == '8':
                self.renew_vps()
            elif choice == '0':
                break
            else:
                print("无效的选择！")
            
            if choice != '0':
                input("\n按回车键继续...")

if __name__ == "__main__":
    try:
        manager = VPSManager()
        manager.show_menu()
    except Exception as e:
        print(f"\n程序出错: {e}")
        input("\n按回车键退出...")  # 只在出错时提示按键退出
