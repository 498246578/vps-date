import json
import os
import logging
from datetime import datetime
import requests
from vps_manager import VPSManager, parse_expire_datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='vps_monitor.log'
)

def check_vps_expiry():
    """检查VPS到期情况并发送通知"""
    try:
        manager = VPSManager()
        expiring_vps = []
        monthly_vps = []
        ssl_expiring = []
        now = datetime.now()

        # 检查所有VPS
        for vps in manager.vps_data:
            if 'expireDate' in vps:
                expire_date = parse_expire_datetime(vps['expireDate'])
                days_left = (expire_date - now).days
                if 0 < days_left <= 3:
                    expiring_vps.append(f"• {vps['name']}: {days_left}天后到期 ({vps['expireDate']})")
            elif 'monthlyExpireDay' in vps:
                expire_day = vps['monthlyExpireDay']
                if now.day > expire_day:
                    if now.month == 12:
                        next_pay_date = datetime(now.year + 1, 1, expire_day)
                    else:
                        next_pay_date = datetime(now.year, now.month + 1, expire_day)
                else:
                    next_pay_date = datetime(now.year, now.month, expire_day)

                days_until_expire = (next_pay_date - now).days
                if 0 <= days_until_expire <= 3:
                    monthly_vps.append(f"• {vps['name']}: {days_until_expire}天后续费 ({next_pay_date.strftime('%Y-%m-%d')})")

            if vps.get('sslExpireDate'):
                try:
                    ssl_date = parse_expire_datetime(vps['sslExpireDate'])
                    ssl_days_left = (ssl_date - now).days
                    if 0 <= ssl_days_left <= 30:
                        ssl_expiring.append(f"• {vps['name']}: SSL证书还有{ssl_days_left}天到期 ({vps['sslExpireDate']})")
                except Exception as e:
                    logging.warning(f"SSL到期时间解析失败: {vps['name']} - {e}")

        # 如果有即将到期的VPS或SSL证书，发送通知
        if expiring_vps or monthly_vps or ssl_expiring:
            message = "⚠️ 到期提醒\n"

            if expiring_vps or monthly_vps:
                message += "\n🖥 VPS到期提醒\n"
                if expiring_vps:
                    message += "\n" + "\n".join(expiring_vps)
                if monthly_vps:
                    if expiring_vps:
                        message += "\n"
                    message += "\n" + "\n".join(monthly_vps)

            if ssl_expiring:
                message += "\n🔐 SSL证书到期提醒\n"
                message += "\n" + "\n".join(ssl_expiring)

            # 发送Telegram通知
            if manager.notification.config['telegram']['enabled']:
                manager.notification.send_telegram(message)
                print("已发送到期提醒通知")
                logging.info("已发送到期提醒通知")
        else:
            print("没有即将到期的VPS或SSL证书")
            logging.info("没有即将到期的VPS或SSL证书")

    except Exception as e:
        error_msg = f"检查过程出错: {str(e)}"
        print(error_msg)
        logging.error(error_msg)

if __name__ == "__main__":
    check_vps_expiry() 