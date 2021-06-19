import os
import sys
import json
import urllib2
import time
import re
import subprocess
import socket
import websocket

hostname= socket.gethostname()
IPAddr = subprocess.Popen(["hostname", "-I"],stdout=subprocess.PIPE).communicate()[0].rstrip()

lineCount = 18
processList=["BURNING","SHEARING","SAWING","BRAKE","PUNCH","DRILL"]

#COLORS
NC="\033[0;37;40m"
BLINK="\033[6m"
#foreground
fRED="\033[0;31;40m"
fGREEN="\033[0;32;40m"
fYELLOW="\033[0;33;40m"
fBLUE="\033[0;34;40m"
fPURPLE="\033[0;35;40m"
fCYAN="\033[0;36;40m"
fWHITE="\033[0;37;40m"
#background
bGREEN_BLACK="\033[0;30;42m"  #green bg/black fg
bYELLOW_BLACK="\033[0;30;43m"
bPURPLE_BLACK="\033[0;30;45m"
bRED_WHITE="\033[0;37;41m"    #red bg / white fg

bWHITE_BLACK="\033[0;30;47m"
bWHITE_RED="\033[0;31;47m"
bWHITE_BLUE="\033[0;34;47m"


class Order:
  def __init__(self,orderNum,custName,po,salesRep,dateDue,lines):
    self.order_num=orderNum
    self.customer_name=custName
    self.po=po
    self.sales_rep=salesRep
    self.date_due=dateDue
    self.lines=lines

  def getOrderColor(self):
    statusList=[]
    for x in range(len(self.lines)):
      if self.lines[x]["process_status"] == "Stopped":
	statusList.append(self.lines[x]["process_status"])
      elif self.lines[x]["process_status"] == "Running":
	statusList.append(self.lines[x]['process_status'])
      else:
        pass
    if "Running" in statusList:
      return bGREEN_BLACK
    elif "Stopped" in statusList:
      return bRED_WHITE
    else:
      return ""


#---------------------------------------------- RELOAD ORDERS ----------------------------------------------------------
def reloadOrders():
  #if hostname == "debian-server":
  #  process="burning"

  url = "http://198.255.132.49/WIP/API/getOpenOrders.php?process="+process.lower()

  try:
    response = urllib2.urlopen(url)
    data = response.read()
    orders = json.loads(data)

    orderList=[]

    for x in orders:
      x["order_num"]=Order(x["order_num"],x["customer_name"],x["po"],x["sales_rep"],x["date_due"],x["lines"])
      orderList.append(x['order_num'])

    return orderList
    #return process,orderList
  except:
    print bRED_WHITE+"--!!!-- THERE WAS AN ERROR LOADING ORDERS! --!!!--"+NC
    time.sleep(3)
    orderSelect(False)


#---------------------------------------------------- SCREEN PAGES ----------------------------------------------------
def screenPages(linesPerPage,itemList):
  screenDict = {}
  pageItemList=[]

  listData = divmod(len(itemList),linesPerPage)
  pageCount = listData[0]

  for x in range(pageCount):
    for y in range(linesPerPage):
      pageItemList.append(itemList[(x*linesPerPage)+y])
    screenDict[str(x)] = pageItemList
    pageItemList = []

  if listData[1] > 0:
    for i in range(listData[1]):
      pageItemList.append(itemList[(pageCount*linesPerPage)+i])
    screenDict[str(len(screenDict))] = pageItemList

  return screenDict,listData



#------------------------------------------------------ FIND INDEX ---------------------------------------------------------
def findIndex(lst, key, value):
    for i, dic in enumerate(lst):
        if dic[key] == value:
            return i
	else:
          return -1


