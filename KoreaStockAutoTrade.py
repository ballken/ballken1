import requests
import json
import datetime
import time
import yaml

with open('config.yaml', encoding='UTF-8') as f:
    _cfg = yaml.load(f, Loader=yaml.FullLoader)
APP_KEY = _cfg['APP_KEY']
APP_SECRET = _cfg['APP_SECRET']
ACCESS_TOKEN = ""
CANO = _cfg['CANO']
ACNT_PRDT_CD = _cfg['ACNT_PRDT_CD']
DISCORD_WEBHOOK_URL = _cfg['DISCORD_WEBHOOK_URL']
URL_BASE = _cfg['URL_BASE']

def send_message(msg):
    """디스코드 메세지 전송"""
    now = datetime.datetime.now()
    message = {"content": f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {str(msg)}"}
    requests.post(DISCORD_WEBHOOK_URL, data=message)
    print(message)

def get_access_token():
    """토큰 발급"""
    headers = {"content-type":"application/json"}
    body = {"grant_type":"client_credentials",
    "appkey":APP_KEY, 
    "appsecret":APP_SECRET}
    PATH = "oauth2/tokenP"
    URL = f"{URL_BASE}/{PATH}"
    res = requests.post(URL, headers=headers, data=json.dumps(body))
    ACCESS_TOKEN = res.json()["access_token"]
    return ACCESS_TOKEN
    
def hashkey(datas):
    """암호화"""
    PATH = "uapi/hashkey"
    URL = f"{URL_BASE}/{PATH}"
    headers = {
    'content-Type' : 'application/json',
    'appKey' : APP_KEY,
    'appSecret' : APP_SECRET,
    }
    res = requests.post(URL, headers=headers, data=json.dumps(datas))
    hashkey = res.json()["HASH"]
    return hashkey

def get_current_price(code="005930"):
    """현재가 조회"""
    PATH = "uapi/domestic-stock/v1/quotations/inquire-price"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json", 
            "authorization": f"Bearer {ACCESS_TOKEN}",
            "appKey":APP_KEY,
            "appSecret":APP_SECRET,
            "tr_id":"FHKST01010100"}
    params = {
    "fid_cond_mrkt_div_code":"J",
    "fid_input_iscd":code,
    }
    res = requests.get(URL, headers=headers, params=params)
    return int(res.json()['output']['stck_prpr'])

def get_target_price(code="005930"):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    PATH = "uapi/domestic-stock/v1/quotations/inquire-daily-price"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json", 
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"FHKST01010400"}
    params = {
    "fid_cond_mrkt_div_code":"J",
    "fid_input_iscd":code,
    "fid_org_adj_prc":"1",
    "fid_period_div_code":"D"
    }
    res = requests.get(URL, headers=headers, params=params)
    stck_oprc = int(res.json()['output'][0]['stck_oprc']) #오늘 시가
    stck_hgpr = int(res.json()['output'][1]['stck_hgpr']) #전일 고가
    stck_lwpr = int(res.json()['output'][1]['stck_lwpr']) #전일 저가
    target_price = stck_oprc + (stck_hgpr - stck_lwpr) * 0.45
    return target_price

def get_stock_balance():
    """주식 잔고조회"""
    PATH = "uapi/domestic-stock/v1/trading/inquire-balance"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json", 
        "authorization":f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"TTTC8434R",
        "custtype":"P",
    }
    params = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "01",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": ""
    }
    res = requests.get(URL, headers=headers, params=params)
    stock_list = res.json()['output1']
    evaluation = res.json()['output2']
    stock_dict = {}
    send_message(f"====주식 보유잔고====")
    for stock in stock_list:
        if int(stock['hldg_qty']) > 0:
            stock_dict[stock['pdno']] = stock['hldg_qty']
            send_message(f"{stock['prdt_name']}({stock['pdno']}): {stock['hldg_qty']}주")
            time.sleep(0.1)
    send_message(f"주식 평가 금액: {evaluation[0]['scts_evlu_amt']}원")
    time.sleep(0.1)
    send_message(f"평가 손익 합계: {evaluation[0]['evlu_pfls_smtl_amt']}원")
    time.sleep(0.1)
    send_message(f"총 평가 금액: {evaluation[0]['tot_evlu_amt']}원")
    time.sleep(0.1)
    send_message(f"=================")
    return stock_dict

