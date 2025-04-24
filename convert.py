from cell import Cell, CellCollection
import xml.etree.ElementTree as ET
import shutil
import subprocess
import os

def insertElementList(root,elementList, after=None):

    position = -1
    if after is not None:
        position = find_last_element_index(root,after)

    for elem in reversed(elementList):
        if position > -1:
            root.insert(position + 1, elem)
        else:
            root.append(elem)

    return root

def addXMLBoilerPlate(root):

    output = '<?xml version="1.0" ?>\n' + ET.tostring(root, encoding='unicode')
    output = output.replace('><',">\n\t<")
    return output


def substitueAsynPorts(input_xml):
    asynPortClasses=["asyn.AsynSerial","mks937a.mks937a","digitelMpc.digitelMpc"]
    tree = ET.ElementTree(ET.fromstring(input_xml))
    root = tree.getroot()
    
    # Step 1: Build a mapping from asyn.AsynSerial name -> replacement name
    serial_replacements = {}
    for elem in root.findall("asyn.AsynSerial"):
        serial_name = elem.get("name")
        serial_replacements[serial_name] = None  # Placeholder
    
    # Step 2: Determine replacement names based on references
    for elem in root:
        if elem.tag in asynPortClasses:
            if elem.tag != "asyn.AsynSerial":
                port = elem.get("port")
                if port in serial_replacements:
                    serial_replacements[port] = f"{elem.get('name')}_PORT"
    
    # Step 3: Remove entries with None values
    serial_replacements = {k: v for k, v in serial_replacements.items() if v is not None}
    
    # Step 4: Replace occurrences in all elements
    for elem in root:
        if elem.tag in asynPortClasses:
            for attr in elem.attrib:
                if elem.attrib[attr] in serial_replacements:
                    elem.attrib[attr] = serial_replacements[elem.attrib[attr]]

    # Convert class to asyn.AsynSerial
    for elem in root.findall("asyn.AsynSerial"):
        elem.tag = "asyn.AsynIP"

    # Clear the port
    for elem in root.findall("asyn.AsynIP"):
        elem.set("port", f"192.168.{target.cell}.")

    # Remove priority
    for elem in root.findall("asyn.AsynIP"):
        if "priority" in elem.attrib:
            del elem.attrib["priority"]
    
    # Output modified XML with declaration
    return addXMLBoilerPlate(root)

def remove_unwanted_tags(input_xml,unwanted_tags):
    tree = ET.ElementTree(ET.fromstring(input_xml))
    root = tree.getroot()

    
    # Remove elements with unwanted tags
    for elem in root.findall("*"):
        if elem.tag in unwanted_tags:
            root.remove(elem)
    
    # Output modified XML with declaration
    return addXMLBoilerPlate(root)

# Returns index of last instance on element found
def find_last_element_index(root,target):

    last_target = None
    for elem in root.findall(target):
        last_target = elem
    
    # If we found an asyn.AsynIP element, insert after it
    if last_target is not None:
        # Find the position to insert after the last asyn.AsynIP
        for i, elem in enumerate(root):
            if elem == last_target:
                return i
        return -1
    else:
        return -1

def add_plc_ports(input_xml,after=None):
    tree = ET.ElementTree(ET.fromstring(input_xml))
    root = tree.getroot()
    elementList = list()
    # Create the new FINS.FINSUDPInit element
    fins_elem = ET.Element("FINS.FINSUDPInit")
    fins_elem.set("ip", "192.168.5.10")
    fins_elem.set("name", "VLVCC_01_FINS")
    fins_elem.set("simulation", "None")
    
    eip_element = ET.Element("ether_ip.EtherIPInit")
    eip_element.set("device",f"SR{target.cell:02d}C-VA-VLVCC-01")
    eip_element.set("ip",f"192.168.{target.cell}.10")
    eip_element.set("name","VLVCC_01.INFO")
    eip_element.set("port","VLVCC_01_EIP")

    elementList.append(eip_element)
    elementList.append(fins_elem)

   
    root=insertElementList(root,elementList,after)

    return addXMLBoilerPlate(root)

