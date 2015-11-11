import urllib2
import json
import time
import threading
import re
from flask import Flask
from flask import render_template,request

app=Flask(__name__)

class AutoSqli(object):
    def __init__(self,serverURL,serverPort):
        self.serverURL=serverURL
        self.serverPort=serverPort
        self.taskid_url_Dict={}
        self.taskid_log_Dict={}
        self.taskid_status_Dict={}
        self.taskid_threads_Dict={}
        self.taskid_data_Dict={}
        self.taskid_options_Dict={}
    def NewTask(self,targetURL):
        m=re.match('(http://)|(https://)',targetURL)
        if m is None:
            targetURL="http://"+targetURL        
        repeated=self.URL_Dedu(targetURL)
        if repeated != 1:
            return "False"
        request=urllib2.Request(self.serverURL+":"+self.serverPort+
                                "/task/new")
        response=urllib2.urlopen(request)
        responseData=json.loads(response.read())
        if(responseData['success']==True):
            taskid=responseData['taskid']
            self.taskid_log_Dict[taskid]=time.strftime("[*%H:%M:%S]")+\
                "Built a new task successfully,taskid is %s;<br>"\
                % (taskid)
            self.taskid_url_Dict[taskid]="empty"
            self.taskid_status_Dict[taskid]="waiting targetUrl"
            self.SetOptions(taskid,{"getDbs":True})
            url=self.serverURL+":"+self.serverPort+"/scan/"+taskid+"/start"
            request=urllib2.Request(url,'{"url":"'+targetURL+'"}')
            request.add_header("Content-Type","application/json")
            response=urllib2.urlopen(request)
            responseData=json.loads(response.read())
            if(responseData['success']==True):
                self.taskid_url_Dict[taskid]=targetURL
                self.taskid_log_Dict[taskid]=self.taskid_log_Dict[taskid]+\
                    time.strftime("[*%H:%M:%S]")+\
                    "Started a new scan of %s sucessfully!The engineid is %s;<br>"\
                    % (targetURL,responseData['engineid'])
                self.taskid_status_Dict[taskid]="scanning"
                self.taskid_threads_Dict[taskid]=threading.Thread(target=self.Thread_Handle,\
                                                                  args=(taskid,))
                self.taskid_threads_Dict[taskid].start()
                return "True"
            else:
                self.DeleteTask(taskid)
                del self.taskid_url_Dict[taskid]
                del self.taskid_log_Dict[taskid]
                del self.taskid_status_Dict[taskid]
                return "False"
        else:
            return "False"
    def Thread_Handle(self,taskid):#must use statusr
        request_status=urllib2.Request(self.serverURL+":"+self.serverPort+
                                "/scan/"+taskid+"/status")
        request_log=urllib2.Request(self.serverURL+":"+self.serverPort+
                                "/scan/"+taskid+"/log")
        request_data=urllib2.Request(self.serverURL+":"+self.serverPort+
                                "/scan/"+taskid+"/data")
        response_status=urllib2.urlopen(request_status)                   #----|
        response_status_data=json.loads(response_status.read())           #    |
        self.taskid_status_Dict[taskid]=response_status_data['status']    #----|   
        while response_status_data['status']!="terminated":
            if self.taskid_status_Dict[taskid]=="deleted":
                return False
            time.sleep(2)
            response_status=urllib2.urlopen(request_status)               #----|
            response_status_data=json.loads(response_status.read())       #    |
            self.taskid_status_Dict[taskid]=response_status_data['status']#----|  
            response_log=urllib2.urlopen(request_log)
            response_log_data=json.loads(response_log.read()) 
            loglist=response_log_data["log"]
            for log in loglist:
                self.taskid_log_Dict[taskid]=self.taskid_log_Dict[taskid]+\
                    "[*"+log["time"]+"]"+log["message"]+";<br>"            
        self.taskid_status_Dict['status']="terminated"
        #convert data['value] to a html table element,too many ugly code......
        response_data=urllib2.urlopen(request_data)
        response_data=response_data.read()
        response_data=json.loads(response_data)
        response_data=response_data['data']
        response_data=response_data[0]
        response_data=response_data["value"][0]
        html_table1=""
        html_table2=""
        for key in response_data:
            if key !="conf" and key!="data":
                response_data[key]=str(response_data[key])
        html_table1='<table width="200" border="1" id="table1">'+\
            '<caption>Conventional data</caption><tr><td>DBMS</td><td colspan="2">'+response_data["dbms"]+'</td></tr>'+\
            '<tr><td>Suffix</td><td colspan="2">'+response_data["suffix"]+'</td></tr><tr><td>Clause</td>'+\
            '<td colspan="2">'+response_data["clause"]+'</td></tr>'+\
            '<tr><td>ptype</td><td colspan="2">'+response_data["ptype"]+'</td></tr>'+\
            '<tr><td>DBMS_Version</td><td colspan="2">'+\
            response_data["dbms_version"]+'</td></tr>'
        for key in response_data["conf"]:
            if not type(response_data["conf"][key]):
                response_data["conf"][key]="empty"
            else:
                response_data["conf"][key]=str(response_data["conf"][key])
        if not type(response_data["os"]):
            response_data["os"]="empty"
        else:
            response_data["os"]=str(response_data["os"])
        html_table1=html_table1+'<tr><td>place</td><td colspan="2">'+response_data["place"]+'</td></tr>'+\
            '<tr><td rowspan="6">conf</td><td>string</td><td>'+response_data["conf"]["string"]+'</td></tr>'+\
            '<tr><td>notString</td><td>'+response_data["conf"]["notString"]+'</td></tr>'+\
            '<tr><td>titles</td><td>'+response_data["conf"]["titles"]+'</td></tr>'+\
            '<tr><td >regexp</td><td >'+response_data["conf"]["regexp"]+'</td></tr>'+\
            '<tr><td >textOnly</td><td >'+response_data["conf"]["textOnly"]+'</td></tr>'+\
            '<tr><td >optimize</td><td >'+response_data["conf"]["optimize"]+'</td></tr>'+\
            '<tr><td>parameter</td><td colspan="2">'+response_data["parameter"]+'</td></tr>'+\
            '<tr><td>OS</td><td colspan="2">'+response_data["os"]+'</td></tr></table>'
        response_data=response_data["data"]
        html_table2='<table width="200" border="1" id="table2">'+\
            '<caption>Payloads Info</caption><tr><th style="width:80px">number</th><th style="width:200px">item</th><th>details</th></tr>'
        for key in response_data:
            for item in response_data[key]:
                if not type(response_data[key][item]):
                    response_data[key][item]="null"
                else:
                    response_data[key][item]=str(response_data[key][item])
            html_table2=html_table2+'<tr><td rowspan="7">'+key+'</td><td>comment</td><td>'+\
                response_data[key]["comment"]+'</td></tr>'+\
                '<tr><td>matchRatio</td><td>'+response_data[key]["matchRatio"]+'</td></tr>'+\
                '<tr><td>title</td><td>'+response_data[key]["title"]+'</td></tr>'+\
                '<tr><td >templatePayload</td><td >'+response_data[key]["templatePayload"]+'</td></tr>'+\
                '<tr><td >vector</td><td >'+response_data[key]["vector"]+'</td></tr>'+\
                '<tr><td >where</td><td >'+response_data[key]["where"]+'</td></tr>'+\
                '<tr><td >payload</td><td >'+response_data[key]["payload"]+'</td></tr>'
        html_table2=html_table2+"</table>"
        self.taskid_data_Dict[taskid]=html_table1+html_table2
    def SetOptions(self,taskid,options={}):
        url=self.serverURL+":"+self.serverPort+"/option/"+taskid+"/set"
        request=urllib2.Request(url,json.dumps(options))
        request.add_header("Content-Type","application/json")
        response=urllib2.urlopen(request)
        responseData=json.loads(response.read())        
    
    def DeleteTask(self,taskid):
        request=urllib2.Request(self.serverURL+":"+self.serverPort+
                                "/task/"+taskid+"/delete")                
        response=urllib2.urlopen(request)
        responseData=json.loads(response.read())
        #there are two status when we wants to delete a task:running and terminated
        #and whatever the status is,we should kill the thread of the task
        #by the way,when a task is running,taskid_data_Dict does not have its taskid in keys()
        if(responseData['success']==True):
            #we should stop thread at first
            if self.taskid_threads_Dict[taskid].isAlive():
                #actually this method is not perfect and can't stop threads set value 100%
                self.taskid_status_Dict[taskid]="deleted"
            del self.taskid_threads_Dict[taskid]
            del self.taskid_log_Dict[taskid]
            if taskid in self.taskid_data_Dict.keys():
                del self.taskid_data_Dict[taskid]
            del self.taskid_status_Dict[taskid]
            del self.taskid_url_Dict[taskid]
            return "True"
        else:
            return "False"
    def SeeTaskList(self):
        task_list=""
        for taskid in self.taskid_url_Dict.keys():
            task_list=task_list+taskid+"-->"+self.taskid_url_Dict[taskid]+"<br>"
        return task_list
    def URL_Dedu(self,targetURL):
        #if not len(self.taskid_url_Dict):
            #return 1
        m=re.match('(http://)|(https://)',targetURL)
        if m is None:
            targetURL="http://"+targetURL
        option_list=[]
        m=re.match('(.+)\?',targetURL)
        if m is None:
            return 0         # return 0 means illegal URL 
        else:
            option_list.append(m.groups()[0])
        temp_list=re.findall('(\&\w+=)',targetURL)
        for i in temp_list:
            if i!="":
                option_list.append(i)
        temp_list=re.findall('(\?\w+=)',targetURL)
        for i in temp_list:
            if i!="":
                option_list.append(i)        
        result=[]
        for key in self.taskid_url_Dict:
            url=self.taskid_url_Dict[key]
            status=True
            for reg in option_list:
                if '&' in reg or '?' in reg:
                    m=re.search('\\'+reg,url)
                else:
                    m=re.search(reg,url)
                if m is None:
                    status=False
                    break
            if status:
                result.append(url)
        if len(result):
            return -1      #return -1 means find url is similar to targeturl
        else:
            return 1       #return 1 means no url is similar to targeturl 
    
