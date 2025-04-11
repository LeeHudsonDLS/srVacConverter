import xml.etree.ElementTree as ET

def insertElementList(root,elementList, after=None):

    position = -1
    if after is not None:
        position = find_last_element_index(root,after)

    for elem in reversed(elementList):
        if position > 0:
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
        elem.set("port", f"192.168.{cell}.")

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
    eip_element.set("device",f"SR{cell:02d}C-VA-VLVCC-01")
    eip_element.set("ip",f"192.168.{cell}.10")
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
        vc = gaugeConfig[name]["vlvcc"]
        slot = gaugeConfig[name]["slot"]
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

    fvMaster = ET.Element("dlsPLC.fastVacuumMaster",dom=f"SR{cell:02d}C",eip_port="VLVCC_01_EIP",fins_port="VLVCC_01_FINS",name="FV.MASTER")

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

    dom = f"SR{cell:02d}{gauge.split("_")[1]}"
    id = f"{int(gauge.split("_")[-1]):01d}"
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

    envList.append(ET.Element("EPICS_BASE.EpicsEnvSet",key="IOCSH_PS1",value=f"SR{cell:02d}C-VA-IOC-01 -&gt;"))
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
        if f"{mpc.split("_")[1]}" == "S":
            straightIonps.append(elem.get("device"))
        else:
            arcIonps.append(elem.get("device"))

    for ionp in straightIonps:
        elementList.append(ET.Element("dlsPLC.NX102_interlock",device=f"{ionp}:MPS_ILK",interlock="",port="VLVCC_01_EIP",tag="MPC",tagidx="1"))

    for ionp in arcIonps:
        elementList.append(ET.Element("dlsPLC.NX102_interlock",device=f"{ionp}:MPS_ILK",interlock="",port="VLVCC_01_EIP",tag="MPC",tagidx="2"))


    root = insertElementList(root,elementList,after="dlsPLC.NX102_readReal")


    return addXMLBoilerPlate(root)
    
def addPLCIO(input_xml):
    tree = ET.ElementTree(ET.fromstring(input_xml))
    root = tree.getroot()

    elementList = list()
    elementList.append(ET.Element("dlsPLC.NX102_digitalIn",device=f"SR{cell:02d}C-VA-VLVCC-01:DIGITAL01",name="DIG_01",port="VLVCC_01_EIP",tagidx="1"))
    elementList.append(ET.Element("dlsPLC.NX102_digitalIn",device=f"SR{cell:02d}C-VA-VLVCC-01:DIGITAL02",name="DIG_02",port="VLVCC_01_EIP",tagidx="2"))

    elementList.append(ET.Element("userIO.bi ",DESC="Rack 01 Fan Status",DTYP="Soft Channel",INP=f"SR{cell:02d}C-VA-VLVCC-01:DIGITAL01:RAWBIT.B0 CP",ONAM="HEALTHY",OSV="NO_ALARM",P="SR05C-VA-FANC-01",R=":STA",SCAN="Passive",ZNAM="FAIL",ZSV="MAJOR",archiver_rate="3600 Monitor", name="VAFAN_01"))
    elementList.append(ET.Element("userIO.bi ",DESC="Rack 02 Fan Status",DTYP="Soft Channel",INP=f"SR{cell:02d}C-VA-VLVCC-01:DIGITAL01:RAWBIT.B1 CP",ONAM="HEALTHY",OSV="NO_ALARM",P="SR05C-VA-FANC-02",R=":STA",SCAN="Passive",ZNAM="FAIL",ZSV="MAJOR",archiver_rate="3600 Monitor", name="VAFAN_02"))
    elementList.append(ET.Element("userIO.bi ",DESC="Rack 03 Fan Status",DTYP="Soft Channel",INP=f"SR{cell:02d}C-VA-VLVCC-01:DIGITAL01:RAWBIT.B2 CP",ONAM="HEALTHY",OSV="NO_ALARM",P="SR05C-VA-FANC-03",R=":STA",SCAN="Passive",ZNAM="FAIL",ZSV="MAJOR",archiver_rate="3600 Monitor", name="VAFAN_03"))
    elementList.append(ET.Element("userIO.bi ",DESC="Rack 01 Duplex PSU Status",DTYP="Soft Channel",INP=f"SR{cell:02d}C-VA-VLVCC-01:DIGITAL01:RAWBIT.B3 CP",ONAM="HEALTHY",OSV="NO_ALARM",P="SR05C-VA-PSU-01",R=":STA",SCAN="Passive",ZNAM="FAIL",ZSV="MAJOR",archiver_rate="3600 Monitor", name="VAPSU_01"))
    elementList.append(ET.Element("userIO.bi ",DESC="Rack 02 Duplex PSU Status",DTYP="Soft Channel",INP=f"SR{cell:02d}C-VA-VLVCC-01:DIGITAL01:RAWBIT.B4 CP",ONAM="HEALTHY",OSV="NO_ALARM",P="SR05C-VA-PSU-02",R=":STA",SCAN="Passive",ZNAM="FAIL",ZSV="MAJOR",archiver_rate="3600 Monitor", name="VAPSU_02"))

    elementList.append(ET.Element("dlsPLC.NX102_powerSupply",device=f"SR{cell:02d}C-VA-PSU-01:1",name="PSU01.1",port="VLVCC_01_EIP",tagidx="1"))
    elementList.append(ET.Element("dlsPLC.NX102_powerSupply",device=f"SR{cell:02d}C-VA-PSU-01:2",name="PSU01.2",port="VLVCC_01_EIP",tagidx="2"))
    elementList.append(ET.Element("dlsPLC.NX102_powerSupply",device=f"SR{cell:02d}C-VA-PSU-02:1",name="PSU02.1",port="VLVCC_01_EIP",tagidx="3"))
    elementList.append(ET.Element("dlsPLC.NX102_powerSupply",device=f"SR{cell:02d}C-VA-PSU-02:2",name="PSU02.2",port="VLVCC_01_EIP",tagidx="4"))

    elementList.append(ET.Element("dlsPLC.NX102_IRVacuum",P=f"SR{cell:02d}-VA-VALVE-01",port="VLVCC_01_EIP"))


    root = insertElementList(root,elementList, after = "mks937a.auto_mks937aImgMean")

    return addXMLBoilerPlate(root)