def get_balance():
    """현금 잔고조회"""
    PATH = "uapi/domestic-stock/v1/trading/inquire-psbl-order"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json", 
        "authorization":f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"TTTC8908R",
        "custtype":"P",
    }
    params = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "PDNO": "005930",
        "ORD_UNPR": "65500",
        "ORD_DVSN": "01",
        "CMA_EVLU_AMT_ICLD_YN": "Y",
        "OVRS_ICLD_YN": "Y"
    }
    res = requests.get(URL, headers=headers, params=params)
    cash = res.json()['output']['ord_psbl_cash']
    send_message(f"주문 가능 현금 잔고: {cash}원")
    return int(cash)

def buy(code="005930", qty="1"):
    """주식 시장가 매수"""  
    PATH = "uapi/domestic-stock/v1/trading/order-cash"
    URL = f"{URL_BASE}/{PATH}"
    data = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "PDNO": code,
        "ORD_DVSN": "01",
        "ORD_QTY": str(int(qty)),
        "ORD_UNPR": "0",
    }
    headers = {"Content-Type":"application/json", 
        "authorization":f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"TTTC0802U",
        "custtype":"P",
        "hashkey" : hashkey(data)
    }
    res = requests.post(URL, headers=headers, data=json.dumps(data))
    if res.json()['rt_cd'] == '0':
        send_message(f"[매수 성공]{str(res.json())}")
        return True
    else:
        send_message(f"[매수 실패]{str(res.json())}")
        return False

def sell(code="005930", qty="1"):
    """주식 시장가 매도"""
    PATH = "uapi/domestic-stock/v1/trading/order-cash"
    URL = f"{URL_BASE}/{PATH}"
    data = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "PDNO": code,
        "ORD_DVSN": "01",
        "ORD_QTY": qty,
        "ORD_UNPR": "0",
    }
    headers = {"Content-Type":"application/json", 
        "authorization":f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"TTTC0801U",
        "custtype":"P",
        "hashkey" : hashkey(data)
    }
    res = requests.post(URL, headers=headers, data=json.dumps(data))
    if res.json()['rt_cd'] == '0':
        send_message(f"[매도 성공]{str(res.json())}")
        return True
    else:
        send_message(f"[매도 실패]{str(res.json())}")
        return False