def add_NX102_readReal(input_xml, after = None):
    tree = ET.ElementTree(ET.fromstring(input_xml))
    root = tree.getroot()
    elementList = list()
    index = 0

    for elem in root.findall("mks937a.mks937aGauge"):
        index += 1
        id = elem.get("id")
        name = elem.get("name")
        dom = elem.get("dom")
        vc = target.gaugeConfig[name]["vlvcc"]
        slot = target.gaugeConfig[name]["slot"]
        chan = ""
        if slot == "A":
            chan="1"
        else:
            chan="2"

        readRealElem = ET.Element("dlsPLC.NX102_readReal")
        readRealElem.set("device", f"{dom}-VA-GAUGE-{id}:RAW")
        readRealElem.set("name", f"PLC_COMB0{index}")
        readRealElem.set("port", "VLVCC_01_EIP")
        readRealElem.set("tag", f"{dom}_VC{vc}_GCTLR_{id}_COMB_{slot}_C{chan}_Comb_mBar")
        elementList.append(readRealElem)


    root=insertElementList(root,elementList,after)

    return addXMLBoilerPlate(root)

def convertFastVacuum(input_xml):
    tree = ET.ElementTree(ET.fromstring(input_xml))
    root = tree.getroot()

    gauges = dict()
    elementList = list()

    fvMaster = ET.Element("dlsPLC.fastVacuumMaster",dom=f"SR{target.cell:02d}C",eip_port="VLVCC_01_EIP",fins_port="VLVCC_01_FINS",name="FV.MASTER")

    for elem in root.findall("FastVacuum.auto_Channel16"):
        gauges[elem.get("name")] = elem.get("img")

    for gauge in gauges:
        elem = ET.Element("dlsPLC.fastVacuumChannel",img=gauge,id=gauges[gauge],master="FV.MASTER",name=f"FV.G{int(gauges[gauge])}")
        elementList.append(elem)

    root.append(fvMaster)
    for elem in elementList:
        root.append(elem)

    return addXMLBoilerPlate(root)

def convertValves(input_xml,after=None):  
    tree = ET.ElementTree(ET.fromstring(input_xml))
    root = tree.getroot()  

    valves = list()
    elementList = list()

    for elem in root.findall("dlsPLC.vacValveDebounce"):
        valves.append(elem.get("device"))

    
    for valve in valves:
        nxValve = ET.Element("dlsPLC.NX102_vacValveDebounce",ILKNUM="1",device=valve,name=f"V{valve[-1]}",port="VLVCC_01_EIP",tag="V",tagidx=f"{valve[-1]}")
        elementList.append(nxValve)

    root = insertElementList(root,elementList,after=after)

    return addXMLBoilerPlate(root)

def addMks937abCombGauge(input_xml,gauge,mks):  
    tree = ET.ElementTree(ET.fromstring(input_xml))
    root = tree.getroot()

    dom = f"SR{target.cell:02d}{gauge.split('_')[1]}"
    id = f"{int(gauge.split('_')[-1]):01d}"
    input = f"{dom}-VA-GAUGE-{int(id):02d}:RAW"
            
    gaugeElement = ET.Element(f"mks937{mks}.mks937{mks}GaugeEGU",dom=dom,id=id,input=input,name=gauge)

    position = find_last_element_index(root,f"mks937{mks}.mks937{mks}GaugeEGU")
    if position < 0:
        position = find_last_element_index(root,"mks937a.mks937a")
    root.insert(position + 1, gaugeElement)


    return addXMLBoilerPlate(root)

def addEpicsEnvs(input_xml):

    tree = ET.ElementTree(ET.fromstring(input_xml))
    root = tree.getroot()

    envList = list()

    envList.append(ET.Element("EPICS_BASE.EpicsEnvSet",key="IOCSH_PS1",value=f"SR{target.cell:02d}C-VA-IOC-01 -&gt;"))
    envList.append(ET.Element("EPICS_BASE.EpicsEnvSet",key="EPICS_CA_AUTO_ADDR_LIST",value="NO"))
    envList.append(ET.Element("EPICS_BASE.EpicsEnvSet",key="EPICS_CA_ADDR_LIST",value="172.23.207.255"))
    envList.append(ET.Element("EPICS_BASE.EpicsEnvSet",key="EPICS_CAS_AUTO_BEACON_ADDR_LIST",value="NO"))
    envList.append(ET.Element("EPICS_BASE.EpicsEnvSet",key="EPICS_CAS_BEACON_ADDR_LIST",value="serverIP"))

    root = insertElementList(root,envList,after="devIocStats.devIocStatsHelper")

    return addXMLBoilerPlate(root)

