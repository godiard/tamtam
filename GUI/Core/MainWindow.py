import pygtk
pygtk.require( '2.0' )
import gtk 
import gobject

import time

from Framework.Constants import Constants
from Framework.Core.PagePlayer import PagePlayer
from Framework.CSound.CSoundClient import CSoundClient
from Framework.CSound.CSoundConstants import CSoundConstants
from Framework.Generation.Generator import GenerationParameters

from GUI.GUIConstants import GUIConstants
from GUI.Core.MixerWindow import MixerWindow
from GUI.Core.MicRecordingWindow import MicRecordingWindow
from GUI.Core.PageView import PageView
from GUI.Core.TuneView import TuneView
from GUI.Core.PageBankView import PageBankView
from GUI.Generation.GenerationParametersWindow import GenerationParametersWindow
from BackgroundView import BackgroundView
from TrackView import TrackView
from PositionIndicator import PositionIndicator
#from KeyboardInput import KeyboardInput   #TODO: put functionality back in there

from Framework.Core.Profiler import TP

from Framework.Generation.Generator import generator1, variate

from Framework.Note import *
from Framework.Music import *
from Framework.NoteLooper import *

#-----------------------------------
# The main TamTam window
#-----------------------------------
class MainWindow( gtk.Window ):

    def __init__( self ):

        # these helper functions do not 
        # run in any particular order.... 
        # TODO: give these functions better names, put them in execution order, cut hierarchy

        def setupGUI( ):
            self.volumeFunctions = {}

