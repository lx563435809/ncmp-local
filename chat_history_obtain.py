import gzip
import re
import json
from binascii import a2b_hex, b2a_hex
from Crypto.Cipher import AES
import hashlib
from datetime import datetime, timezone, timedelta
import requests
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import unpad

EAPI_KEY = b"e82ckenh8dichen8"
EAPI_CRYPTOR = AES.new(EAPI_KEY, AES.MODE_ECB)

url = "https://interface.music.163.com/eapi/msg/private/history"

# -----------------------------
# MD5 生成函数
# -----------------------------
def md5encrypt(s: str) -> str:
    m = hashlib.md5()
    m.update(s.encode('utf-8'))
    return m.hexdigest()

def md5forencrypt(path: str, json_str: str) -> str:
    """生成 md5 签名"""
    s = f"nobody{path}use{json_str}md5forencrypt"
    return md5encrypt(s)

# -----------------------------
# AES 加密/解密函数
# -----------------------------
AES_KEY = b"e82ckenh8dichen8"
AES_BLOCK_SIZE = 16

def pkcs7_pad(s: str) -> bytes:
    pad_len = AES_BLOCK_SIZE - (len(s.encode('utf-8')) % AES_BLOCK_SIZE)
    return s.encode('utf-8') + bytes([pad_len] * pad_len)

def pkcs7_unpad(b: bytes) -> str:
    pad_len = b[-1]
    return b[:-pad_len].decode('utf-8')

def aesEncrypt(path: str, json_str: str) -> str:
    sign = md5forencrypt(path, json_str)
    plain_text = f"{path}-36cd479b6b5-{json_str}-36cd479b6b5-{sign}"
    padded = pkcs7_pad(plain_text)
    cipher = AES.new(AES_KEY, AES.MODE_ECB)
    encrypted = cipher.encrypt(padded)
    return b2a_hex(encrypted).upper().decode()

def aesDecrypt(encrypted_hex: str) -> str:
    cipher = AES.new(AES_KEY, AES.MODE_ECB)
    encrypted_bytes = a2b_hex(encrypted_hex)
    decrypted_bytes = cipher.decrypt(encrypted_bytes)
    return pkcs7_unpad(decrypted_bytes)

def data_decrypt(enc_data):
    # 先解压缩，如果数据确实是 gzip 格式
    try:
        enc_data = gzip.decompress(enc_data)
    except OSError:
        # 如果不是 gzip 格式，跳过解压
        pass

    # 解密并取消填充
    try:
        data = unpad(EAPI_CRYPTOR.decrypt(enc_data), AES.block_size)
        return data.decode('utf-8')
    except ValueError as e:
        print("解密失败，可能是填充错误:", str(e))
    return None


def onResponse(context, response):
    enc_data = response.content
    data = data_decrypt(enc_data)

    if not data:
        print("解密失败或无数据")
        return False

    try:
        data = json.loads(data)
    except json.JSONDecodeError as e:
        print("解析 JSON 数据失败:", str(e))
        return False

    if 'msgs' not in data:
        print("没有发现记录")
        return False

    for item in data.get('msgs', []):
        timestamp = item.get('time')

        # 🚨 如果早于 end_date，直接停止
        if timestamp and timestamp < end_timestamp:
            print("已到达结束时间，停止请求")
            return False

        from_nickname = item.get('fromUser', {}).get('nickname', 'Unknown')
        msg_data = json.loads(item.get('msg', '{}'))
        msg_content = msg_data.get('msg', 'No message')

        if timestamp:
            timestamp_seconds = timestamp / 1000
            utc_time = datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc)
            beijing_time = utc_time + timedelta(hours=8)
            formatted_time = beijing_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            formatted_time = "No time available"

        print(f"{formatted_time} {from_nickname}: {msg_content}")

    return True

