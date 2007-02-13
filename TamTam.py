import signal , time , sys , os, shutil
import pygtk
pygtk.require( '2.0' )
import gtk

import Config
import Util.CSoundClient as CSoundClient
from   Util.Profiler import TP
from   miniTamTam.miniTamTamMain import miniTamTamMain
from   Edit.MainWindow import MainWindow
from Util.Clooper.sclient import *

try :
    from sugar.activity.Activity import Activity
except ImportError:
    print "No Sugar for you"

if not os.path.isdir(Config.PREF_DIR):
    os.mkdir(Config.PREF_DIR)
    os.system('chmod 0777 ' + Config.PREF_DIR + ' &')
    for snd in ['mic1','mic2','mic3','mic4','lab1','lab2','lab3','lab4']:
        shutil.copyfile(Config.SOUNDS_DIR + '/' + snd , Config.PREF_DIR + '/' + snd)
        os.system('chmod 0777 ' + Config.PREF_DIR + '/' + snd + ' &')

if __name__ == "__main__":     
    def run_non_sugar_mode():
        tamtam = miniTamTamMain()
        mainwin = gtk.Window(gtk.WINDOW_TOPLEVEL)
        color = gtk.gdk.color_parse('#FFFFFF')
        mainwin.modify_bg(gtk.STATE_NORMAL, color)
        #mainwin.set_size_request(1200,700)
        mainwin.set_title('miniTamTam')
        mainwin.set_resizable(False)
        mainwin.connect('destroy' , gtk.main_quit )
        mainwin.connect( "key-press-event", tamtam.keyboardStandAlone.onKeyPress )
        mainwin.connect( "key-release-event", tamtam.keyboardStandAlone.onKeyRelease )
        mainwin.add(tamtam)
        tamtam.show()
        mainwin.show()
        gtk.main()
        
    def run_edit_mode():
        tamtam = MainWindow()
        mainwin = gtk.Window(gtk.WINDOW_TOPLEVEL)
        mainwin.set_title('TamTam Player')
        display = mainwin.get_display()
        screen = gtk.gdk.Display.get_default_screen(display)
        mainwin.set_geometry_hints( None, screen.get_width(), screen.get_height(), screen.get_width(), screen.get_height(), screen.get_width(), screen.get_height() )
        #mainwin.fullscreen() # don't need to specify full screen, it seem to sit properly anyway
        mainwin.set_resizable(False)
        mainwin.connect('destroy' , tamtam.destroy )
        #mainwin.connect( "configure-event", tamtam.handleConfigureEvent )
        mainwin.connect( "key-press-event", tamtam.onKeyPress )
        mainwin.connect( "key-release-event", tamtam.onKeyRelease )
        mainwin.connect( "delete_event", tamtam.delete_event )
        mainwin.add(tamtam)
        tamtam.show()
        mainwin.show()
        gtk.main()

    if len(sys.argv) > 1 and sys.argv[1] == 'edit':
        if False:
            import hotshot
            prof = hotshot.Profile("some_stats")
            prof.runcall(run_edit_mode)
            prof.close()
        else:
            run_edit_mode()
    else:
        run_non_sugar_mode()
    
    sys.exit(0)

class TamTam(Activity):
    def __init__(self):
        Activity.__init__(self)
        
        color = gtk.gdk.color_parse(Config.PANEL_BCK_COLOR)
        self.modify_bg(gtk.STATE_NORMAL, color)
        
        self.tamtam = miniTamTamMain()
        self.connect('focus_in_event',self.handleFocusIn)
        self.connect('focus_out_event',self.handleFocusOut)
        self.connect('destroy', self.do_quit)
        self.add(self.tamtam)
        self.tamtam.show()
        self.set_title('TamTam')
        self.set_resizable(False)
        self.connect( "key-press-event", self.tamtam.keyboardStandAlone.onKeyPress )
        self.connect( "key-release-event", self.tamtam.keyboardStandAlone.onKeyRelease )

    def handleFocusIn(self, event, data=None):
        csnd = new_csound_client()
        csnd.connect(True)
        csnd.load_instruments()
    
    def handleFocusOut(self, event, data=None):
        if self.tamtam.synthLabWindowOpen(): 
            return
        csnd = new_csound_client()
        csnd.connect(False)

    def do_quit(self, arg2):
        os.system('rm ' + Config.PREF_DIR + '/synthTemp*')
        del self.tamtam