#------------------------------------------------------- UPDATE DATABASE -------------------------------------------------
def updateDB(rowid,status,lineNum):
  url = "http://198.255.132.49/WIP/update_db.php"

  if status == "Running":
    data_status = "resume_job"
    color = bGREEN_BLACK
  if status == "Stopped":
    data_status = "stop_job"
    color = bRED_WHITE
  if status == "Complete":
    data_status = "complete_job"
    color = bPURPLE_BLACK

  data = json.dumps({rowid:send_status})
  req = urllib2.Request(url,data,{"Content-Type": "application/json"})

  response = urllib2.urlopen(req)
  if response.getcode() == 200:
    ws = websocket.create_connection("ws://198.255.132.49:8000")
    ws.send(str(rowid)+","+data_status)
    ws.close()

    print bWHITE_BLUE+"OK - Line Number "+str(lineNum)+ " is now "+ NC + color + status+"!!"+NC
  else:
    print bRED_WHITE+"--!!!-- THERE WAS AN ERROR UPDATING THE DATABASE! --!!!--"+NC

  time.sleep(2)
  orderSelect(True)

#--------------------------------------------------------------- SCREENS ------------------------------------------------------------------------

#==================================================== STATUS SELECTION SCEEEN ===========================================================
def statusSelect(order,lineDetail):

  os.system("clear")
  if lineDetail["process_status"] == "Not Started":
    options=[bGREEN_BLACK+"Start Line"+NC]
    optClean=["Running"]
  elif lineDetail["process_status"] == "Running":
    options=[bRED_WHITE+"Stop Line"+NC,bPURPLE_BLACK+"Complete Line"+NC]
    optClean=["Stopped","Complete"]
  elif lineDetail["process_status"] == "Stopped":
    options=[bGREEN_BLACK+"Resume Line"+NC,bPURPLE_BLACK+"Complete Line"+NC]
    optClean=["Running","Complete"]

  line1=" "+order.customer_name+ " - " +str(order.order_num)+" "
  line2=" LINE#: "+str(lineDetail['line_number'])+" "
  line3=str(lineDetail["quantity"])+" "+lineDetail["uom"]+" - "+lineDetail["description"]+" @ "+str(lineDetail["width"])+" x "+str(lineDetail["length"])

  print IPAddr.rjust(80," ")
  print bWHITE_BLUE+line1.center(80)[:80]
  print line2.center(80)[:80]
  print line3.center(80)[:80]+NC
  print " "
  print "============================== "+fYELLOW+"UPDATE LINE STATUS"+NC+" =============================="
  print " "

  for x in range(len(options)):
    print str(x+1)+": "+options[x]

  print " "
  print "--| OPTIONS: |------------------------------------------------------------------"
  print fYELLOW+"*: RETURN TO ORDER SELECT"+NC
  print fYELLOW+"+: RETURN TO LINE SELECT"+NC
  print "=".center(80,"=")
  print " "

  try:
    selection=raw_input("ENTER SELECTION:")

    if len(selection) > 1:
      raise IndexError
    try:
      selection = re.findall(r"\d|\W",selection)
      if not selection:
        raise Exception("INVALID CHOICE")
      else:
        if selection[0] == "+":
          lineSelect(order)
        elif selection[0] == "*":
          orderSelect(False)
        elif selection[0] == "-":
          raise Exception("INVALID CHOICE")
          statusSelect(order,lineDetail)
        elif selection[0] == ".":
          raise Exception("INVALID CHOICE")
	  statusSelect(order,lineDetail)
        elif selection[0] == "/":
          raise Exception("INVALID CHOICE")
          statusSelect(order,lineDetail)
        else:
	  updateDB(lineDetail["row_id"],optClean[int(selection[0])-1],lineDetail["line_number"])
    except:
      error = sys.exc_info()
      os.system("clear")
      print error
      time.sleep(3)
      statusSelect(order,lineDetail)

  except IndexError:
    os.system("clear")
    selection=""
    print bRED_WHITE+"--!!!-- INVALID LINE CHOICE!! TRY AGAIN  --!!!--"+NC
    time.sleep(3)
    statusSelect(order,lineDetail)
  except KeyboardInterrupt:
    print "keyboard error"
    sys.exit()
  except:
    error = sys.exc_info()
    os.system("clear")
    print error
    print bRED_WHITE+"--!!!-- INVALID INPUT --!!!--                                                orderSelect"+NC
    time.sleep(3)
    orderSelect(False)


