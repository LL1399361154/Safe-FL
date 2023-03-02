'''
@Date: 2020-07-29 12:01:10
@Description: Do not edit
@LastEditors: Iridium
@LastEditTime: 2020-07-31 11:51:56
@FilePath: \Interfere\main.py
'''
import logging
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import StringProperty
from device import start
from kivy.core.text import LabelBase
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
import sys

# Load Default Config Here
config={  # Global Var
    "believable_ip":"127.0.0.1",
    "believable_port":9990,
    "edge_ip":"127.0.0.1",
    "edge_port":9994
}

cur_path="./"





class ScreenManager(ScreenManager):
    pass

class HomeScreen(Screen):
    pass

class RunScreen(Screen):
    res=StringProperty()
    def __init__(self, **kwargs):
        super(RunScreen, self).__init__(**kwargs)
        self.res="Ready to Run"
        
    def run(self):
        self.believable_ip=config["believable_ip"]
        self.believable_port=config["believable_port"]
        self.edge_ip=config["edge_ip"]
        self.edge_port=config["edge_port"]
        self.res=self.believable_ip+":"+str(self.believable_port)+"\n"+self.edge_ip+":"+str(self.edge_port)


        resultdata=start(config,cur_path)#{TimeSpan,Acc}
        print(resultdata)
        self.res=self.res+"\n"+"Time Span is "+str(resultdata[0])+'\n'+"Accuracy is "+str(resultdata[1])
        return


        
        
        

class ConfigScreen(Screen):
    def __init__(self, **kwargs):
        super(ConfigScreen, self).__init__(**kwargs)

        #self.believableserver=InputWidget()

    def submit(self):
        global config
        print("text is",self.ids.rootip.text)
        rootiplist=self.ids.rootip.text.split(":") # FIXME: Don't input invaild IP!

        config["believable_ip"]=rootiplist[0]
        config["believable_port"]=rootiplist[1]

        edgeiplist=self.ids.edgeip.text.split(":")

        config["edge_ip"]=edgeiplist[0]
        config["edge_port"]=edgeiplist[1]

        print(f"[DEBUG]Changed config is {self.ids.rootip.text} and {self.ids.edgeip.text}")
        return

class InputWidget(BoxLayout):
    pass
class LabelWidget(BoxLayout):
    pass
class Padding(BoxLayout):
    pass 
class ButtonPadding(GridLayout):
    pass
class TestApp(App):
    def build(self):
        return ScreenManager()


if __name__=="__main__":
    if len(sys.argv)>1:
        cur_path=sys.argv[1]

    LabelBase.register(name='reduct',
    fn_regular=cur_path+"reductosskregular.ttf")
    with open(cur_path+"layout.kv", "r", encoding='utf-8') as l: 
        layout_string=l.read()

    Builder.load_string(layout_string)
    TestApp().run()
