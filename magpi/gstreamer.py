import sys
from functools import partial

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstBase', '1.0')

from gi.repository import GLib, GObject, Gst, GstBase
from PIL import Image

GObject.threads_init()
Gst.init(None)

SRC_WIDTH =  640
SRC_HEIGHT = 480
SRC_RATE = '30/1'
SRC_ELEMENT = 'v4l2src'

SINK_WIDTH = 320
SINK_HEIGHT = 180
SINK_ELEMENT = 'appsink name=appsink sync=false emit-signals=true max-buffers=1 drop=true'

DL_CAPS = 'video/x-raw,format=RGBA,width={width},height={height}'
SINK_CAPS = 'video/x-raw,format=RGB,width={width},height={height}'
LEAKY_Q = 'queue max-size-buffers=1 leaky=downstream'

# Use this for Raspberry Pi camera
SRC_CAPS = 'video/x-raw,format=RGB,width={width},height={height},framerate={rate}'
PIPELINE = '''
    {src_element} ! {src_caps} ! {leaky_q} !  
    tee name=t
    t. ! {leaky_q} ! videoconvert ! videoscale ! {sink_caps} ! {sink_element}
    '''
#    t. ! {leaky_q} ! videoconvert ! rsvgoverlay name=overlay ! videoconvert ! ximagesink 

# Use this for enterprise camera
#SRC_CAPS = 'video/x-raw,format=YUY2,width={width},height={height},framerate={rate}'
#PIPELINE = '''
#    {src_element} ! {src_caps} ! {leaky_q} ! glupload ! tee name=t
#    t. ! {leaky_q} ! glfilterbin filter=glcolorscale ! rsvgoverlay name=overlay ! videoconvert ! ximagesink 
#    t. ! {leaky_q} ! glfilterbin filter=glcolorscale ! {dl_caps} !
#        videoconvert ! {sink_caps} ! {sink_element}
#'''

def on_bus_message(bus, message, loop):
    t = message.type
    if t == Gst.MessageType.EOS:
        loop.quit()
    elif t == Gst.MessageType.WARNING:
        err, debug = message.parse_warning()
        sys.stderr.write('Warning: %s: %s\n' % (err, debug))
    elif t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        sys.stderr.write('Error: %s: %s\n' % (err, debug))
        loop.quit()
    return True

def on_new_sample(sink, overlay, user_function):
    sample = sink.emit('pull-sample')
    buf = sample.get_buffer()
    result, mapinfo = buf.map(Gst.MapFlags.READ)
    if result:
      img = Image.frombytes('RGB', (SINK_WIDTH, SINK_HEIGHT), mapinfo.data, 'raw')
      quit = user_function(img, overlay)
      if quit: return Gst.FlowReturn.EOS
    buf.unmap(mapinfo)
    return Gst.FlowReturn.OK

def run_pipeline(user_function):
    src_caps = SRC_CAPS.format(width=SRC_WIDTH, height=SRC_HEIGHT, rate=SRC_RATE)
    dl_caps = DL_CAPS.format(width=SINK_WIDTH, height=SINK_HEIGHT)
    sink_caps = SINK_CAPS.format(width=SINK_WIDTH, height=SINK_HEIGHT)
    pipeline = PIPELINE.format(leaky_q=LEAKY_Q, src_element=SRC_ELEMENT,
        src_caps=src_caps, dl_caps=dl_caps, sink_caps=sink_caps,
        sink_element=SINK_ELEMENT)
    print(pipeline)

    pipeline = Gst.parse_launch(pipeline)

    overlay = pipeline.get_by_name('overlay')
    appsink = pipeline.get_by_name('appsink')
    appsink.connect('new-sample', partial(on_new_sample,
        overlay=overlay, user_function=user_function))

    loop = GObject.MainLoop()

    # Set up a pipeline bus watch to catch errors.
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect('message', on_bus_message, loop)

    # Run pipeline.
    pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except:
        pass

    # Clean up.
    pipeline.set_state(Gst.State.NULL)
    while GLib.MainContext.default().iteration(False):
        pass