#============================================== LINE SELECTION SCREEN ==================================================================
def lineSelect(order):
  currentPage = 0
  os.system("clear")

  lines = screenPages(lineCount,order.lines)

  def paintLineSelectScreen(ord,orderLines,currentPage):
    os.system("clear")
    customerAndOrderNum = ord.customer_name+" "+str(ord.order_num)

    print IPAddr.rjust(80," ")
    print bWHITE_BLUE+customerAndOrderNum.center(80)+NC
    print " ".center(80)
    print "=================================="+fYELLOW+ " LINE SELECT "+NC+ "================================="
    print """LN #|  QTY  | UOM |       DESCRIPTION          | WIDTH  | LENGTH  |    STATUS   """
    print """====|=======|=====|============================|========|=========|============="""

    for line in orderLines[str(currentPage)]:
      lineBackgroundColor=""
      if line["process_status"] == "Not Started":
        status=fCYAN+"Not Started "
      elif line["process_status"] == "Stopped":
        status="Stopped     "
        lineBackgroundColor=bRED_WHITE
      elif line["process_status"]=="Running":
        status="Running     "
        lineBackgroundColor=bGREEN_BLACK

      print lineBackgroundColor+" "+str(line["line_number"]).ljust(3)+"| "+str(line["quantity"]).ljust(6)+"| "+str(line["uom"]).ljust(4)+"| "+str(line["description"])[:27].ljust(27)+"| "+str(line["width"]).ljust(7)+"| "+str(line["length"]).ljust(8)+"| "+status+NC

    print "=".center(80,"=")
    print " "
    pageNum = " "+bWHITE_BLUE+"PAGE {}".format(currentPage+1)+NC+" "
    print str(pageNum).center(100," ")
    print " "
    print "--| OPTIONS: |------------------------------------------------------------------"
    print fYELLOW+"*: RETURN TO ORDER SELECT"+NC

    while len(orderLines) > 1:
      if currentPage > 0:
        print fYELLOW+"+: ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ + "+bYELLOW_BLACK+" PAGE UP "+fYELLOW+" + ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^"+NC
      if currentPage in range(0,len(orderLines)-1):
        print fYELLOW+"-: vvvvvvvvvvvvvvvvvvvvvvvvvvvvv - "+bYELLOW_BLACK+"PAGE DOWN"+fYELLOW+" - vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv"+NC
      break

    print "=".center(80,"=")
    print " "

    try:
      selection=raw_input("ENTER SELECTION:")

      if len(selection) > 3:
        raise IndexError
      if len(selection) <= 3:
        if len(selection) == 1:
          try:
            selection = re.findall(r"\d|\W",selection)
            if not selection:
              raise Exception("INVALID CHOICE")
            else:
              if selection[0] == "-":
                currentPage += 1
                paintLineSelectScreen(ord,lines[0],currentPage)
              elif selection[0] == "+":
                currentPage -= 1
                paintLineSelectScreen(ord,lines[0],currentPage)
              elif selection[0] == "*":
                currentPage=0
                os.system("clear")
                orderSelect(False)
              elif selection[0] == ".":
                raise Exception("INVALID CHOICE")
                paintLineSelectScreen(ord,lines[0],currentPage)
              elif selection[0] == "/":
                raise Exception("INVALID CHOICE")
                paintLineSelectScreen(ord,lines[0],currentPage)
              else:
	 	pagedIndex = findIndex(orderLines[str(currentPage)],"line_number",int(selection[0]))
		if pagedIndex == -1:
		  raise Exception("INVALID CHOICE")
                statusSelect(ord,orderLines[str(currentPage)][pagedIndex])
          except:
            error = sys.exc_info()
            os.system("clear")
            print error
            time.sleep(3)
            paintLineSelectScreen(ord,lines[0],currentPage)
        else:
          try:
            selection = re.findall(r"^\d{1,3}|^\W{1}",selection)
            if not selection:
              raise Exception("INVALID CHOICE")
            pagedIndex = findIndex(orderLines[str(currentPage)],"line_number",int(selection[0]))
            if pagedIndex == -1:
              raise Exception("INVALID CHOICE")
            statusSelect(ord,orderLines[str(currentPage)][pagedIndex])
          except:
            error = sys.exc_info()
            os.system("clear")
            print error
            time.sleep(3)
            paintLineSelectScreen(ord,lines[0],currentPage)

    except IndexError:
      os.system("clear")
      selection=""
      print bRED_WHITE+"--!!!-- INVALID LINE CHOICE!! TRY AGAIN  --!!!--"+NC
      time.sleep(3)
      paintLineSelectScreen(ord,lines[0],currentPage)
    except KeyboardInterrupt:
      print "keyboard error"
      sys.exit()
    except:
      error = sys.exc_info()
      os.system("clear")
      print error
      print bRED_WHITE+"--!!!-- INVALID INPUT --!!!--                                                orderSelect"+NC
      time.sleep(3)
      lineSelect(ord)


  paintLineSelectScreen(order,lines[0],currentPage)