# 자동매매 시작
try:
    ACCESS_TOKEN = get_access_token()

    symbol_list = ["247540","091990","066970","028300","293490","263750","068760","196170","278280","253450","086520","096530","035760","112040","058470","035900","005290","357780","237690","041510","007390","145020","240810","108320","064760","056190","048260","025900","225570","032500","222800","215600","195940","214370","034230","403870","016790","067630","048410","078600","298380","141080","214150","122870","067160","299900","078340","215200","137400","039030","144510","098460","064550","090460","030190","323990","003380","215000","036540","085660","121600","053800","222080","376300","166090","086450","022100","256840","039200","095700","213420","000250","036930","068240","200130","100090","086900","084850","205470","348370","950130","272290","084990","084370","290650","140860","131290","069080","074600","214450","067310","348210","046890","151910","182400","003100","290510","383310","218410","101730","268600","206650","095340","189300","025980","294090","319660","178320","095660","235980","289220","033290","194480","230360","140410","052020","106240","082270","060250","287410","199800","950160","151860","278650","064260","049070","041190","091700","183300","099190","038540","089980","950220","090710","217270","060720","003800","085370","310210","121800","053030","267980","092040","091120","043150","041960","033640","054210","131970","030520","006730","243070","101490","298540","099430","038500","307750","102710","051500","039840","328130","243840","206560","036830","104460","032190","102940","110790","321550","299030","027360","029960","095610","060150","032300","230240","246710","015750","277810","047920","089970","104830","013120","086390","086980","048530","058820","035600","100120","119610","115450","104480","143240","061970","293780","031330","078020","080580","377030","330860","290670","063080","232140","063170","048550","077360","067000","089030","285490","319400","047820","088800","217330","122450","228670","214260","023160","179900","078160","136510","100130","041830","034950","036810","078130","050890","298870","048870","035890","036030","291230","033500","033310","371950","101160","294570","206640","03260","037070","078590","179290","281740","214870","032820","051370","060280","092190","136480","014620","204270","131370","099320","131390","089010","030530","100790","065350","023410","078070","058610","366030","083790","059090","399720","194700","121440","241840","094480","084110","025770","084650","034810","317330","042000","096240","226950","263720","027710","080160","035080","038290","245620","018000","108230","123860","011040","045100","101360","067990","340570","043610","228760","314130","118990","086890","018310","183490","080420","265520","042600","115180","336570","046440","175250","042420","052400","216080","039440","389140","045390","258830","143160","123420","214610","006910","033160","252990","365270","089600","064290","054950","02760","253840","299660","297090","025320","237880","363260","282880","079370","138080","053610","091580","122990","036800","013030","053300","093320","082800","138610","950190","094820","119860","038880","009520","149950","049180","108490","195990","082920","067280","389260","192440","019550","200670","126700","241820","337930","036200","318020","036890","036630","396270","220100","005860","030960","053580","225530","017890","150840","348150","160550","263920","148150","288330","180400","047310","044340","185490","083310","142760","365590","251370","146320","012700","297890","052710","334970","115960","114810","019210","370090","039560","261780","357230","074430","294140","306040","126340","068930","347860","054450","065660","362320","057880","069920","083450","065680","092130","056090","214180","088390","376980","073490","123040","216050","031980","352480","082850","251970","234340","136540","284620","095500","377450","060590","051160","087010","124560","061250","088290","220260","006620","078350","097780","044490","259630","056080","396300","023900","306620","376190","251120","182360","067290","060570","356860","052260","045970","125210","027830","090360","058970","211270","311690","138580","046120","166480","300080","042370","066410","109610","144960","232680","200710","388720","217600","102120","048910","018290","301300","119830","277880","128540","308080","270660","041590","036190","239610","092070","025950","191420","174900","061040","109860","083650","314930","361570","049950","382840","063570","192410","238090","090850","142280","332570","010170","067900","137950","109820","083930","092730","126600","228850","262260","290550","236200","340930","239890","200230","099750","040910","080220","037460","156100","273640","033560","060560","352700","361390","054620","203650","348030","054780","053280","043370","353590","357580","046390","171090","203400","021080","208640","023910","264450","112290","160980","347740","054050","023600","065450","041440","094360","115160","089890","111710","108860","007330","244460","039860","078150","005160","038390","161580","079940","094170","043650","018120","247660","036710","026150","052420","049720","138360","056700,","050110","402030","066700","289080","171120","100700","377460","068330","033170","058630","348350","276040","109740","040300","054920","256630","054670","057680","073640","046140","333620","267320","136410","051360","067390","207760","033200","040350","114190","234690","215100","190510","066590","201490","046110","099220","053050","053080","036010","373200","353810","215360","139670","021320","265560","104200","060310","347890","241690","084730","288620","068940","038070","071200","187420","086960","078890","322310","065530","168330","159580","226330","274090","377220","205500","039340","064820","060370","205100","236810","041930","290720","067080","186230","011370","052330","054800","065510","298060","260930","072870","199820","110990","290090","065560","036560","253590","058400","140070","049550","014470","122640","200350","120240","036620","093520","073560","153710","060240","095190","049960","066980","388050","094850","158430","122350","082210","376180","014940","261200","304840","014200","066620","204620","068790","311390","368770","126880","227950","214270","060900","072020","122310","007820","192250","225220","000440","140670","104540","214430","155650","011320","032850","071670","255440","187870","053260","057540","217730","352910","101930","049080","276730","053980","064240","001840","241520","369370","263700","096040","377330","043220","039290","005990","193250","123570","189980","027050","093190","067170","382480","354200","130580","215090","225190","105330","357880","950200","067570","019590","032790","013720","086820","159010","086040","016250","330350","051380","085670","256940","104620","012790","129890","040420","218150","037440","270870","105550","024810","263050","007680","004650","335890","170030","251630","053450","303530","241790","043910","066670","108380","066310","217500","013310","163730","412350","311320","033100","001540","220180","900100","950110","041460","047560","330730","290380","310200","131400","111870","042510","056730","089850","035610","150900","087260","024880","367000","241770","052790","263690","053590","020710","302430"] # 매수 희망 종목 리스트
    bought_list = [] # 매수 완료된 종목 리스트
    total_cash = get_balance() # 보유 현금 조회
    stock_dict = get_stock_balance() # 보유 주식 조회
    for sym in stock_dict.keys():
        bought_list.append(sym)
    target_buy_count = 4 # 매수할 종목 수
    buy_percent = 0.25 # 종목당 매수 금액 비율
    buy_amount = total_cash * buy_percent  # 종목별 주문 금액 계산
    soldout = False

    send_message("===국내 주식 자동매매 프로그램을 시작합니다===")
    while True:
        t_now = datetime.datetime.now()
        t_9 = t_now.replace(hour=9, minute=0, second=0, microsecond=0)
        t_start = t_now.replace(hour=9, minute=5, second=0, microsecond=0)
        t_sell = t_now.replace(hour=15, minute=15, second=0, microsecond=0)
        t_exit = t_now.replace(hour=15, minute=20, second=0,microsecond=0)
        today = datetime.datetime.today().weekday()
        if today == 5 or today == 6:  # 토요일이나 일요일이면 자동 종료
            send_message("주말이므로 프로그램을 종료합니다.")
            break
        if t_9 < t_now < t_start and soldout == False: # 잔여 수량 매도
            for sym, qty in stock_dict.items():
                sell(sym, qty)
            soldout == True
            bought_list = []
            stock_dict = get_stock_balance()
        if t_start < t_now < t_sell :  # AM 09:05 ~ PM 03:15 : 매수
            for sym in symbol_list:
                if len(bought_list) < target_buy_count:
                    if sym in bought_list:
                        continue
                    target_price = get_target_price(sym)
                    current_price = get_current_price(sym)
                    if target_price < current_price:
                        buy_qty = 0  # 매수할 수량 초기화
                        buy_qty = int(buy_amount // current_price)
                        if buy_qty > 0:
                            send_message(f"{sym} 목표가 달성({target_price} < {current_price}) 매수를 시도합니다.")
                            result = buy(sym, buy_qty)
                            if result:
                                soldout = False
                                bought_list.append(sym)
                                get_stock_balance()
                    time.sleep(1)
            time.sleep(1)
            if t_now.minute == 30 and t_now.second <= 5: 
                get_stock_balance()
                time.sleep(5)
        if t_sell < t_now < t_exit:  # PM 03:15 ~ PM 03:20 : 일괄 매도
            if soldout == False:
                stock_dict = get_stock_balance()
                for sym, qty in stock_dict.items():
                    sell(sym, qty)
                soldout = True
                bought_list = []
                time.sleep(1)
        if t_exit < t_now:  # PM 03:20 ~ :프로그램 종료
            send_message("프로그램을 종료합니다.")
            break
except Exception as e:
    send_message(f"[오류 발생]{e}")
    time.sleep(1)
