import numpy as np
from fastglycan.delta_window import window_statistics,DeltaWindowObserver


def test_all_channels_and_worst_channel_are_retained():
    z=np.zeros((12,12,3),np.float32);y=z.copy()
    y[:,:,0]=1;y[:,:,1]=np.eye(12);y[2,:,2]=1
    stats=window_statistics(z,y,2)
    assert len(stats['channels'])==3
    assert stats['channels'][0]['r95']==1
    assert stats['channels'][1]['r95']==12
    assert stats['channels'][2]['outside_energy_fraction']==0


def test_depth_selection_does_not_repeat_first_cycle_window():
    observer=DeltaWindowObserver(None)
    for c in (1,2,3,4):
        observer.cycle=c
        assert observer.selected(16)==(c==1)
        assert observer.selected(1)==(c!=1)
    observer.cycle=1
    assert not observer.selected(9)
