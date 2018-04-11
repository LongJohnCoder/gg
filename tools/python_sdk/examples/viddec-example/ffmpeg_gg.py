#! /usr/bin/python

import sys
import os
import glob
import argparse
import numpy as np
import subprocess as sp
from timeit import default_timer as now
from gg_sdk import GG, GGThunk

CMD = "ffmpeg -ss 00:{min}:{sec} -loglevel panic -i {video} -frames:v {numout} frameout%03d_{ofile}.jpg"
CMD_IMREC = "li-static {myimage} inception_v3_2016_08_28_frozen.pb imagenet_slim_labels.txt {myoutput}"
SUFFIX_TO_CLEAR = ['jpg', 'out']

num_out = 2

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--video', '-v', type=str, required=False,
            dest='vidToProcess', default='4kvid', help='Video to process (Def: 4kvid)')
    return parser.parse_args()

def clear_chunks():
    to_delete = []
    for stc in SUFFIX_TO_CLEAR:
        to_delete.extend(glob.glob('*.' + stc))

    for todel in to_delete:
        if os.path.exists(todel):
            os.remove(todel)

def get_dur_fps(myvid):
    cmd = 'ffmpeg -i %s 2>&1 | grep -e "fps" -e "Duration"' % myvid
    process = sp.Popen(cmd, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    out, _ = process.communicate()
    out_split = out.decode('utf-8').split()
    duration = out_split[out_split.index('Duration:') + 1].strip(',')
    duration_split = duration.split(':')
    tot_seconds = float(duration_split[0])*3600.0 + float(duration_split[1])*60.0 + float(duration_split[2])

    print("Total duration: %s (%.3f seconds)" % (duration, tot_seconds))
    return tot_seconds

def main(args):
    vidStart = args.vidToProcess
    all_chunks = glob.glob(vidStart + '_chunk*')

    # Get all durations
    all_dur = {}
    for ac in all_chunks:
        ts = get_dur_fps(ac)
        if ts > 4:
          all_dur[ac] = ts

    gg = GG()
    all_thunks = []

    start = now()
    all_count = 0
    for myvid in all_chunks:
        if myvid not in all_dur:
          continue
        vid_dur = int(all_dur[myvid])
        for vd in np.arange(0, vid_dur, 0.04 + 0.04 * num_out):
          next_min = '%02d' % int(vd / 60)
          next_sec = '%.2f' % (vd % 60)
          all_outname = []
          for j in range(num_out):
              all_outname.append('frameout%03d_%03d.jpg' % (j + 1, all_count))

          next_cmd = CMD.format(video=myvid, min=next_min, sec=next_sec,
              numout=num_out, ofile='%03d' % all_count)
          next_cmd_split = next_cmd.split()
          gen_jpg_thunk = GGThunk(exe=next_cmd_split[0], outname=all_outname,
                  exe_args=next_cmd_split[1:], args_infiles=False)
          gen_jpg_thunk.add_infile(myvid)

          for j in range(num_out): 
              pic_out = 'frameout%03d_%03d_lab.out' % (j + 1, all_count)
              all_count += 1

              last_cmd = CMD_IMREC.format(myimage=all_outname[j], myoutput=pic_out)
              last_cmd_split = last_cmd.split()
              last_thunk = GGThunk(exe=last_cmd_split[0], outname=pic_out,
                      exe_args=last_cmd_split[1:], args_infiles=False)
              last_thunk.add_infile(['inception_v3_2016_08_28_frozen.pb',
                      'imagenet_slim_labels.txt', (gen_jpg_thunk, all_outname[j])])

              all_thunks.append(last_thunk)

    end = now()
    delta = end - start
    print("Total time to declare thunks: %.3f seconds" % delta)
    gg.create_thunks(all_thunks)

if __name__ == '__main__':
    clear_chunks()
    parsed_args = get_args()
    start = now()
    main(parsed_args)
    end = now()
    delta = end - start
    print("Total runtime: %.3f seconds" % delta)

