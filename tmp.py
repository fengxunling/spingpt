import napari
viewer = napari.Viewer()

@viewer.bind_key('r')
def record_timestamp(viewer):
    print(f"Recording started at: {datetime.now()}")