# Example usage
input_filename = "SR06C-VA-IOC-01.xml"
output_filename = input_filename.replace(".xml", "_converted.xml")
cell = 6
gaugeConfig = {"GAUGE_S_01":{"slot":"A","vlvcc":"1","mksType":"b"},
               "GAUGE_S_02":{"slot":"B","vlvcc":"1","mksType":"b"},
               "GAUGE_A_01":{"slot":"A","vlvcc":"1","mksType":"b"},
               "GAUGE_A_02":{"slot":"B","vlvcc":"1","mksType":"b"},
               "GAUGE_A_03":{"slot":"B","vlvcc":"2","mksType":"b"},
               "GAUGE_A_31":{"slot":"A","vlvcc":"2","mksType":"b"},
               "GAUGE_A_04":{"slot":"B","vlvcc":"2","mksType":"b"}}

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


with open(input_filename, "r") as file:
    input_xml = file.read()


converted_xml = remove_unwanted_tags(input_xml,firstBatchUnwanted)
converted_xml = substitueAsynPorts(converted_xml)
converted_xml = add_plc_ports(converted_xml,"asyn.AsynIP")
converted_xml = add_NX102_readReal(converted_xml,after="FINS.FINSUDPInit")
converted_xml = convertFastVacuum(converted_xml)
converted_xml = remove_unwanted_tags(converted_xml,["FastVacuum.Master16","FastVacuum.auto_Channel16","FastVacuum.auto_ChannelUn"])
converted_xml = convertValves(converted_xml,after="dlsPLC.vacValveDebounce")
converted_xml = remove_unwanted_tags(converted_xml,["dlsPLC.vacValveDebounce"])

for gauge in gaugeConfig:
    converted_xml = addMks937abCombGauge(converted_xml,gauge,gaugeConfig[gauge]["mksType"])



converted_xml = remove_unwanted_tags(converted_xml,["mks937a.mks937aGauge"])
converted_xml = addEpicsEnvs(converted_xml)
converted_xml = addMPCInterlocks(converted_xml)
converted_xml = addPLCIO(converted_xml)

convertAllmks = True
for gauge in gaugeConfig:
    if gaugeConfig[gauge]["mksType"] == "a":
       convertAllmks = False

converted_xml = converted_xml.replace('937a','937b')
 

with open(output_filename, "w") as file:
    file.write(converted_xml)

print(f"Converted XML saved to {output_filename}")
