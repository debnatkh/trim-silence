# trim-silence
## Usage:
```
usage: main.py [-h] -i INFILE [-o OUTFILE] [-s MIN_SILENCE_LEN] [-t SILENCE_THRESH] [-m MARGIN] [-d]

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
  -d                    print debugging info
```

## Example:

```python3 main.py -i lect1.mp4 -o lect1_trimmed.mp4 -d```
