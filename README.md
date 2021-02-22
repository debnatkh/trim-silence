# trim-silence
This script can be used to trim silence from video.

It detects silent (configured by `SILENCE_THRESH` param) parts, whose duration exceeds `MIN_SILENCE_LEN` ms. 
If there are k nonsilent parts, i.e. [a1:b1], [a2:b2], ..., [ak:bk], then the resulting video is a concatenation of 
parts [a1-m:b1+m], [a2-m:b2+m], ..., [ak-m,bk+m], where m = `MARGIN`.

In order to bypass some limitations `N_SEGMENTS` = 10 is used, which means that the input video will be split into 
`N_SEGMENTS` chunks firstly, then each chunk processed independently and in the end all results will be concatenated.

## Usage:
```
usage: main.py [-h] -i INFILE [-o OUTFILE] [-s MIN_SILENCE_LEN] [-t SILENCE_THRESH] [-m MARGIN]
               [-n N_SEGMENTS] [-d]

Trim silence from video.

optional arguments:
  -h, --help            show this help message and exit
  -i INFILE, -input INFILE
                        input file
  -o OUTFILE, -output OUTFILE
                        output file
  -s MIN_SILENCE_LEN    min_silence_len (ms), default = 300
  -t SILENCE_THRESH     silence threshold, default = -16
  -m MARGIN             margin (ms), default = 100
  -n N_SEGMENTS         number of chunks to split input file to be processed independently
                        default = 10
  -d                    print debugging info
```

## Example:

```python3 main.py -i lect1.mp4 -o lect1_trimmed.mp4 -d ```
