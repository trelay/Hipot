# -*- coding: UTF-8 -*-
from zeep import Client
import pyvisa
from time import sleep
from time import strftime, localtime


url = r'http://api.ramaxel.com/hw_manufacture/MidLayer.asmx?WSDL'
#url = r'http://10.233.80.81:8080/hw_manufacture/MidLayer.asmx?WSDL'

PASS="""
        PPPPPPPP             A                    S S S           S S S
        P       P           A A                 S       S       S       S
        P        P         A   A                S               S
        P       P         A     A                S               S
        P      P         A       A                S               S
        PPPPPP          A         A                  S               S
        P              AAAAAAAAAAAAA                   S               S
        P             A             A                   S               S
        P            A               A                  S               S
        P           A                 A         S      S        S      S
        P          A                   A          S S S           S S S   
"""

FAIL="""
        FFFFFFFFFFF               A                      I          L
        F                        A A                     I          L
        F                       A   A                    I          L
        F                      A     A                   I          L
        FFFFFFFFFFF           A       A                  I          L
        F                    A         A                 I          L
        F                   AAAAAAAAAAAAA                I          L
        F                  A             A               I          L
        F                 A               A              I          L
        F                A                 A             I          L
        F               A                   A            I          LLLLLLLLLLLL
"""

input_xml='''
<?xml version="1.0" encoding="UTF-8"?><GetProcessStatus>
<Import><Barcode>{0}</Barcode><Process>{1}</Process><Site>MP1</Site>
<CheckType>EnterStation</CheckType></Import></GetProcessStatus>
'''
sub_xml = '''
<?xml version="1.0" encoding="UTF-8"?><SubmitATETestResult><Import><TaskOrder></TaskOrder><Barcode>{0}</Barcode>
<StartDateTime>{1}</StartDateTime><StopDateTime>{2}</StopDateTime><TestResult>{3}</TestResult>
<ATEName>ST-SmarX8500A0125</ATEName><ATEVer>ITESTINSIDE-1.045-1.000</ATEVer><ATEDesc></ATEDesc><UUTName></UUTName><TPSName></TPSName>
<TPSVer></TPSVer><TPSProduct></TPSProduct><TPSProductLine></TPSProductLine><LineCode></LineCode><ProcessCode>ST</ProcessCode><SiteCode>{4}</SiteCode>
<FailDesc></FailDesc><TestBy>kdzb</TestBy></Import></SubmitATETestResult>
'''

station_name = "EST-MP1"
inf_name = "GetProcessStatus"
sub_name = "SubmitATETestResult"

def test_import(input_xml,inf_name):
    input_xml = input_xml.replace("\n","")
    
    client = Client(url)
    output_xml = client.service.Get_Info_Frmbarcode(inf_name, input_xml)
    return output_xml
    
def clean_hi(hi_instrument):
    while True:
        if "No error" in hi_instrument.query('SYST:ERR?'):
            sleep(0.2)
	    break

setting=(
'SAFE:STEP 1:DEL',\
'SAFE:STEP 1:DEL',\
'SAFE:STEP 1:DEL',\
'SAFE:STEP 1:IR 50',\
'SAFE:STEP 1:IR:LIM:LOW 100000',\
'SAFE:STEP 1:IR:TIME 2',\
'SAFE:STEP 1:IR:TIME:RAMP 5',\
'SAFE:STEP 2:DC 2121',\
'SAFE:STEP 2:DC:LIM 0.01',\
'SAFE:STEP 2:DC: TIME: DWEL 1.1',\
'SAFE:STEP 2:DC:TIME 1',\
'SAFE:STEP 2:DC: TIME: RAMP 1',\
'SAFE:STEP 2:DC:TIME:FALL 1',\
'SAFE:STEP 3:GB 25',\
'SAFE:STEP 3:GB:TIME:TEST 2')

def init_dev(hi_instrument):
    for cmd in setting:
        hi_instrument.write(cmd)
        sleep(0.2)

if __name__=="__main__":
    while True:
        #####input SN and order###
        while True:
            SN = raw_input("扫描条码:".decode('utf-8').encode('gbk'))
            if "5005" in SN:
                break
                
        while True:
            order = raw_input("扫描任务令:".decode('utf-8').encode('gbk'))
            if "EB" in order and len(order)==8:
                break

        ###### check station######    
        inport_xml = input_xml.format(SN, station_name)
        output_xml = test_import(inport_xml,inf_name)
        if '''StatusValue="1"''' not in output_xml:
            print(u'测试站位错误，这个整机不能测试安规')
            continue

        ######  init hipot instrument########
        rm = pyvisa.ResourceManager()
        hi_name = rm.list_resources()[0]
        hi_instrument = rm.open_resource(hi_name)
        if u'Chroma' not in hi_instrument.query('*IDN?'):
            print(u'设备初始化失败')
            continue

        ######  1. init instrument   2. start test
        print(u'测试开始')
        init_dev(hi_instrument)
        start_t = strftime("%Y-%m-%d %H:%M:%S", localtime())
        print(start_t)
        hi_instrument.write("SAFE:STAR")
        sleep(17)

        ######### check result#####
        test_result = hi_instrument.query('SAFE:RES:ALL?')
        end_t = strftime("%Y-%m-%d %H:%M:%S", localtime())
        print(test_result)
        if '116,116,116' not in test_result:
            print(FAIL)
            hi_result = "1"
            fl_nm = 'sn_fail.txt'
        else:
            print(PASS)
            hi_result = "0"
            fl_nm = 'sn_pass.txt'

        ###### submit test result ######    
        subATE_xml = sub_xml.format(SN,start_t,end_t,hi_result,station_name)
        output_xml = test_import(subATE_xml,sub_name)
        if '''ErrorCode>0''' not in output_xml:
            print(u'不能上传安规测试记录')
            print(FAIL)
            print(u'不能上传安规测试记录')

        ######### save log for tracking #####
        log_msg = "{0}\t\t{1}\n".format(start_t,SN)
        with open(fl_nm, 'a') as f:
            f.write(log_msg)

        ###### clean errors if exist ###
        clean_hi(hi_instrument)
        ###### Better to close it for next round of test###
        hi_instrument.close()
        