#            self.pagePlayer = PagePlayer( set( range( Constants.NUMBER_OF_TRACKS ) ),
#                                          self.updatePositionIndicator,
#                                          self.updatePage )
            
            self.generateParametersWindow = GenerationParametersWindow( self.generate, self.variate, self.handleCloseGenerateWindow )
            
            setupWindow()
            setupGlobalControls()
            setupPageControls()
            setupTrackControls()
            setupMainView()

            self.tuneView = TuneView( self.onTuneViewSelect )
            self.pageBankView = PageBankView( self.onPageBankSelect )
                    
            self.mainWindowBox = gtk.HBox( False, 5 )

            self.globalControlsBox = gtk.VBox( False )
     
            self.fpsText = gtk.Label( "" )
            self.globalControlsBox.pack_start( self.fpsText, False )
            self.globalControlsBox.pack_start( self.globalControlsFrame, True )

            self.mainWindowBox.pack_start( self.globalControlsBox, False )

            
            controlsBox = gtk.VBox( False, 5 )
            controlsBox.pack_start( self.trackControlsBox, False )
            #TODO: this Label is temporary!!
            controlsBox.pack_start( gtk.Label( "" ), True )
            controlsBox.pack_start( self.pageControlsBox, False )
            self.mainWindowBox.pack_start( controlsBox, False )
            
            self.trackPagesBox = gtk.VBox( False )
            self.trackPagesBox.pack_start( self.mainView, True )
            self.trackPagesBox.pack_start( self.tuneView, False )
            self.trackPagesBox.pack_start( self.pageBankView, False, True, 5 )
            
            self.mainWindowBox.pack_start( self.trackPagesBox )
            self.add( self.mainWindowBox )

            #to update mainView's contents when window gets resized
            #TODO: is this the right way to do this?
            self.connect( "configure-event", self.handleConfigureEvent )

            self.connect( "key-press-event", self.onKeyPress )
            self.connect( "key-release-event", self.onKeyRelease )

        def initialize( ):
            # Volume initialisation for Csound.
            CSoundClient.setMasterVolume( self.getVolume() )
            
            for pageIndex in range( GUIConstants.NUMBER_OF_PAGE_BANK_ROWS * 
                                    GUIConstants.NUMBER_OF_PAGE_BANK_COLUMNS ):
                self.addPage()
            self.pageBankView.selectPage( 0 )    
            
            for tid in range(Constants.NUMBER_OF_TRACKS):
                self.handleInstrumentChanged( ( tid, music_trackInstrument_get(tid) ) )


        def setupWindow( ):
            self.connect( "delete_event", self.delete_event )
            self.connect( "destroy", self.destroy )
            
            ntracks = Constants.NUMBER_OF_TRACKS
            self.set_border_width( 10 )
            self.set_geometry_hints( None, 855, ntracks * 50 + 200, 900, ntracks * 300 + 200 )
        
        # contains TAM-TAM and OLPC labels, as well as the volume and tempo sliders
        def setupGlobalControls( ):
            self.globalControlsFrame = gtk.Frame()
            self.globalControlsFrame.set_shadow_type( gtk.SHADOW_ETCHED_OUT )
            
            self.globalControlsBox = gtk.VBox()
            
            self.tamTamLabel = gtk.Label( "     TAM - TAM     " )
            self.globalControlsBox.pack_start( self.tamTamLabel )
            
            self.mainSlidersBox = gtk.HBox()
            self.volumeAdjustment = gtk.Adjustment( 50, 0, 100, 1, 1, 0 )
            self.volumeAdjustment.connect( "value_changed", self.handleVolumeChanged, None )
            self.volumeSlider = gtk.VScale( self.volumeAdjustment )
            self.volumeSlider.set_draw_value( False )
            self.volumeSlider.set_digits( 0 )
            self.volumeSlider.set_inverted( True )
            self.mainSlidersBox.pack_start( self.volumeSlider, True, True, 4 )
            
            self.tempoAdjustment = gtk.Adjustment( 100, 60, 180, 1, 1, 0 )
            self.tempoAdjustment.connect( "value_changed", self.handleTempoChanged, None )
            self.tempoSlider = gtk.VScale( self.tempoAdjustment )
            self.tempoSlider.set_draw_value( False )
            self.tempoSlider.set_digits( 0 )
            self.tempoSlider.set_inverted( True )
            self.mainSlidersBox.pack_start( self.tempoSlider )

            self.beatsPerPageAdjustment = gtk.Adjustment( 4, 1, 8, 1, 1, 0 )
            self.beatsPerPageAdjustment.connect( "value_changed", self.updateNumberOfBars, None )
            self.barsSlider = gtk.VScale( self.beatsPerPageAdjustment )
            self.barsSlider.set_draw_value( False )
            self.barsSlider.set_digits( 0 )
            self.barsSlider.set_inverted( True )
            self.barsSlider.set_increments( 1, 1 )
            self.barsSlider.set_update_policy( gtk.UPDATE_DELAYED )
            self.mainSlidersBox.pack_start( self.barsSlider )

            self.globalControlsBox.pack_start( self.mainSlidersBox )
            self.updateWindowTitle( None, None )

            self.olpcLabel = gtk.Label( "OLPC" )
            self.globalControlsBox.pack_start( self.olpcLabel )
            
            self.saveButton = gtk.Button("Save")
            self.loadButton = gtk.Button("Open")
            
            fileBox = gtk.HBox()
            fileBox.pack_start( self.saveButton, True )
            fileBox.pack_start( self.loadButton, True )
            self.globalControlsBox.pack_start( fileBox, False )
            self.saveButton.connect("clicked", self.handleSave, None )
            self.loadButton.connect("clicked", self.handleLoad, None )
            
            self.globalControlsFrame.add( self.globalControlsBox )

        def setupPageControls( ):
            self.pageControlsBox = gtk.VBox( False )

            self.generateButton = gtk.ToggleButton( "Generate" )
            self.playButton = gtk.ToggleButton( "Play" )
            self.keyboardButton = gtk.ToggleButton( "K" )
            self.keyboardRecordButton = gtk.ToggleButton( "Record" )
            
            self.pageControlsBox.pack_start( self.generateButton, False )
            self.pageControlsBox.pack_start( self.playButton, False )
            
            keyboardBox = gtk.HBox()
            keyboardBox.pack_start( self.keyboardButton, False )
            keyboardBox.pack_start( self.keyboardRecordButton )
            self.pageControlsBox.pack_start( keyboardBox, False )
            
            self.generateButton.connect( "toggled", self.handleGenerate, None )
            self.playButton.connect( "toggled", self.handlePlay, "Page Play" )
            self.keyboardButton.connect( "toggled", self.handleKeyboard, None )
            self.keyboardRecordButton.connect( "toggled", self.handleKeyboardRecord, None )
            
        def setupTrackControls( ):
            self.trackControlsBox = gtk.VBox()
            self.instrumentRecordButtons = {}
            for trackID in range( Constants.NUMBER_OF_TRACKS):
                trackControlsBox = gtk.HBox()

                #setup instrument controls
                instrumentControlsBox = gtk.VBox()
                
                instrumentMenu = gtk.Menu()
                instrumentMenuItem = gtk.MenuItem( "Instrument" )
                instrumentMenuItem.set_submenu( instrumentMenu )
                
                instrumentNames = []
                instrumentFolderNames = CSoundConstants.INSTRUMENTS.keys()
                for instrumentName in instrumentFolderNames:
                    if not instrumentName[0: 4] == 'drum':
                       instrumentNames.append( instrumentName )
                                    
                instrumentNames.append( 'drum1kit' )
                instrumentNames.sort()
                for instrumentName in instrumentNames:
                    menuItem = gtk.MenuItem( instrumentName )
                    menuItem.connect_object( "activate", self.handleInstrumentChanged, ( trackID, instrumentName ) )
                    instrumentMenu.append( menuItem )
                    
                instrumentMenuBar = gtk.MenuBar()
                instrumentMenuBar.append( instrumentMenuItem )
                instrumentControlsBox.pack_start( instrumentMenuBar )
                
                recordButton = gtk.Button()
                recordButton.set_size_request( 15, 15 )
                self.instrumentRecordButtons[ trackID ] = recordButton
                instrumentControlsBox.pack_start( recordButton, False )
                
                trackControlsBox.pack_start( instrumentControlsBox )

                #setup playback controls
                playbackControlsBox = gtk.VBox()
                
                muteButton = gtk.ToggleButton()
                muteButton.set_size_request( 15, 15 )
                playbackControlsBox.pack_start( muteButton, False )
                
                volumeAdjustment = gtk.Adjustment( 0.8, 0, 1, 0.01, 0.01, 0 )
                volumeAdjustment.connect( "value_changed", self.handleTrackVolumeChanged, trackID )
                self.volumeFunctions[ trackID ] = volumeAdjustment.get_value
                volumeSlider = gtk.VScale( volumeAdjustment )
                volumeSlider.set_update_policy( 0 )
                volumeSlider.set_digits( 2 )
                volumeSlider.set_draw_value( False )
                volumeSlider.set_digits( 0 )
                volumeSlider.set_inverted( True )
                playbackControlsBox.pack_start( volumeSlider, True )
                            
                trackControlsBox.pack_start( playbackControlsBox )

                trackName = "Track %i" % trackID
                muteButton.connect( "toggled", self.handleMuteTrack, trackID )

                self.trackControlsBox.pack_start( trackControlsBox )

        def setupMainView( ):
            self.mainView = gtk.Fixed()

            self.backgroundView = BackgroundView( self.pagePlayer.trackIDs,
                                                  self.pagePlayer.selectedTrackIDs,
                                                  self.updateSelection,
                                                  self.pagePlayer.mutedTrackIDs,
                                                  self.beatsPerPageAdjustment,
                                                  self.pagePlayer.trackDictionary,
                                                  self.pagePlayer.selectedPageIDs,
                                                  self.updatePage )
            self.mainView.put( self.backgroundView, 0, 0 )

            self.trackViews = {} # [ pageID : [ trackID : TrackView ] ]
            
        gtk.Window.__init__( self, gtk.WINDOW_TOPLEVEL )
            
        # keyboard variables
        self.kb_active = False
        self.kb_record = False
        self.kb_mono = False
        self.kb_keydict = {}

        # playback params
        self.playingTune = False
        self.currentPageId = 0

        # FPS stuff
        self.fpsTotalTime = 0
        self.fpsFrameCount = 0
        self.fpsN = 100 # how many frames to average FPS over
        self.fpsLastTime = time.time() # fps will be borked for the first few frames but who cares?
        
        music_init()

        setupGUI()    #above
        initialize()  #above


        self.handleConfigureEvent( None, None ) # needs to come after pages have been added in initialize()
        
        self.show_all()  #gtk command
    
    def updateFPS( self ):
        t = time.time()
        dt = t - self.fpsLastTime
        self.fpsLastTime = t
        self.fpsTotalTime += dt
        self.fpsFrameCount += 1
        if self.fpsFrameCount == self.fpsN:
            fps = self.fpsN/self.fpsTotalTime
            avgMS = 1000/fps
            self.fpsText.set_text("FPS %d ms %.2f" % (fps, avgMS) )
            self.fpsTotalTime = 0
            self.fpsFrameCount = 0

    #-----------------------------------
    # playback functions
    #-----------------------------------
    def handlePlay( self, widget, data ):
        if widget.get_active():
            self.noteLooper = NoteLooper( 48, 0.2, 0, [1.0] * 6, 20, music_getNotes([0], range(6) ) )
            buf = self.noteLooper.next( )
            CSoundClient.sendText( buf ) 
            self.playbackTimeout = gobject.timeout_add( 50, self.onTimeout )
        else:
            gobject.source_remove( self.playbackTimeout )

        self.kb_record = self.playButton.get_active() and self.keyboardRecordButton.get_active() and self.keyboardButton.get_active()

    def onTimeout(self):
        buf = self.noteLooper.next()
        CSoundClient.sendText( buf ) 

        self.updateFPS()

        return True

    def shutOffCSound(self ):
        for track in range( Constants.NUMBER_OF_TRACKS ):
            for i in range( 3 ):
                csoundInstrument = i + 101
                CSoundClient.sendText( CSoundConstants.PLAY_NOTE_OFF_COMMAND % ( csoundInstrument, track ) )


    def handleKeyboard( self, widget, data ):
        self.kb_active = widget.get_active()
        
    def handleKeyboardRecord( self, widget, data ):
        if not self.kb_active:
            self.keyboardButton.set_active( True )
            
        self.kb_record = self.playButton.get_active() and self.keyboardRecordButton.get_active()

    def handleMuteTrack( self, widget, trackID ):
        print 'ERROR: handleMuteTrack'
    
    def handleVolumeChanged( self, widget, data ):
    	CSoundClient.setMasterVolume(self.getVolume())
        self.updateWindowTitle()
       
    def handleTempoChanged( self, widget, data ):

        tempo = round( self.tempoAdjustment.value, 0 )

        music_tempo_set( tempo )

        print 'TODO: propagate tempo to player'
        
        self.updateWindowTitle()


    #-----------------------------------
    # generation functions
    #-----------------------------------
    def handleGenerate( self, widget, data ):
        if widget.get_active():
            self.generateParametersWindow.show_all()
        else:
            self.handleCloseGenerateWindow()
            
    def handleCloseGenerateWindow( self, widget = None, data = None ):
        self.generateParametersWindow.hide_all()
        self.generateButton.set_active( False )
                
    def recompose( self, algo, params):

        dict = {}
        for t in range(8):
            dict[t] = {}
            for p in range(40):
                dict[t][p] = []

        trackIDs = set([])
        pageIDs = [0,1,2]

        #hack... this is it right?
        if set([]) == trackIDs:
            trackIDs = set(range(0,Constants.NUMBER_OF_TRACKS))

        algo( 
                params,
                music_volume_get( slice(0, Constants.NUMBER_OF_TRACKS)),
                music_trackInstrument(slice(0, Constants.NUMBER_OF_TRACKS)),
                music_tempo_get(),
                4,  #beats per page TODO: talk to olivier about handling pages of different sizes
                trackIDs,
                pageIDs,
                dict)
        #print dict

        music_addNotes_fromDict(dict)

        self.updateTrackViews()
        
        self.handleCloseGenerateWindow( None, None )
        self.handleConfigureEvent( None, None )

    def generate( self, params ):
        self.recompose( generator1, params)

    def variate( self, params ):
        self.recompose( variate, params)
        
    #-----------------------------------
    # load and save functions
    #-----------------------------------
    def handleSave(self, widget, data):
        chooser = gtk.FileChooserDialog(title=None,action=gtk.FILE_CHOOSER_ACTION_SAVE, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_SAVE,gtk.RESPONSE_OK))

        if chooser.run() == gtk.RESPONSE_OK:
            try: 
                print 'INFO: serialize to file %s' % chooser.get_filename()
                f = open( chooser.get_filename(), 'w')
                music_save(f)
                f.close()
            except IOError: 
                print 'ERROR: failed to serialize to file %s' % chooser.get_filename()

        chooser.destroy()
    
    def handleLoad(self, widget, data):
        chooser = gtk.FileChooserDialog(title=None,action=gtk.FILE_CHOOSER_ACTION_OPEN, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))

        if chooser.run() == gtk.RESPONSE_OK:
            try: 
                print 'INFO: unserialize from file %s' % chooser.get_filename()
                f = open( chooser.get_filename(), 'r')
                music_load(f)
            except IOError: 
                print 'ERROR: failed to unserialize from file %s' % chooser.get_filename()

        chooser.destroy()
        print 'TODO: update misc. program state to new music'
        
    def handleTrackVolumeChanged( self, widget, trackID ):
        music_volume_set( trackID, widget.get_value())
        
    # data is tuple ( trackID, instrumentName )
    def handleInstrumentChanged( self, data ):
        trackID = data[ 0 ]
        instrumentName = data[ 1 ]

        recordButton = self.instrumentRecordButtons[ trackID ]
        if instrumentName in CSoundConstants.RECORDABLE_INSTRUMENTS:
            recordButton.show()
            recordButton.connect( "clicked", 
                                  self.handleMicRecord,
                                  CSoundConstants.RECORDABLE_INSTRUMENT_CSOUND_IDS[ instrumentName ] )
        else:
            recordButton.hide()

    #-----------------------------------
    # Record functions
    #-----------------------------------
    def handleMicRecord( self, widget, data ):
        CSoundClient.micRecording( data )
            
    def handleCloseMicRecordWindow( self, widget = None, data = None ):
        self.micRecordWindow.destroy()
        self.micRecordButton.set_active( False )

    #-----------------------------------
    # callback functions
    #-----------------------------------
    def onTuneViewSelect(pageId):
        print 'ERROR: implement onTuneViewSelect'

    def onPageBankSelect(pageId, arg2):
        print 'ERROR: implement onPageBankSelect'

    def onKeyPress(self,widget,event):
        if not self.kb_active:
            return
        if self.kb_record:
            self.kb_mono = False
        
        key = event.hardware_keycode 
        # If the key is already in the dictionnary, exit function (to avoir key repeats)
        if self.kb_keydict.has_key(key):
                return
        # Assign on which track the note will be created according to the number of keys pressed    
        track = len(self.kb_keydict)+10
        if self.kb_mono:
            track = 10
        # If the pressed key is in the keymap
        if KEY_MAP.has_key(key):
            # CsoundNote parameters
            onset = self.getCurrentTick()
            pitch = KEY_MAP[key]
            duration = -1
            instrument = self.getTrackInstruments()[0]
            # get instrument from top selected track if a track is selected
            if self.getSelectedTrackIDs():
                instrument = self.getTrackInstruments()[min(self.getSelectedTrackIDs())]
            
            if instrument == 'drum1kit':
                if GenerationConstants.DRUMPITCH.has_key( pitch ):
                    instrument = CSoundConstants.DRUM1INSTRUMENTS[ GenerationConstants.DRUMPITCH[ pitch ] ]
                else:
                    instrument = CSoundConstants.DRUM1INSTRUMENTS[ pitch ]
                pitch = 36
                duration = 100
            
            if CSoundConstants.INSTRUMENTS[instrument].csoundInstrumentID == 102:
                duration = 100
            
            # Create and play the note
            self.kb_keydict[key] = Note.note_new(onset = 0, 
                                            pitch = pitch, 
                                            amplitude = 1, 
                                            pan = 0.5, 
                                            duration = duration, 
                                            trackID = track, 
                                            fullDuration = False, 
                                            instrument = instrument, 
                                            instrumentFlag = instrument)
            Note.note_play(self.kb_keydict[key])
                
    def onKeyRelease(self,widget,event):
        if not self.kb_active:
            return
        key = event.hardware_keycode 
        
        if KEY_MAP.has_key(key):
            self.kb_keydict[key]['duration'] = 0
            self.kb_keydict[key]['amplitude'] = 0
            self.kb_keydict[key]['dirty'] = True
            Note.note_play(self.kb_keydict[key])
            self.kb_keydict[key]['duration'] = self.getCurrentTick() - self.kb_keydict[key]['onset']
            #print "onset",self.kb_keydict[key].onset
            #print "dur",self.kb_keydict[key].duration
            if self.kb_record and len( self.getSelectedTrackIDs() ) != 0:
                self.kb_keydict[key]['amplitude'] = 1
                self.getTrackDictionary()[min(self.getSelectedTrackIDs())][self.getCurrentPageIDCallback()].append(self.kb_keydict[key])
                print 'ERROR: keyboard release... callbacks?'
            del self.kb_keydict[key]

    def delete_event( self, widget, event, data = None ):
        return False

    def destroy( self, widget ):
        print TP.PrintAll()
        gtk.main_quit()

    def updateWindowTitle( self, widget = None, data = None ):
        self.set_title( self.getWindowTitle() )
    
    def updateNumberOfBars( self, widget = None, data = None ):
        self.updateWindowTitle()
        self.updateTrackViews()
        self.backgroundView.queue_draw()
        
    def updateSelection( self ):
        self.positionIndicator.queue_draw()

    def updatePage( self ):
        TP.ProfileBegin( "updatePage" )

        if self.playingTune:
            self.tuneView.selectPage( self.currentPageId, False )
            self.pageBankView.deselectAll()
        else:
            self.tuneView.deselectAll()

        self.backgroundView.setCurrentTracks( self.trackViews[currentPageId] )

        self.handleConfigureEvent( None, None )

        print TP.ProfileEndAndPrint( "updatePage" )
        
    def addPage( self ):
        pageID = len( self.pagePlayer.pageDictionary.keys() )

        #setup track views for pageID
        self.trackViews[ pageID ] = {}
        for trackID in self.pagePlayer.trackIDs:
            trackView = TrackView( trackID, self.beatsPerPageAdjustment )
            self.trackViews[ pageID ][ trackID ] = trackView
        
        self.pagePlayer.addPage( pageID )
        self.pagePlayer.setPlayPage( pageID )
        self.pageBankView.addPage( pageID, False )
        
    def addPageCallback( self, widget = None, event = None,  ):
        self.addPage()
        
    # handle resize (TODO: this could probably be done more efficiently)
    def handleConfigureEvent( self, widget, event ):
        mainBoxRect = self.trackPagesBox.get_allocation()
        
        self.tuneView.set_size_request( mainBoxRect.width, GUIConstants.PAGE_HEIGHT + 
                                                           self.tuneView.get_hscrollbar().get_allocation().height + 10 )
        self.tuneView.show_all()
    
        self.pageBankView.set_size_request( mainBoxRect.width, GUIConstants.PAGE_HEIGHT * GUIConstants.NUMBER_OF_PAGE_BANK_ROWS )
        self.pageBankView.show_all()
        
        mainViewRect = self.mainView.get_allocation()
        
        #TODO: why do we specify mainViewRect.height - 4?  should this be a constant?
        # this logic (width/height realtive to parent) should probably be inside PositionIndicator
        self.positionIndicator.set_size_request( 3, max(0, mainViewRect.height - 4) )
        
        self.backgroundView.set_size_request( mainViewRect.width, mainViewRect.height )
        
        self.trackControlsBox.set_size_request( 100, mainViewRect.height )

    #-----------------------------------
    # access functions (not sure if this is the best way to go about doing this)
    #-----------------------------------
    def getVolume( self ):
        return round( self.volumeAdjustment.value, 0 )

    def getTempo( self ):
        return round( self.tempoAdjustment.value, 0 )

    def getBeatsPerPage( self ):
        return int(round( self.beatsPerPageAdjustment.value, 0 ))

    def getWindowTitle( self ):
        return "Tam-Tam [Volume %i, Tempo %i, Beats/Page %i]" % ( self.volumeAdjustment.value, self.getTempo(), self.getBeatsPerPage() )