# 请求头
cookies = {
    'WEVNSM': '1.0.0',
    'WNMCID': 'hkrxwb.1772257448543.01.0',
    'os': 'pc',
    'deviceId': 'C0EEB40D7D8DF9B5595395DFB79BAFF8A2DC79E270B5E82DE63D',
    'osver': 'Microsoft-Windows-10-Professional-build-19045-64bit',
    'clientSign': '70:B5:E8:2D:E6:3D@@@WD-WCC6Y1NTUJ9T@@@@@@1410bb0e0246630956c07ee1f8442306de1d66354e0cf64253bd586958013071',
    'channel': 'netease',
    'NMTID': '00OVo8aysmK-DNEbkOZuOWP4j_wLqQAAAGZBKXyww',
    '__remember_me': 'true',
    '_ntes_nnid': '6528cb23ed2a63d44beb6603f0d33cc1,1757387587408',
    '_ntes_nuid': '6528cb23ed2a63d44beb6603f0d33cc1',
    '_iuqxldmzr_': '33',
    'mode': 'OptiPlex 7070',
    'JSESSIONID-WYYY': 'v4K%2BmvyyGKEfgExBAkd8QiDcXzSTnT87H%2BnaUs%5CO%2BUUQOz7Fse1JRUO0i%2F5oN%2BlO%2F%2BVG4O9qC35KtaIUjKdGw3pVC7IM7%2Fj16WUEHWtxaqtk3DBWlgRkv1msiKfgY6s5JyO9Zeu%5CDZsC1peslZWP5OfuX%5Cv9rqyp%2FwPAxvQ75iTP0zdF%3A1770273145153',
    'appver': '3.1.28.205001',
    '__csrf': '57c4aac476c6f888dfd83f1e775dbfd7',
    'MUSIC_U': '00357B9577C78F539D6D7A59C6BFD236FC09E65C34CFC4B6FEB5FDB70B3A79AC395FE29868CF4F76F67539BE2B2FA99221AAB6EC8D8DFCB798FE873BB8EB97B3716A893ACA5776ED10ACBB4170ED60519C9208EB6AD678C3251E287A6A45055821AC6522B91AAB67C7CA0B26A4A91497C03C8CF945A30860DC46163A2347FC603A9E3DCEC0B3C9B90EB82CA826E6C6D64FA63BE4F6B7405888E4303F79D1AAEB91117BD9E2BE17E057988D32086BE0451F088BA8A790C01850A72BF3DD03310D5D675A122682C7EEFCC09E00B824CF1B061C0D872C8C7FEF2CF2B9D4136F0A2523DAAAED3E14A0B429FD26C69778C8E28B2D370E9BDFA7B1093F4E8DA420EF9DAB98D059154A66CBA698C6178925B347CFC4CDF6A275C8C20AC840C25640A5470E035DAE628F88DBFF76A6AFD3FE6ADED873E17E2A3428F9F48B06692F8E8155BF3A001675FFDE3A3CFDEC2CB63E16915F7A48F67B13164823B4C1FFDD770EAD7DA3653CF885B3187FAAA3887CDC217989D573E6F11CD36E4132EB9D6F1184A8DF3CF1E579BF18018DCF28D8CD3D5640BD3809561ECEB0CC8846168A287B685962479014DCEE8B41403A980CEBC79400708A4238A0865AAF1F8B3208CB5C9BA44077731C0C6E7A9848EC8D951318D92BDD5A3417C7532A8CCF1672AF5940361ACDA046EA32E6A32F972B08A6B9B2666EB5',
    'ntes_kaola_ad': '1',
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36 Chrome/91.0.4472.164 NeteaseMusicDesktop/3.1.2.203359',
    'Content-Type': 'application/x-www-form-urlencoded',
    'mconfig-info': '{"IuRPVVmc3WWul9fT":{"version":729088,"appver":"3.1.2.203359"}}',
    'origin': 'orpheus://orpheus',
    'sec-ch-ua': '"Chromium";v="91"',
    'sec-ch-ua-mobile': '?0',
    'sec-fetch-site': 'cross-site',
    'sec-fetch-mode': 'cors',
    'sec-fetch-dest': 'empty',
    'accept-language': 'en-US,en;q=0.9',
    # 'Cookie': 'os=pc; deviceId=C0EEB40D7D8DF9B5595395DFB79BAFF8A2DC79E270B5E82DE63D; osver=Microsoft-Windows-10-Professional-build-19045-64bit; NMTID=00OmZV3Yve4UI9lNUkvjkKMsReQxjMAAAGNH4q2tg; channel=netease; WEVNSM=1.0.0; ntes_kaola_ad=1; clientSign=70:B5:E8:2D:E6:3D@@@WD-WCC6Y1NTUJ9T@@@@@@1410bb0e0246630956c07ee1f8442306de1d66354e0cf64253bd586958013071; mode=OptiPlex 7070; MUSIC_U=00A3C9813001E643011AFA7847052D7A914928A91D585925632D0ECFC86FC827B3E7C5047509A6C60AC4140FBAD4B7CDF6F868BD33F0780D3BBC73B7F27691CD0D30C17C95D87ABA42A6A16A87C4C743692D0358401CFC265C2BF43C287E60A4CFAB27BF0A1F06D94701A85CE2DFB913B1F77FEEF2BCC28940DEB8E8167D89B2C45CAF602C7ABE1FCE59CC67000860D100FD500D3E7910680EC4E7E9E31A3EAAF262AC19E7D88E289DEAF3D52A052BA079664E9B57EFD9C41CE5D27AEF69E001ABEDAE8EAEC5377B521390A4B7B636A332E310992C2234218E7F135AEBBC63CD65501E6A512A183D0DB2D51A62FB8C588E0CEB11186A53693654D2DF57870475EB5FD86686F6757C5AFDCCE30AD171896B3BAE8756EA0E4E9280BB49BE0D4CA04BE0CE10C2D47CA2A0C609075AC168F5B5B0AF5032149B93B3FB0D47A19AC8F3AF30FEA3FD866E11BEB0F905A805A8FEF20A9E37A57FE7B75B7D8D0439FE9CD345C86FA6E19983771DB92F438F66CDB1A8F72717147C5D0613D6950CA8EA53F8426A71DBB40C093400B7AFBFCCA57683FA5402F6D8F5868E1CA68CAAF58CA863DB52F19A06FBE7B3C7791FD56187D71C133576BCBB20FA3863E7B59D00CE7A94EA; _ntes_nuid=ad229bb2d13a41e3b7a7d4b15f32b456; _ntes_nnid=ad229bb2d13a41e3b7a7d4b15f32b456,1731916338594; _iuqxldmzr_=33; JSESSIONID-WYYY=19vNgAcgbxf5h3bvU5RKNrcXEEemTeIKXh9KarNYy0CrQZvyOWP46y%2B7rssuuTQQDMGRpjug449Zoj%5CtvN2kvXzvVP3ioYhWth6sJMQi02683t%2BllF6wE7DGGmZAg%2BcqBcvG%5Ck0UuxHUeS3u%2BMGJ8bmaCXqOMz3xttvR9jK3Yk2QCwJF%3A1733107234996; __csrf=3fd2c8b511f18b96b4d9204d90bff912; appver=3.1.2.203359; WNMCID=dgtksm.1730712088682.01.0',
}