def addMPCInterlocks(input_xml):
    tree = ET.ElementTree(ET.fromstring(input_xml))
    root = tree.getroot()

    straightIonps = list()
    arcIonps = list()
    elementList = list()

    for elem in root.findall("digitelMpc.digitelMpcIonp"):
        mpc = elem.get("MPC")
        if f"{mpc.split('_')[1]}" == "S":
            straightIonps.append(elem.get("device"))
        else:
            arcIonps.append(elem.get("device"))

    for ionp in straightIonps:
        elementList.append(ET.Element("dlsPLC.NX102_interlock",device=f"{ionp}:MPS_ILK",interlock="",port="VLVCC_01_EIP",tag="MPC",tagidx="1",desc="MPS Interlock"))

    for ionp in arcIonps:
        elementList.append(ET.Element("dlsPLC.NX102_interlock",device=f"{ionp}:MPS_ILK",interlock="",port="VLVCC_01_EIP",tag="MPC",tagidx="2",desc="MPS Interlock"))


    root = insertElementList(root,elementList,after="dlsPLC.NX102_readReal")


    return addXMLBoilerPlate(root)
    
def addPLCIO(input_xml):
    tree = ET.ElementTree(ET.fromstring(input_xml))
    root = tree.getroot()

    elementList = list()
    elementList.append(ET.Element("dlsPLC.NX102_digitalIn",device=f"SR{target.cell:02d}C-VA-VLVCC-01:DIGITAL01",name="DIG_01",port="VLVCC_01_EIP",tagidx="1"))
    elementList.append(ET.Element("dlsPLC.NX102_digitalIn",device=f"SR{target.cell:02d}C-VA-VLVCC-01:DIGITAL02",name="DIG_02",port="VLVCC_01_EIP",tagidx="2"))

    elementList.append(ET.Element("userIO.bi ",DESC="Rack 01 Fan Status",DTYP="Soft Channel",INP=f"SR{target.cell:02d}C-VA-VLVCC-01:DIGITAL01:RAWBIT.B0 CP",ONAM="HEALTHY",OSV="NO_ALARM",P="SR05C-VA-FANC-01",R=":STA",SCAN="Passive",ZNAM="FAIL",ZSV="MAJOR",archiver_rate="3600 Monitor", name="VAFAN_01"))
    elementList.append(ET.Element("userIO.bi ",DESC="Rack 02 Fan Status",DTYP="Soft Channel",INP=f"SR{target.cell:02d}C-VA-VLVCC-01:DIGITAL01:RAWBIT.B1 CP",ONAM="HEALTHY",OSV="NO_ALARM",P="SR05C-VA-FANC-02",R=":STA",SCAN="Passive",ZNAM="FAIL",ZSV="MAJOR",archiver_rate="3600 Monitor", name="VAFAN_02"))
    elementList.append(ET.Element("userIO.bi ",DESC="Rack 03 Fan Status",DTYP="Soft Channel",INP=f"SR{target.cell:02d}C-VA-VLVCC-01:DIGITAL01:RAWBIT.B2 CP",ONAM="HEALTHY",OSV="NO_ALARM",P="SR05C-VA-FANC-03",R=":STA",SCAN="Passive",ZNAM="FAIL",ZSV="MAJOR",archiver_rate="3600 Monitor", name="VAFAN_03"))
    elementList.append(ET.Element("userIO.bi ",DESC="Rack 01 Duplex PSU Status",DTYP="Soft Channel",INP=f"SR{target.cell:02d}C-VA-VLVCC-01:DIGITAL01:RAWBIT.B3 CP",ONAM="HEALTHY",OSV="NO_ALARM",P="SR05C-VA-PSU-01",R=":STA",SCAN="Passive",ZNAM="FAIL",ZSV="MAJOR",archiver_rate="3600 Monitor", name="VAPSU_01"))
    elementList.append(ET.Element("userIO.bi ",DESC="Rack 02 Duplex PSU Status",DTYP="Soft Channel",INP=f"SR{target.cell:02d}C-VA-VLVCC-01:DIGITAL01:RAWBIT.B4 CP",ONAM="HEALTHY",OSV="NO_ALARM",P="SR05C-VA-PSU-02",R=":STA",SCAN="Passive",ZNAM="FAIL",ZSV="MAJOR",archiver_rate="3600 Monitor", name="VAPSU_02"))

    elementList.append(ET.Element("dlsPLC.NX102_powerSupply",device=f"SR{target.cell:02d}C-VA-PSU-01:1",name="PSU01.1",port="VLVCC_01_EIP",tagidx="1"))
    elementList.append(ET.Element("dlsPLC.NX102_powerSupply",device=f"SR{target.cell:02d}C-VA-PSU-01:2",name="PSU01.2",port="VLVCC_01_EIP",tagidx="2"))
    elementList.append(ET.Element("dlsPLC.NX102_powerSupply",device=f"SR{target.cell:02d}C-VA-PSU-02:1",name="PSU02.1",port="VLVCC_01_EIP",tagidx="3"))
    elementList.append(ET.Element("dlsPLC.NX102_powerSupply",device=f"SR{target.cell:02d}C-VA-PSU-02:2",name="PSU02.2",port="VLVCC_01_EIP",tagidx="4"))

    elementList.append(ET.Element("dlsPLC.NX102_IRVacuum",P=f"SR{target.cell:02d}-VA-VALVE-01",port="VLVCC_01_EIP"))

    if convertAllmks:
        root = insertElementList(root,elementList, after = "mks937b.auto_mks937bImgMean")
    else:
        root = insertElementList(root,elementList, after = "mks937a.auto_mks937aImgMean")


    return addXMLBoilerPlate(root)