#=================================== ORDER SELECTION SCREEN ===============================================================
def orderSelect(reload=False):
  global orderList
  global process
  currentPage = 0

  if reload == True:
    orderList = reloadOrders()
    #reloadData = reloadOrders()
    #orderList = reloadData[1]
    #process = reloadData[0].upper()

  pages = screenPages(lineCount,orderList)

  def paintOrderSelectScreen(pages,currentPage):

    os.system("clear")
    pageList = pages[0]
    listData = pages[1]

    print IPAddr.rjust(80," ")
    processHeader = " "+bWHITE_BLACK+" "+process+" "+NC+" "
    print processHeader.center(98," ")
    screenHeader = fYELLOW+" ORDER SELECT "+NC
    print screenHeader.center(100,"=")
    print """# | ORDER #|         CUSTOMER           |     PO      |  SALES REP  | DATE DUE  """
    print   "==|========|============================|=============|=============|==========="

    for order in pageList[str(currentPage)]:
      if listData[1] > 0 and currentPage > listData[0]:
        orderIndex = (currentPage-1)*lineCount + pageList[str(currentPage)].index(order)
      else:
        orderIndex = currentPage*lineCount + pageList[str(currentPage)].index(order)
        orderColor = order.getOrderColor()
      print orderColor+str(orderIndex+1).ljust(2)+"| "+str(order.order_num).ljust(7)+"|"+order.customer_name[:28].ljust(28)+"|"+str(order.po)[:13].ljust(13)+"|"+str(order.sales_rep)[:13].ljust(13)+"| "+str(order.date_due).ljust(10)+NC
    print "=".center(80,"=")
    print " "
    pageNum = " "+bWHITE_BLUE+"PAGE {}".format(currentPage+1)+NC+" "
    print str(pageNum).center(100,' ')
    print " "
    print "--| OPTIONS: |------------------------------------------------------------------"
    print fYELLOW+"*: RETURN TO PROCESS SELECT"+NC

    while len(pageList) > 1:
      if currentPage > 0:
        print fYELLOW+"+: ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ + "+bYELLOW_BLACK+" PAGE UP "+fYELLOW+" + ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^"+NC
      if currentPage in range(0,len(pageList)-1):
        print fYELLOW+"-: vvvvvvvvvvvvvvvvvvvvvvvvvvvvv - "+bYELLOW_BLACK+"PAGE DOWN"+fYELLOW+" - vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv"+NC
      break

    print "=".center(80,"=")+"\n"


    try:
      selection=raw_input("ENTER SELECTION:")

      if len(selection) > 3:
	raise IndexError
      if len(selection) <= 3:
	if len(selection) == 1:
          try:
            selection = re.findall(r"\d|\W",selection)
            if not selection:
	      raise Exception("INVALID CHOICE")
	    else:
              if selection[0] == "-":
      	        currentPage += 1
                paintOrderSelectScreen(pages,currentPage)
              elif selection[0] == "+":
                currentPage -= 1
                paintOrderSelectScreen(pages,currentPage)
              elif selection[0] == "*":
		currentPage=0
		os.system("clear")
                processSelect()
	      elif selection[0] == ".":
		raise Exception("INVALID CHOICE")
		paintOrderSelectScreen(pages,currentPage)
              elif selection[0] == '/':
                raise Exception("INVALID CHOICE")
                paintOrderSelectScreen(pages,currentPage)
	      else:
		pagedIndex = (int(selection[0])-(currentPage*lineCount))-1
		lineSelect(pageList[str(currentPage)][pagedIndex])
          except:
            error = sys.exc_info()
            os.system("clear")
            print error
            time.sleep(3)
            paintOrderSelectScreen(pages,currentPage)
	else:
	  try:
	    selection = re.findall(r"^\d{1,3}|^\W{1}",selection)
	    if not selection:
	      raise Exception("INVALID CHOICE")
	    pagedIndex = (int(selection[0])-(currentPage*lineCount))-1
            lineSelect(pageList[str(currentPage)][pagedIndex])
	  except:
            error = sys.exc_info()
            os.system("clear")
            print error
	    time.sleep(3)
	    paintOrderSelectScreen(pages,currentPage) 


    except IndexError:
      os.system("clear")
      selection=""
      print bRED_WHITE+"--!!!-- INVALID ORDER CHOICE!! TRY AGAIN  --!!!--"+NC
      time.sleep(3)
      paintOrderSelectScreen(pages,currentPage)
    except KeyboardInterrupt:
      print "keyboard error"
      sys.exit()
    except:
      error = sys.exc_info()
      os.system("clear")
      print error
      print bRED_WHITE+"--!!!-- INVALID INPUT --!!!--                                                orderSelect"+NC
      time.sleep(3)
      orderSelect(False)



  paintOrderSelectScreen(pages,currentPage)