# 原始密文（示例）
encrypted_text = "49784C69DFB48DED4ABE5ED832A4339D9034DBA03DF594A81E38B770D4F8A5F12BBBFD93917549FD040F92F3FEE0984804B8D743C1E891F23A6E86803E842C2BC372D57E1EE635F6A9F6F4EA98A5041F437B52D2B9AC39BACFC06978A128F1C260FE3777E382B4FF1BB2BFD558FDFA0E70C7583BCEDC64F7FD18DA318D28D8F7A9C6B6803E78785428B70710355976EAB89BBDC57BC80A54F97CE972F6960D50552A8926558246941A9E13F8A170C750EA1FF041BC9C70CF0542309AC07C7C0821E6C5DE053BD6A5A061F5392B307B87A05F9DE8722A3BD7FB5E102EFFD68A3F81D93818A97999F7A97D1F4FA065CFEBE147589F49F66414BCBB8565A9D74A42F1F8FEFEDD860826CF84CD1E9DE81B6D50F8C6A604CCC29BE2237E03DA9468B86ED6A37BAD0E8F58DBD5DEB8B7F8AD8D001812F9CBEAED9C7E0545CA91824A6E252D34416D5BC20B45C81728916C85AC13761CC37E25AA9F0BF79F45713F5CFF1A8D5061C580C20F5DBAE30819C6D54CD3C77097A5935FD5C36D73D00AA41DE8BEC047D37836747551A3E07EC1FA4D56F56471A51609CC97C129064524201571FAA6F1D4FE6BAA7567B92995C2599256C6A11A0C050267D329A9F686C6AC40FF60013F1CF221119F2F8BA038A692DE56A69E949FFCD42569D821C3484EFE3B3377229D5CD116A8896DEFDC214BC6C69C168FE2DB2E68501F70D8D5A275E47498"

