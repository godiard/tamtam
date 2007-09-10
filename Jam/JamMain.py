
import pygtk
pygtk.require( '2.0' )
import gtk

from SubActivity import SubActivity

import os, sys, shutil

import Config
from   gettext import gettext as _
import sugar.graphics.style as style

from Jam.Desktop import Desktop
import Jam.Picker as Picker
import Jam.Block as Block
from Jam.Toolbars import JamToolbar, DesktopToolbar

    
from Util.CSoundNote import CSoundNote
from Util.CSoundClient import new_csound_client
import Util.InstrumentDB as InstrumentDB
from Util import NoteDB

from Fillin import Fillin
from RythmGenerator import generator
from Generation.GenerationConstants import GenerationConstants
from Util.NoteDB import Note, Page

from Util import ControlStream

from math import sqrt

class JamMain(SubActivity):
    
    def __init__(self, activity, set_mode):
        SubActivity.__init__(self, set_mode)

        self.activity = activity

        self.instrumentDB = InstrumentDB.getRef()
        self.noteDB = NoteDB.NoteDB()

        #-- initial settings ----------------------------------
        self.tempo = Config.PLAYER_TEMPO
        self.volume = 0.5
        
        self.csnd = new_csound_client()
        for i in range(0,9):
            self.csnd.setTrackVolume( 100, i )
        self.csnd.setMasterVolume( self.volume*100 ) # csnd expects a range 0-100 for now
        self.csnd.setTempo( self.tempo )

        self.paused = False

        #-- Drawing -------------------------------------------
        def darken( colormap, hex ):
            hexToDec = { "0":0, "1":1, "2":2, "3":3, "4":4, "5":5, "6":6, "7":7, "8":8, "9":9, "A":10, "B":11, "C":12, "D":13, "E":14, "F":15, "a":10, "b":11, "c":12, "d":13, "e":14, "f":15 }
            r = int( 0.7*(16*hexToDec[hex[1]] + hexToDec[hex[2]]) )
            g = int( 0.7*(16*hexToDec[hex[3]] + hexToDec[hex[4]]) )
            b = int( 0.7*(16*hexToDec[hex[5]] + hexToDec[hex[6]]) )
            return colormap.alloc_color( r*256, g*256, b*256 )
        def lighten( colormap, hex ):
            hexToDec = { "0":0, "1":1, "2":2, "3":3, "4":4, "5":5, "6":6, "7":7, "8":8, "9":9, "A":10, "B":11, "C":12, "D":13, "E":14, "F":15, "a":10, "b":11, "c":12, "d":13, "e":14, "f":15 }
            r = 255 - int( 0.7*(255-(16*hexToDec[hex[1]] + hexToDec[hex[2]])) )
            g = 255 - int( 0.7*(255-(16*hexToDec[hex[3]] + hexToDec[hex[4]])) )
            b = 255 - int( 0.7*(255-(16*hexToDec[hex[5]] + hexToDec[hex[6]])) )
            return colormap.alloc_color( r*256, g*256, b*256 )

        win = gtk.gdk.get_default_root_window()
        self.gc = gtk.gdk.GC( win )
        colormap = gtk.gdk.colormap_get_system()
        self.colors = { "bg":                   colormap.alloc_color( Config.PANEL_BCK_COLOR ), 
                        "black":                colormap.alloc_color( style.COLOR_BLACK.get_html() ), 
                        "Picker_Bg":            colormap.alloc_color( "#404040" ), 
                        "Picker_Bg_Inactive":   colormap.alloc_color( "#808080" ), 
                        #"Picker_Bg":            colormap.alloc_color( style.COLOR_TOOLBAR_GREY.get_html() ), 
                        #"Picker_Bg_Inactive":   colormap.alloc_color( style.COLOR_BUTTON_GREY.get_html() ), 
                        "Picker_Fg":            colormap.alloc_color( style.COLOR_WHITE.get_html() ), 
                        "Border_Active":        colormap.alloc_color( "#590000" ), 
                        "Border_Inactive":      colormap.alloc_color( "#8D8D8D" ), 
                        "Border_Highlight":     colormap.alloc_color( "#FFFFFF" ), 
                        "Bg_Active":            colormap.alloc_color( "#FFDDEA" ), 
                        "Bg_Inactive":          colormap.alloc_color( "#DBDBDB" ),
                        "Preview_Note_Fill":    colormap.alloc_color( Config.BG_COLOR ),
                        "Preview_Note_Border":  colormap.alloc_color( Config.FG_COLOR ),
                        "Preview_Note_Selected": colormap.alloc_color( style.COLOR_WHITE.get_html() ),
                        "Note_Fill_Active":     lighten( colormap, "#590000" ), # base "Border_Active"
                        "Note_Fill_Inactive":   lighten( colormap, "#8D8D8D" ), # base "Border_Inactive"
                        "Beat_Line":            colormap.alloc_color( "#959595" ) }
        self.colors[    "Note_Border_Active"]   = self.colors["Border_Active"]
        self.colors[    "Note_Border_Inactive"] = self.colors["Border_Inactive"]


        if True: # load block clipmask
            pix = gtk.gdk.pixbuf_new_from_file(Config.IMAGE_ROOT+'jam-blockMask.png')
            pixels = pix.get_pixels()
            stride = pix.get_rowstride()
            channels = pix.get_n_channels()
            bitmap = ""
            byte = 0
            shift = 0
            for j in range(pix.get_height()):
                offset = stride*j
                for i in range(pix.get_width()):
                    r = pixels[i*channels+offset]
                    if r != "\0": byte += 1 << shift
                    shift += 1
                    if shift > 7:
                        bitmap += "%c" % byte
                        byte = 0
                        shift = 0
                if shift > 0:
                    bitmap += "%c" % byte
                    byte = 0
                    shift = 0
            self.blockMask = gtk.gdk.bitmap_create_from_data( None, bitmap, pix.get_width(), pix.get_height() )
        
        pix = gtk.gdk.pixbuf_new_from_file( Config.IMAGE_ROOT+"sampleBG.png" )
        self.sampleBg = gtk.gdk.Pixmap( win, pix.get_width(), pix.get_height() )
        self.sampleBg.draw_pixbuf( self.gc, pix, 0, 0, 0, 0, pix.get_width(), pix.get_height(), gtk.gdk.RGB_DITHER_NONE )
        self.sampleBg.endOffset = pix.get_width()-5
        self.sampleNoteHeight = 7
        if True: # load sample note clipmask
            pix = gtk.gdk.pixbuf_new_from_file(Config.IMAGE_ROOT+'sampleNoteMask.png')
            pixels = pix.get_pixels()
            stride = pix.get_rowstride()
            channels = pix.get_n_channels()
            bitmap = ""
            byte = 0
            shift = 0
            for j in range(pix.get_height()):
                offset = stride*j
                for i in range(pix.get_width()):
                    r = pixels[i*channels+offset]
                    if r != "\0": byte += 1 << shift
                    shift += 1
                    if shift > 7:
                        bitmap += "%c" % byte
                        byte = 0
                        shift = 0
                if shift > 0:
                    bitmap += "%c" % byte
                    byte = 0
                    shift = 0
            self.sampleNoteMask = gtk.gdk.bitmap_create_from_data( None, bitmap, pix.get_width(), pix.get_height() )
            self.sampleNoteMask.endOffset = pix.get_width()-3

        self.loopPitchOffset = 4
        self.loopTickOffset = 13
        self.pitchPerPixel = float(Config.NUMBER_OF_POSSIBLE_PITCHES-1) / (Block.Loop.HEIGHT - 2*self.loopPitchOffset - self.sampleNoteHeight)
        self.pixelsPerPitch = float(Block.Loop.HEIGHT - 2*self.loopPitchOffset - self.sampleNoteHeight)/(Config.MAXIMUM_PITCH - Config.MINIMUM_PITCH)
        self.pixelsPerTick = Block.Loop.BEAT/float(Config.TICKS_PER_BEAT)
        self.ticksPerPixel = 1.0/self.pixelsPerTick

        #-- Instrument Images ---------------------------------
        self.instrumentImage = {}
        self.instrumentImageActive = {}
        for inst in self.instrumentDB.getSet( "All" ):
            self.prepareInstrumentImage( inst.id, inst.img )

        #-- Loop Images ---------------------------------------
        self.loopImage = {}       # get filled in through updateLoopImage 
        self.loopImageActive = {} #

        #-- Toolbars ------------------------------------------
        self.activity.activity_toolbar.keep.show()

        self.jamToolbar = JamToolbar( self )
        self.activity.toolbox.add_toolbar( _("Jam"), self.jamToolbar )

        self.desktopToolbar = DesktopToolbar( self )
        self.activity.toolbox.add_toolbar( _("Desktop"), self.desktopToolbar )

        #-- GUI -----------------------------------------------
        if True: # GUI
            self.modify_bg( gtk.STATE_NORMAL, self.colors["bg"] ) # window bg
            
            self.GUI = {}
            self.GUI["mainVBox"] = gtk.VBox()
            self.add( self.GUI["mainVBox"] )

            #-- Desktop -------------------------------------------
            self.desktop = self.GUI["desktop"] = Desktop( self )
            self.GUI["mainVBox"].pack_start( self.GUI["desktop"] )

            #-- Bank ----------------------------------------------
            separator = gtk.Label( " " )
            separator.set_size_request( -1, style.TOOLBOX_SEPARATOR_HEIGHT )
            self.GUI["mainVBox"].pack_start( separator, False )
            self.GUI["notebook"] = gtk.Notebook()
            self.GUI["notebook"].set_scrollable( True )
            self.GUI["notebook"].modify_bg( gtk.STATE_NORMAL, self.colors["Picker_Bg"] )            # active tab
            self.GUI["notebook"].modify_bg( gtk.STATE_ACTIVE, self.colors["Picker_Bg_Inactive"] )   # inactive tab
            self.GUI["notebook"].props.tab_vborder = style.TOOLBOX_TAB_VBORDER
            self.GUI["notebook"].props.tab_hborder = style.TOOLBOX_TAB_HBORDER
            self.GUI["notebook"].set_size_request( -1, 160 )
            self.GUI["notebook"].connect( "switch-page", self.setPicker )
            self.GUI["mainVBox"].pack_start( self.GUI["notebook"], False, False )
            self.pickers = {}
            self.pickerScroll = {}
            for type in [ Picker.Instrument, Picker.Drum, Picker.Loop ]:
                self.pickers[type] = type( self )

            def prepareLabel( name ):
                label = gtk.Label( _(name) )
                label.set_alignment( 0.0, 0.5 )
                label.modify_fg( gtk.STATE_NORMAL, self.colors["Picker_Fg"] )
                label.modify_fg( gtk.STATE_ACTIVE, self.colors["Picker_Fg"] )
                return label
                
            self.GUI["notebook"].append_page( self.pickers[Picker.Drum], prepareLabel("Drum Kits") )
            self.GUI["notebook"].append_page( self.pickers[Picker.Loop], prepareLabel("Loops") )

            sets = self.instrumentDB.getLabels()[:]
            sets.sort()
            for set in sets:
                page = gtk.HBox()
                page.set = set
                self.GUI["notebook"].append_page( page, prepareLabel( set ) )

            self.show_all()

            self.GUI["notebook"].set_current_page( 0 )

        #-- Keyboard ------------------------------------------
        self.key_dict = {}
        self.nextTrack = 1
        self.keyboardListener = None
        self.recordingNote = None

        # default instrument
        self._updateInstrument( Config.INSTRUMENTS["kalimba"].instrumentId, 0.5 )
        self.instrumentStack = []

        #-- Drums ---------------------------------------------
        self.drumLoopId = None
        # use dummy values for now
        self.drumFillin = Fillin( 2, 100, Config.INSTRUMENTS["drum1kit"].instrumentId, 0, 1 )

        #-- Desktops ------------------------------------------
        self.curDesktop = None
        # copy preset desktops
        path = Config.TAM_TAM_ROOT+"/Resources/Desktops/"
        filelist = os.listdir( path )
        for file in filelist:
            shutil.copyfile( path+file, Config.SCRATCH_DIR+file ) 

        #-- Final Set Up --------------------------------------
        self.setVolume( self.volume )
        self.setTempo( self.tempo )
        self.activity.toolbox.set_current_toolbar(1) # JamToolbar
        self.setDesktop( 0, True )


    #==========================================================
    # SubActivity Handlers 

    def onActivate( self, arg ):
        SubActivity.onActivate( self, arg )

    def onDeactivate( self ):
        SubActivity.onDeactivate( self )

    def onDestroy( self ):
        SubActivity.onDestroy( self )
    
        # clear up scratch folder    
        path = Config.SCRATCH_DIR
        filelist = os.listdir( path )
        for file in filelist:
           os.remove( path+file ) 


    #==========================================================
    # Playback 

    def onKeyPress( self, widget, event ):
        key = event.hardware_keycode

        if self.key_dict.has_key( key ): # repeated press
            return

        if Config.KEY_MAP_PIANO.has_key( key ):
            pitch = Config.KEY_MAP_PIANO[key]
            inst = Config.INSTRUMENTSID[self.instrument["id"]]

            if inst.kit: # drum kit
                if pitch in GenerationConstants.DRUMPITCH:
                    pitch = GenerationConstants.DRUMPITCH[pitch]
                csnote = self._playNote( key, 
                                         36, 
                                         self.instrument["amplitude"]*0.5, # trackVol*noteVol
                                         self.instrument["pan"], 
                                         100, 
                                         inst.kit[pitch].instrumentId,
                                         self.instrument["reverb"] ) 
            else:
                if event.state == gtk.gdk.MOD1_MASK:
                    pitch += 5
                
                if inst.csoundInstrumentId == Config.INST_PERC: #Percussions resonance
                    duration = 60 
                else:
                    duration = -1

                csnote = self._playNote( key, 
                                         pitch,
                                         self.instrument["amplitude"]*0.5, # trackVol*noteVol
                                         self.instrument["pan"], 
                                         duration,
                                         self.instrument["id"], 
                                         self.instrument["reverb"] ) 

            if self.keyboardListener:
                self.keyboardListener.recordNote( csnote.pitch )
                self.recordingNote = True
 
    def onKeyRelease( self, widget, event ):
        key = event.hardware_keycode

        if self.key_dict.has_key( key ): 
            self._stopNote( key )

        if self.recordingNote:
            if self.keyboardListener:
                self.keyboardListener.finishNote()
            self.recordingNote = False 

    def _playNote( self, key, pitch, amplitude, pan, duration, instrumentId, reverb ):
        self.key_dict[key] = CSoundNote( 0, # onset
                                         pitch,
                                         amplitude,
                                         pan,
                                         duration,
                                         self.nextTrack,
                                         instrumentId,
                                         reverbSend = reverb,
                                         tied = True,
                                         mode = 'mini' )
        self.nextTrack += 1
        if self.nextTrack > 8:
            self.nextTrack = 1
        self.csnd.play(self.key_dict[key], 0.3)

        return self.key_dict[key]

    def _stopNote( self, key ):
        csnote = self.key_dict[key]
        if Config.INSTRUMENTSID[ csnote.instrumentId ].csoundInstrumentId == Config.INST_TIED:
            csnote.duration = .5
            csnote.decay = 0.7
            csnote.tied = False
            self.csnd.play(csnote, 0.3)
        del self.key_dict[key]
 
    def _updateInstrument( self, id, volume, pan = 0, reverb = 0 ): 
        self.instrument = { "id":           id,
                            "amplitude":    volume,
                            "pan":          pan,
                            "reverb":       reverb }

    def pushInstrument( self, instrument ):
        self.instrumentStack.append( self.instrument )
        self.instrument = instrument

    def popInstrument( self ):
        self.instrument = self.instrumentStack.pop()

    def _playDrum( self, id, pageId, volume, reverb, beats, regularity, loopId = None ):

        if loopId == None: # create new loop
            startTick = 0
        else:              # update loop
            startTick = self.csnd.loopGetTick( loopId )
            self.csnd.loopDestroy( loopId )

        loopId = self.csnd.loopCreate()

        # TODO update track volume

        noteOnsets = []
        notePitchs = []
        for n in self.noteDB.getNotesByTrack( pageId, 0 ):
            n.pushState()
            noteOnsets.append( n.cs.onset )
            notePitchs.append( n.cs.pitch )
            n.cs.amplitude = volume * n.cs.amplitude # TODO remove me once track volume is working
            n.cs.reverbSend = reverb
            self.csnd.loopPlay( n, 1, loopId = loopId )    #add as active
            n.popState()

        ticks = self.noteDB.getPage( pageId ).ticks

        self.csnd.loopSetNumTicks( ticks, loopId )

        self.drumFillin.setLoopId( loopId )
        self.drumFillin.setProperties( self.tempo, Config.INSTRUMENTSID[id].name, volume, beats, reverb ) 
        self.drumFillin.unavailable( noteOnsets, notePitchs )

        self.drumFillin.play()

        while startTick > ticks: # align with last beat
            startTick -= Config.TICKS_PER_BEAT
 
        self.csnd.loopSetTick( startTick, loopId )

        # TODO update for beat syncing

        if not self.paused:
            self.csnd.loopStart( loopId )

        return loopId

    def _stopDrum( self, loopId ):
        self.drumFillin.stop()
        self.csnd.loopDestroy( loopId )

    def _playLoop( self, id, volume, reverb, tune, loopId = None, force = False ):
        if loopId == None: # create new loop
            startTick = 0
        else:              # update loop
            startTick = self.csnd.loopGetTick( loopId )
            self.csnd.loopDestroy( loopId )
        
        loopId = self.csnd.loopCreate()
            
        # TODO update track volume

        inst = Config.INSTRUMENTSID[id]

        offset = 0
        for page in tune:
            for n in self.noteDB.getNotesByTrack( page, 0 ):
                n.pushState()
                n.cs.instrumentId = id
                n.cs.amplitude = volume * n.cs.amplitude # TODO remove me once track volume is working
                n.cs.reverbSend = reverb
                if inst.kit: # drum kit
                    if n.cs.pitch in GenerationConstants.DRUMPITCH:
                        n.cs.pitch = GenerationConstants.DRUMPITCH[n.cs.pitch]
                n.cs.onset += offset
                self.csnd.loopPlay( n, 1, loopId = loopId )
                n.popState()
            offset += self.noteDB.getPage(page).ticks


        self.csnd.loopSetNumTicks( offset, loopId )
        
        while startTick > offset: # align with last beat
            startTick -= Config.TICKS_PER_BEAT
        
        self.csnd.loopSetTick( startTick, loopId )

        # TODO update for beat syncing

        if not self.paused or force:
            self.csnd.loopStart( loopId )

        return loopId

    def _stopLoop( self, loopId ):
        self.csnd.loopDestroy( loopId )

    def setPaused( self, paused ):
        if self.paused == paused:
            return

        loops = self.desktop.getLoopIds()

        if self.paused: # unpause
            self.paused = False
            for loop in loops:
                self.csnd.loopStart( loop )
        else:           # pause
            self.paused = True
            for loop in loops:
                self.csnd.loopPause( loop )

    #==========================================================
    # Generate

    def _generateDrumLoop( self, instrumentId, beats, regularity, reverb, pageId = -1 ):
        def flatten(ll):
            rval = []
            for l in ll:
                rval += l
            return rval

        notes = flatten( generator( Config.INSTRUMENTSID[instrumentId].name, beats, 0.8, regularity, reverb) )

        if pageId == -1:
            page = Page( beats )
            pageId = self.noteDB.addPage( -1, page )
        else:
            self.noteDB.deleteNotesByTrack( [ pageId ], [ 0 ] )
            
        if len(notes):
            self.noteDB.addNotes( [ pageId, 0, len(notes) ] + notes + [-1] ) 

        return pageId

    def _generateTrack( self, instrumentId, page, track, parameters, algorithm ):
        dict = { track: { page: self.noteDB.getCSNotesByTrack( page, track ) } }
        instruments = { page: [ Config.INSTRUMENTSID[instrumentId].name for i in range(Config.NUMBER_OF_TRACKS) ] }
        beatsOfPages = { page: self.noteDB.getPage(page).beats }

        algorithm( parameters,
                   [ 0.5 for i in range(Config.NUMBER_OF_TRACKS) ],
                   instruments,
                   self.tempo,
                   beatsOfPages,
                   [ track ],
                   [ page ],
                   dict, 
                   4) 

        # filter & fix input ...WTF!?
        for track in dict:
            for page in dict[track]:
                for note in dict[track][page]:
                    intdur = int(note.duration)
                    note.duration = intdur
                    note.pageId = page
                    note.trackId = track

        # prepare the new notes
        newnotes = []
        for tid in dict:
            for pid in dict[tid]:
                newnotes += dict[tid][pid]

        # delete the notes and add the new
        self.noteDB.deleteNotesByTrack( [ page ], [ track ] )

        self.noteDB.addNotes( 
            [ page, track, len(dict[track][page]) ]
          + dict[track][page]
          + [ -1 ] )


    #==========================================================
    # Get/Set 

    def getVolume( self ):
        return self.volume

    def setVolume( self, volume ):
        self.jamToolbar.volumeSlider.set_value( volume )

    def _setVolume( self, volume ):
        self.volume = volume
        self.csnd.setMasterVolume( self.volume*100 ) # csnd expects a range 0-100 for now

    def getTempo( self ):
        return self.tempo

    def setTempo( self, tempo ):
        self.jamToolbar.tempoSlider.set_value( tempo )

    def _setTempo( self, tempo ):
        self.tempo = tempo
        self.csnd.setTempo( self.tempo )

    def getInstrument( self ):
        return self.instrument

    def getDesktop( self ):
        return self.desktop

    def _clearDesktop( self, save = True ):
        if self.curDesktop == None:
            return

        if save:
            self._saveDesktop()

        self.desktop._clearDesktop()

        self.curDesktop = None

    def setDesktop( self, desktop, force = False ):
        radiobtn = self.desktopToolbar.getDesktopButton( desktop )
        if force and radiobtn.get_active():
            self._setDesktop( desktop )
        else:
            radiobtn.set_active( True )

    def _setDesktop( self, desktop ):
        self._clearDesktop()

        self.curDesktop = desktop
    
        TTTable = ControlStream.TamTamTable( self.noteDB, jam = self )

        filename = self.getDesktopScratchFile( self.curDesktop )
        try:
            stream = open( filename, "r" )
            TTTable.parseFile( stream )
            stream.close()
        except IOError, (errno, strerror):
            if Config.DEBUG > 3: print "IOError:: _setDesktop:", errno, strerror 

    def getInstrumentImage( self, id, active = False ):
        if active: return self.instrumentImageActive[id]
        else:      return self.instrumentImage[id]           

    def getLoopImage( self, id, active = False ):
        if active: return self.loopImageActive[id]
        else:      return self.loopImage[id]

    def setPicker( self, widget, pagePointer, page_num ):
        page = self.GUI["notebook"].get_nth_page( page_num )
        if page == self.pickers[Picker.Drum]:
            pass
        elif page == self.pickers[Picker.Loop]:
            pass
        else:
            self.pickers[Picker.Instrument].setFilter( ( page.set ) )
            parent = self.pickers[Picker.Instrument].get_parent()
            if parent != page:
                if parent != None:
                    parent.remove( self.pickers[Picker.Instrument] )
                page.add( self.pickers[Picker.Instrument] )

    def setKeyboardListener( self, listener ):
        self.keyboardListener = listener

    #==========================================================
    # Pixmaps 

    def prepareInstrumentImage( self, id, img_path ):
        try:
            win = gtk.gdk.get_default_root_window()
            pix = gtk.gdk.pixbuf_new_from_file( img_path )
            x = (Block.Block.WIDTH-pix.get_width())//2
            y = (Block.Block.HEIGHT-pix.get_height())//2
            img = gtk.gdk.Pixmap( win, Block.Block.WIDTH, Block.Block.HEIGHT )
            self.gc.foreground = self.colors["Bg_Inactive"]
            img.draw_rectangle( self.gc, True, 0, 0, Block.Block.WIDTH, Block.Block.HEIGHT )
            img.draw_pixbuf( self.gc, pix, 0, 0, x, y, pix.get_width(), pix.get_height(), gtk.gdk.RGB_DITHER_NONE )
            self.instrumentImage[id] = img
            img = gtk.gdk.Pixmap( win, Block.Block.WIDTH, Block.Block.HEIGHT )
            self.gc.foreground = self.colors["Bg_Active"]
            img.draw_rectangle( self.gc, True, 0, 0, Block.Block.WIDTH, Block.Block.HEIGHT )
            img.draw_pixbuf( self.gc, pix, 0, 0, x, y, pix.get_width(), pix.get_height(), gtk.gdk.RGB_DITHER_NONE )
            self.instrumentImageActive[id] = img
        except:
            if Config.DEBUG >= 5: print "JamMain:: file does not exist: " + img_path
            img = gtk.gdk.Pixmap( win, Block.Block.WIDTH, Block.Block.HEIGHT )
            self.gc.foreground = self.colors["Bg_Inactive"]
            img.draw_rectangle( self.gc, True, 0, 0, Block.Block.WIDTH, Block.Block.HEIGHT )
            self.instrumentImage[id] = img
            img = gtk.gdk.Pixmap( win, Block.Block.WIDTH, Block.Block.HEIGHT )
            self.gc.foreground = self.colors["Bg_Active"]
            img.draw_rectangle( self.gc, True, 0, 0, Block.Block.WIDTH, Block.Block.HEIGHT )
            self.instrumentImageActive[id] = img
    
    def _drawNotes( self, pixmap, beats, notes, active ):
        self.gc.set_clip_mask( self.sampleNoteMask )
        for note in notes: # draw N notes
            x = self.ticksToPixels( note.cs.onset )
            endX = self.ticksToPixels( note.cs.onset + note.cs.duration ) - 3 # include end cap offset
            width = endX - x
            if width < 5: 
                width = 5
                endX = x + width
            y = self.pitchToPixels( note.cs.pitch )
            # draw fill
            if active: self.gc.foreground = self.colors["Note_Fill_Active"]
            else:      self.gc.foreground = self.colors["Note_Fill_Inactive"]
            self.gc.set_clip_origin( x, y-self.sampleNoteHeight )
            pixmap.draw_rectangle( self.gc, True, x+1, y+1, width+1, self.sampleNoteHeight-2 )
            # draw border
            if active: self.gc.foreground = self.colors["Note_Border_Active"]
            else:      self.gc.foreground = self.colors["Note_Border_Inactive"]
            self.gc.set_clip_origin( x, y )
            pixmap.draw_rectangle( self.gc, True, x, y, width, self.sampleNoteHeight )
            self.gc.set_clip_origin( endX-self.sampleNoteMask.endOffset, y )
            pixmap.draw_rectangle( self.gc, True, endX, y, 3, self.sampleNoteHeight )
 
    def updateLoopImage( self, id ):
        page = self.noteDB.getPage( id )

        win = gtk.gdk.get_default_root_window()
        width = Block.Loop.WIDTH[page.beats]
        height = Block.Loop.HEIGHT

        self.gc.set_clip_rectangle( gtk.gdk.Rectangle( 0, 0, width, height ) )

        pixmap = gtk.gdk.Pixmap( win, width, height )
        self.gc.foreground = self.colors["Bg_Inactive"]
        pixmap.draw_rectangle( self.gc, True, 0, 0, width, height )
        self._drawNotes( pixmap, page.beats, self.noteDB.getNotesByTrack( id, 0 ), False )
        self.loopImage[id] = pixmap

        self.gc.set_clip_rectangle( gtk.gdk.Rectangle( 0, 0, width, height ) )

        pixmap = gtk.gdk.Pixmap( win, width, height )
        self.gc.foreground = self.colors["Bg_Active"]
        pixmap.draw_rectangle( self.gc, True, 0, 0, width, height )
        self._drawNotes( pixmap, page.beats, self.noteDB.getNotesByTrack( id, 0 ), True )
        self.loopImageActive[id] = pixmap

    def ticksToPixels( self, ticks ):
        return self.loopTickOffset + int(round( ticks * self.pixelsPerTick ))
    def pitchToPixels( self, pitch ):
        return self.loopPitchOffset + int(round( ( Config.MAXIMUM_PITCH - pitch ) * self.pixelsPerPitch ))

    #==========================================================
    # Load/Save 
 
    def _saveDesktop( self ):
        if self.curDesktop == None:
            return

        filename = self.getDesktopScratchFile( self.curDesktop )
        if os.path.isfile( filename ):
           os.remove( filename ) 

        try:
            scratch = open( filename, "w" )
            stream = ControlStream.TamTamOStream(scratch)

            self.noteDB.dumpToStream( stream, True )
            self.desktop.dumpToStream( stream )

            scratch.close()
        except IOError, (errno, strerror):
            if Config.DEBUG > 3: print "IOError:: _saveDesktop:", errno, strerror 

    def getDesktopScratchFile( self, i ):
        return Config.SCRATCH_DIR+"desktop%d" % i

    def handleJournalLoad( self, filepath ):

        self._clearDesktop( False )

        TTTable = ControlStream.TamTamTable( self.noteDB, jam = self )

        try:
            stream = open( filepath, "r" )
            TTTable.parseFile( stream )
            stream.close()

            self.setVolume( TTTable.masterVolume )
            self.setTempo( TTTable.tempo )

        except IOError, (errno, strerror):
            if Config.DEBUG > 3: print "IOError:: handleJournalLoad:", errno, strerror 

    def handleJournalSave( self, filepath ):
        
        self._saveDesktop()

        try:
            streamF = open( filepath, "w" )
            stream = ControlStream.TamTamOStream( streamF )
    
            for i in range(10):
                desktop_file = self.getDesktopScratchFile( i )
                stream.desktop_store( desktop_file, i ) 

            stream.desktop_set( self.curDesktop )

            stream.master_vol( self.volume )
            stream.tempo( self.tempo )

            streamF.close()

        except IOError, (errno, strerror):
            if Config.DEBUG > 3: print "IOError:: handleJournalSave:", errno, strerror 