#Instantiates the AutoSqli class.    
autosqli=AutoSqli("http://127.0.0.1","8775")

@app.route('/',methods=['GET'])
def handle_root(): 
    return render_template("index.html")

@app.route('/index.html',methods=['GET'])
def handle_index(): 
    return render_template("index.html")

@app.route('/quickbuild.html',methods=['GET'])
def handle_quickbuild():
    return render_template("quickbuild.html")
@app.route('/quickbuild.html',methods=['POST'])
def handle_post_quickbuild():
    if 'url' in request.json:
        log=autosqli.NewTask(request.json['url'])
        return log
    else:
        return "illegal data."
    
@app.route('/customtask.html',methods=['GET'])
def handle_customtask():
    return render_template("customtask.html")

@app.route('/tasklist.html',methods=['GET'])
def handle_tasklist():
    if "action" in request.args and request.args["action"]=="refresh":
        return_html=""
        for taskid in autosqli.taskid_url_Dict:
            return_html=return_html+'<div class="task_box">'+\
                '<p><span><strong>TargetURL:&nbsp;&nbsp;&nbsp;&nbsp;</strong>'+\
                autosqli.taskid_url_Dict[taskid]+\
                '</span></p><p><span><strong>Status:&nbsp;&nbsp;&nbsp;&nbsp;</strong>'+\
                autosqli.taskid_status_Dict[taskid]+'</span></p>'+\
                '<a class="button" href="/tasklog.html?taskid='+taskid+'">'+\
                '<strong>Log</strong></a>'+\
                '<a class="button" href="/taskdata.html?taskid='+taskid+'">'+\
                '<strong>Data</strong></a>'+\
                '<p class="button" onclick="del_task(\''+taskid+'\')">'+\
                '<strong>Delete</strong></p></div>'            
        return return_html
    elif "action" in request.args and request.args["action"]=="delete" \
         and "taskid" in request.args and request.args["taskid"]!="":
        return autosqli.DeleteTask(str(request.args["taskid"]))
    #elif "action" in request.args and request.args["action"]=="seedata"\
         #and "taskid" in request.args and request.args["taskid"]!="":
        #taskid=str(request.args["taskid"])
        #if taskid in autosqli.taskid_data_Dict.keys():
            #return render_template("data.html",data=autosqli.taskid_data_Dict[taskid])
        #else:
            #return render_template("index.html",serversite="http://127.0.0.1:8775")
    elif "action" in request.args and request.args["action"]=="seelog"\
         and "taskid" in request.args and request.args["taskid"]!="":
        taskid=str(request.args["taskid"])
        return autosqli.taskid_log_Dict[taskid];
    else:
        return_html=""
        for taskid in autosqli.taskid_url_Dict:
            return_html=return_html+'<div class="task_box">'+\
                '<p><span><strong>TargetURL:&nbsp;&nbsp;&nbsp;&nbsp;</strong>'+\
                autosqli.taskid_url_Dict[taskid]+\
                '</span></p><p><span><strong>Status:&nbsp;&nbsp;&nbsp;&nbsp;</strong>'+\
                autosqli.taskid_status_Dict[taskid]+'</span></p>'+\
                '<a class="button" href="/tasklog.html?taskid='+taskid+'">'+\
                '<strong>Log</strong></a>'+\
                '<a class="button" href="/taskdata.html?taskid='+taskid+'">'+\
                '<strong>Data</strong></a>'+\
                '<p class="button" onclick="delete(\''+taskid+'\')">'+\
                '<strong>Delete</strong></p></div>'            
        return render_template("tasklist.html",html=return_html)

@app.route('/instructions.html',methods=['GET'])
def handle_instructions():
    return render_template("instructions.html")

@app.route('/tasklog.html',methods=['GET'])
def handle_tasklog():
    if "action" in request.args and request.args["action"]=="refresh"\
       and "taskid" in request.args\
       and request.args["taskid"] in autosqli.taskid_log_Dict.keys():
        taskid=str(request.args["taskid"])
        if autosqli.taskid_status_Dict[taskid]!="terminated":
            return autosqli.taskid_log_Dict[taskid]
        else:
            return "terminated"
    elif "taskid" in request.args and \
       request.args["taskid"] in autosqli.taskid_log_Dict.keys():
        taskid=str(request.args["taskid"])
        return render_template("tasklog.html",Log=autosqli.taskid_log_Dict[taskid],\
                               TaskID=taskid,TargetURL=autosqli.taskid_url_Dict[taskid])
    else:
        return '<script>window.location="/index.html"</script>'
    
@app.route('/taskdata.html',methods=['GET'])
def handle_taskdata():
    return render_template("taskdata.html")

def returnlist():
    return autosqli.SeeTaskList()
    
if __name__=='__main__':
    app.run(host="0.0.0.0",port=80,debug=True)