# 解密
decrypted = aesDecrypt(encrypted_text)
# print("解密后的明文:\n", decrypted)

# 修改 time 字段（示例）


# ====== 起始时间 ======
new_date = "2025-06-08 00:00:00"
new_limit = "10"

# ====== 结束时间（早于这个就停止）=====
end_date = "2025-06-01 00:00:00"
# ==============================

beijing_tz = timezone(timedelta(hours=8))

# 起始时间 → 13位时间戳
dt = datetime.strptime(new_date, "%Y-%m-%d %H:%M:%S")
dt = dt.replace(tzinfo=beijing_tz)
new_time = str(int(dt.timestamp() * 1000))

# 结束时间 → 13位时间戳
end_dt = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
end_dt = end_dt.replace(tzinfo=beijing_tz)
end_timestamp = int(end_dt.timestamp() * 1000)

# 提取 JSON 部分
json_part = re.search(r'-36cd479b6b5-(.*?)-36cd479b6b5-', decrypted).group(1)
data = json.loads(json_part)

# 修改字段
data["time"] = new_time
data["limit"] = new_limit

# 注意：必须保持无空格格式，否则 md5 会不同
new_json_str = json.dumps(data, separators=(',', ':'))

# 生成新密文
path = "/api/msg/private/history"
new_encrypted = aesEncrypt(path, new_json_str)

# print("修改后的 JSON:\n", new_json_str)
# print(new_encrypted)

# data = {
#     'params': '49784C69DFB48DED4ABE5ED832A4339D9034DBA03DF594A81E38B770D4F8A5F12BBBFD93917549FD040F92F3FEE0984804B8D743C1E891F23A6E86803E842C2B46B3AD6EEE1223F5C54368CF070A49A2437B52D2B9AC39BACFC06978A128F1C260FE3777E382B4FF1BB2BFD558FDFA0E70C7583BCEDC64F7FD18DA318D28D8F7A9C6B6803E78785428B70710355976EAB89BBDC57BC80A54F97CE972F6960D50552A8926558246941A9E13F8A170C750EA1FF041BC9C70CF0542309AC07C7C0821E6C5DE053BD6A5A061F5392B307B87A05F9DE8722A3BD7FB5E102EFFD68A3F81D93818A97999F7A97D1F4FA065CFEBE147589F49F66414BCBB8565A9D74A42F1F8FEFEDD860826CF84CD1E9DE81B6D50F8C6A604CCC29BE2237E03DA9468B86ED6A37BAD0E8F58DBD5DEB8B7F8AD8D001812F9CBEAED9C7E0545CA91824A6E252D34416D5BC20B45C81728916C85AC13761CC37E25AA9F0BF79F45713F5CFF1A8D5061C580C20F5DBAE30819C6D54CD3C77097A5935FD5C36D73D00AA41DE8BEC047D37836747551A3E07EC1FA4D56F56471A51609CC97C129064524201571FAA6F1D4FE6BAA7567B92995C2599256C6A11A0C050267D329A9F686C6AC40FF60013F1CF221119F2F8BA038A692DE5668F6CC3510591421CD84F915B11340EC0646CF2E066EAF5428DC118794F4CC38A6073F78C543B0A89158359B0E15B6F6',
# }

data = {
    'params': new_encrypted,
}

response = requests.post(url, headers=headers, data=data, cookies=cookies)
# print(f"Response Status Code: {response.status_code}")
# print(f"Response Content (raw): {response.content}")

if response.status_code == 200:
    onResponse(None, response)
else:
    print("请求失败，请检查请求参数和服务器状态")

# onResponse(None, response)