def addExtraGaugeControllers(input_xml):
    tree = ET.ElementTree(ET.fromstring(input_xml))
    root = tree.getroot()

    for i in range(0,2):
        element = ET.Element("mks937b.mks937b",name=f"GCTLR_{target.d2GaugeControllers[i]}_01",device=f"SR{target.cell:02d}{target.d2GaugeControllers[i]}-VA-GCTLR-01",port=f"GCTLR_{target.d2GaugeControllers[i]}_01_PORT",address="001")
        insertElementList(root,[element],after="dlsPLC.NX102_interlock")

    return addXMLBoilerPlate(root)

def sortAsynPort(input_xml):
    tree = ET.ElementTree(ET.fromstring(input_xml))
    root = tree.getroot()
    elementList = list()

    for port in target.asynPorts:
        elementList.append(ET.Element("asyn.AsynIP", name=port,port=target.asynPorts[port]))

    if useSrVacCommon:
        for elem in reversed(elementList):
            root.insert(0, elem)
    else:
        root = insertElementList(root,elementList,after="EPICS_BASE.EpicsEnvSet")

    return addXMLBoilerPlate(root)

def addTerminalServer(input_xml):
    tree = ET.ElementTree(ET.fromstring(input_xml))
    root = tree.getroot()
    elementList = list()

    elementList.append(ET.Element("terminalServer.Moxa", HOST=f"192.168.{target.cell}.11", NCHANS='16', P = f"SR{target.cell:02d}C-VA-TSERV-01", R="", name="TSERV1"))
    elementList.append(ET.Element("terminalServer.Moxa", HOST=f"192.168.{target.cell}.12", NCHANS='16', P = f"SR{target.cell:02d}C-VA-TSERV-02", R="", name="TSERV2"))

    root = insertElementList(root,elementList,after="dlsPLC.fastVacuumChannel")
    return addXMLBoilerPlate(root)

def updateAutosave(input_xml):
    tree = ET.ElementTree(ET.fromstring(input_xml))
    root = tree.getroot()

    autosave = ET.Element("autosave.Autosave",bl="False",db_suffix=":SR",iocName=f"SR{target.cell:02d}",ip="172.23.194.14",path="/exports/home/ops-iocs/prod/autosave",req_prefix=f"SR{target.cell:02d}C",server="cs03r-cs-serv-14")

    root.insert(0, autosave)
    return addXMLBoilerPlate(root)

def addMks937bAddress(input_xml):
    tree = ET.ElementTree(ET.fromstring(input_xml))
    root = tree.getroot()

    for elem in root.findall("mks937b.mks937b"):
        elem.set("address","001")

    return addXMLBoilerPlate(root)

def addPVLogging(input_xml):
    tree = ET.ElementTree(ET.fromstring(input_xml))
    root = tree.getroot()

    pvlog = ET.Element("pvlogging.PvLogging", name="PVLOG")
    root.insert(0, pvlog)
    return addXMLBoilerPlate(root)

