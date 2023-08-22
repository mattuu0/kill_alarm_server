from dotenv import load_dotenv
load_dotenv()

import qrcode
from database.models import gen_iotid,iot_device
from database.setting import session
import jwt

iot_deviceid = gen_iotid()

import uuid
import json
import os
import zipfile
from io import BytesIO

secret_key = os.environ["IOT_Token_Secret"]
algorithm = "HS512"

def register_device():
    tokenid = str(uuid.uuid4())

    payload = {"deviceid" : iot_deviceid,"tokenid":tokenid}

    token = jwt.encode(payload,secret_key,algorithm=algorithm)

    iot_token = str(token)

    register_device = iot_device()
    register_device.deviceid = iot_deviceid
    register_device.tokenid = tokenid

    session.add(register_device)
    session.commit()

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=3,
        border=2,
    )

    qr.add_data(iot_deviceid)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    qrcode_path = f"QR_Code.png"

    register_json = {
        "deviceToken" : iot_token,
        "deviceid" : iot_deviceid
    }

    img_io = BytesIO()
    img.save(img_io,format="PNG")

    with zipfile.ZipFile(f"{iot_deviceid}.zip","w") as write_zip:
        write_zip.writestr("RegisterInfo.json",json.dumps(register_json).encode("utf-8"))
        write_zip.writestr(qrcode_path,img_io.getvalue())
    
    img_io.close()