#==================================== PROCESS SELECT SCREEN ======================================================================
def processSelect():
  global process
  hostAndIp = hostname + "@" + IPAddr
  print hostAndIp.rjust(80," ")
  print "=".center(80,"=")
  print fYELLOW+"                             SELECT PROCESS                                    "+NC
  print "-".center(80,"-")

  for x in range(len(processList)):
    print fYELLOW+str(x+1)+": "+NC+processList[x]

  print "=".center(80,"=")+"\n"

  try:
    processSelection=raw_input("ENTER SELECTION:")

    if set(processSelection).issubset(["/",".","-","+","*"]) or len(processSelection) > 1:
      raise IndexError
    else:
      processSelection = int(processSelection)-1

    if processSelection < 0 or processSelection >= 6:
      raise IndexError
    else:
      process=processList[processSelection]

  except IndexError:
    os.system("clear")
    process=""
    print bRED_WHITE+"--!!!-- INVALID PROCESS CHOICE!! TRY AGAIN --!!!--"+NC
    time.sleep(3)
    os.system("clear")
    processSelect()
  except KeyboardInterrupt:
    sys.exit()
  except:
    error = sys.exc_info()
    os.system("clear")
    print error

  orderSelect(True)


#==================================== SPLASH SCREEN ======================================================================
def splash():
  os.system("clear")
  print fCYAN+"            ____   _    ____ _____ __  __    _    _  _______ ____  "
  print """           |  _ \ / \  / ___| ____|  \/  |  / \  | |/ / ____|  _ \ """
  print """           | |_) / ^ \| |   |  _| | |\/| | / ^ \ | ' /|  _| | |_) |"""
  print """           |  __/ _-_ \ |___| |___| |  | |/ _-_ \| . \| |___|  _ < """
  print "           |_| /_/   \_\____|_____|_|  |_/_/   \_\\"+"_|\_\_____|_| \_\\"
  print "                        ____ _____ _____ _____ _     "
  print "                       / ___|_   _| ____| ____| |    "
  print "                       \___ \ | | |  _| |  _| | |    "
  print "                        ___) || | | |___| |___| |___ "
  print "                       |____/ |_| |_____|_____|_____|"
  print fYELLOW+"\n\n\n                                                      labor tracking v1.0"
  print "                                                      written by: John Perestam"+NC

  time.sleep(3)

#------------------------------------------------------------------------------------------------------------------------




#----- START PROGRAM ------
splash()
#orderSelect(True)
processSelect()