def addRgaPowerCycle(input_xml):
    tree = ET.ElementTree(ET.fromstring(input_xml))
    root = tree.getroot()
    
    elementList = list()

    elementList.append(ET.Element("SR-VA.auto_rgaPowerCycle", PORT="VLVCC_01_EIP", TAG="RGA_S_01_RESET", device=f"SR{target.cell:02d}S-VA-RGA-01"))
    elementList.append(ET.Element("SR-VA.auto_rgaPowerCycle", PORT="VLVCC_01_EIP", TAG="RGA_A_01_RESET", device=f"SR{target.cell:02d}A-VA-RGA-01"))
    elementList.append(ET.Element("SR-VA.auto_rgaPowerCycle", PORT="VLVCC_01_EIP", TAG="RGA_A_02_RESET", device=f"SR{target.cell:02d}A-VA-RGA-02"))
    root = insertElementList(root,elementList,after="FINS.FINSUDPInit")
    
    return addXMLBoilerPlate(root)

def addControllerStatus(input_xml):
    tree = ET.ElementTree(ET.fromstring(input_xml))
    root = tree.getroot()

    controllerStatus = ET.Element("dlsPLC.NX102_controller_status", port="VLVCC_01_EIP", device=f"SR{target.cell:02d}C-VA-VLVCC-01", name="PLC_CS")
    root = insertElementList(root,[controllerStatus],after="FINS.FINSUDPInit")
    return addXMLBoilerPlate(root)

def addSrVacCommon(input_xml):
    tree = ET.ElementTree(ET.fromstring(input_xml))
    root = tree.getroot()

    common = ET.Element("SR-VA.common", dom=f"SR{target.cell:02d}C", name="COMMON")
    root = insertElementList(root,[common],after="FINS.FINSUDPInit")
    return addXMLBoilerPlate(root)


# Example usage
# inputFileName = "SR06C-VA-IOC-01.xml"
# outputFilename = inputFileName.replace(".xml", "_converted.xml")
# cell = 6
# d2GaugeControllers = ["SS","KS"]

# target.asynPorts ={f"GCTLR_{target.d2GaugeControllers[0]}_01_PORT":f"192.168.{target.cell}.7001",
#             f"GCTLR_A_01_PORT":f"192.168.{target.cell}.11:7002",
#             f"GCTLR_S_01_PORT":f"192.168.{target.cell}.11:7003",
#             f"MPC_S_01_PORT":f"192.168.{target.cell}.11:7004",
#             f"MPC_A_01_PORT":f"192.168.{target.cell}.11:7005",
#             f"MPC_A_02_PORT":f"192.168.{target.cell}.11:7006",
#             f"RGA_PC_01_PORT":f"192.168.{target.cell}.12:7001",
#             f"GCTLR_{target.d2GaugeControllers[1]}_01_PORT":f"192.168.{target.cell}.12:7002",
#             f"GCTLR_A_02_PORT":f"192.168.{target.cell}.12:7003",
#             f"GCTLR_A_03_PORT":f"192.168.{target.cell}.12:7004",
#             f"MPC_A_03_PORT":f"192.168.{target.cell}.12:7005",
#             f"MPC_A_04_PORT":f"192.168.{target.cell}.12:7006",
#             f"MPC_A_05_PORT":f"192.168.{target.cell}.12:7007",
#             f"MPC_A_06_PORT":f"192.168.{target.cell}.12:7008",
#             f"MPC_A_07_PORT":f"192.168.{target.cell}.12:7009",
#             f"MPC_A_08_PORT":f"192.168.{target.cell}.12:7010"}

# target.gaugeConfig = {"GAUGE_S_01":{"slot":"A","vlvcc":"1","mksType":"b"},
#                "GAUGE_S_02":{"slot":"B","vlvcc":"1","mksType":"b"},
#                "GAUGE_A_01":{"slot":"A","vlvcc":"1","mksType":"b"},
#                "GAUGE_A_02":{"slot":"B","vlvcc":"1","mksType":"b"},
#                "GAUGE_A_03":{"slot":"B","vlvcc":"2","mksType":"b"},
#                "GAUGE_A_31":{"slot":"A","vlvcc":"2","mksType":"b"},
#                "GAUGE_A_04":{"slot":"B","vlvcc":"2","mksType":"b"}}

srVacuumCells = CellCollection()
target = srVacuumCells.cells[7]
useSrVacCommon = True


    # Define unwanted tags
