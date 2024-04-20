import datetime
import logging
import sys
import time
import random
import config
import login
import process
import privateCrypt

DATE_FORMAT = "%m/%d/%Y %H:%M:%S %p"
TODAY = datetime.date.today().strftime("%Y%m%d")
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s  %(filename)s : %(levelname)s  %(message)s',  # 定义输出log的格式
                    stream=sys.stdout,
                    datefmt=DATE_FORMAT)

print(r'''
**************************************
    欢迎使用i茅台自动预约工具
**************************************
''')

#时间判断，如果当前时间在9:00-10:00时间段内，则执行预约程序，否则判断时间是否在7:00-9:00时间段，如果在，则等待到9点05分再执行预约程序，否则退出程序
now = datetime.datetime.now()
if now.hour >= 9 and now.hour < 10:
    logging.info("当前时间为9:00-10:00，开始执行预约程序")
elif now.hour >= 7 and now.hour < 9:
    logging.info("当前时间为7:00-9:00，等待9点05分后开始执行预约程序")
    #计算等待时间
    wait_time = datetime.datetime.combine(datetime.date.today(), datetime.time(hour=9, minute=5)) - now
    logging.info(f"等待时间：{wait_time.seconds}秒")
    time.sleep(wait_time.seconds)
else:
    logging.info("当前时间不在预约时间段内，退出程序")
    sys.exit(0)

# 获取当前会话ID的方法
process.get_current_session_id()

# 校验配置文件是否存在
configs = login.config
if len(configs.sections()) == 0:
    logging.error("配置文件未找到配置")
    sys.exit(1)

aes_key = privateCrypt.get_aes_key()

s_title = '茅台预约成功'
s_content = ""

for section in configs.sections():
    if (configs.get(section, 'enddate') != 9) and (TODAY > configs.get(section, 'enddate')):
        continue
    mobile = privateCrypt.decrypt_aes_ecb(section, aes_key)
    province = configs.get(section, 'province')
    city = configs.get(section, 'city')
    token = configs.get(section, 'token')
    userId = privateCrypt.decrypt_aes_ecb(configs.get(section, 'userid'), aes_key)
    lat = configs.get(section, 'lat')
    lng = configs.get(section, 'lng')

    p_c_map, source_data = process.get_map(lat=lat, lng=lng)

    process.UserId = userId
    process.TOKEN = token
    process.init_headers(user_id=userId, token=token, lng=lng, lat=lat)
    # 根据配置中，要预约的商品ID，城市 进行自动预约
    try:
        for item in config.ITEM_CODES:
            max_shop_id = process.get_location_count(province=province,
                                                     city=city,
                                                     item_code=item,
                                                     p_c_map=p_c_map,
                                                     source_data=source_data,
                                                     lat=lat,
                                                     lng=lng)
            # print(f'max shop id : {max_shop_id}')
            if max_shop_id == '0':
                continue
            shop_info = source_data.get(str(max_shop_id))
            title = config.ITEM_MAP.get(item)
            shopInfo = f'商品:{title};门店:{shop_info["name"]}'
            logging.info(shopInfo)
            reservation_params = process.act_params(max_shop_id, item)
            # 核心预约步骤
            r_success, r_content = process.reservation(reservation_params, mobile)
            # 为了防止漏掉推送异常，所有只要有一个异常，标题就显示失败
            if not r_success:
                s_title = '！！失败！！茅台预约'
            s_content = s_content + r_content + shopInfo + "\n"
            # 领取小茅运和耐力值
            process.getUserEnergyAward(mobile)
    except BaseException as e:
        print(e)
        logging.error(e)

# 推送消息
process.send_msg(s_title, s_content)