firstBatchUnwanted = ["mrfTiming.EventReceiverPMC",
                    "ipac.Hy8002",
                    "ipac.Hy8001",
                    "Hy8401ip.Hy8401",
                    "Hy8414.Hy8414",
                    "DLS8515.DLS8515",
                    "FINS.FINSHostlink",
                    "DLS8515.DLS8515channel",
                    "Hy8401ip.auto_Hy8401ip",
                    "dlsPLC.read100",
                    "TimingTemplates.defaultEVR",
                    "SR-VA.auto_psu24vStatus",
                    "rackFan.rackFan",
                    "IOCinfo.IOCinfo",
                    "FINS.FINSTemplate",
                    "EPICS_BASE.EpicsEnvSet",
                    "EPICS_BASE.StartupCommand"]


with open(target.inputFileName, "r") as file:
    input_xml = file.read()


converted_xml = remove_unwanted_tags(input_xml,firstBatchUnwanted)
converted_xml = substitueAsynPorts(converted_xml)
converted_xml = add_plc_ports(converted_xml,"asyn.AsynIP")
converted_xml = add_NX102_readReal(converted_xml,after="FINS.FINSUDPInit")
converted_xml = convertFastVacuum(converted_xml)
converted_xml = remove_unwanted_tags(converted_xml,["FastVacuum.Master16","FastVacuum.auto_Channel16","FastVacuum.auto_ChannelUn"])
converted_xml = convertValves(converted_xml,after="dlsPLC.vacValveDebounce")
converted_xml = remove_unwanted_tags(converted_xml,["dlsPLC.vacValveDebounce"])

for gauge in target.gaugeConfig:
    converted_xml = addMks937abCombGauge(converted_xml,gauge,target.gaugeConfig[gauge]["mksType"])

converted_xml = remove_unwanted_tags(converted_xml,["mks937a.mks937aGauge"])
converted_xml = addMPCInterlocks(converted_xml)

converted_xml = addExtraGaugeControllers(converted_xml)
convertAllmks = True
for gauge in target.gaugeConfig:
    if target.gaugeConfig[gauge]["mksType"] == "a":
       convertAllmks = False

converted_xml = converted_xml.replace('937a','937b')
converted_xml = remove_unwanted_tags(converted_xml,["autosave.Autosave"])
converted_xml = updateAutosave(converted_xml)
converted_xml = addMks937bAddress(converted_xml)

if not useSrVacCommon:
    converted_xml = addPVLogging(converted_xml)
    converted_xml = addRgaPowerCycle(converted_xml)
    converted_xml = addControllerStatus(converted_xml)
    converted_xml = addTerminalServer(converted_xml)
    converted_xml = addPLCIO(converted_xml)
    converted_xml = addEpicsEnvs(converted_xml)

converted_xml = remove_unwanted_tags(converted_xml,["asyn.AsynIP"])
converted_xml = sortAsynPort(converted_xml)

if useSrVacCommon:
    converted_xml = remove_unwanted_tags(converted_xml,["autosave.Autosave","devIocStats.devIocStatsHelper"])
    converted_xml = addSrVacCommon(converted_xml)

converted_xml = converted_xml.replace("vxWorks-ppc604_long","linux-x86_64")
with open(target.outputFilename, "w") as file:
    file.write(converted_xml)



print(f"Converted XML saved to {target.outputFilename}")

src = target.outputFilename
dstFileName=src.replace('_converted','')
dst = f"/dls_sw/work/R3.14.12.7/support/SR-BUILDER/etc/makeIocs/{os.path.basename(dstFileName)}"
repo_dir = "/dls_sw/work/R3.14.12.7/support/SR-BUILDER"

relative_path = os.path.relpath(dst, repo_dir)

# Check for uncommitted changes in the file
result = subprocess.run(
    ["git", "status", "--porcelain", "--", relative_path],
    cwd=repo_dir,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

if result.stdout.strip():
    print(f"Warning: {relative_path} has uncommitted changes in the repo.")
else:
    shutil.copy(src, dst)
    print(f"Copied {src} to {dst}")

#shutil.copy(target.outputFilename, f"/dls_sw/work/R3.14.12.7/support/SR-BUILDER/etc/makeIocs/{target.outputFilename}")
# add req_prefix=f"SR{target.cell:02d}C" and db_suffix=":SR" to autosave