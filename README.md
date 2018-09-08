# KeepToOrg
Convert Google Keep notes to Emacs .org files

Usage:
`python KeepToOrg.py /path/to/google/Keep output/dir`

Given a Takeout of your Google Keep Notes in .html format, output .org files with logical groupings 
based on tags. This will also format lists and try to be smart.

Go to [Google Takeout](https://takeout.google.com/settings/takeout) to download your Keep data. Extract the data and run this script on it.

Note that the dates used to sort the notes can be out of order. After investigating, the dates in the note .html files themselves appear to be wrong. I think this is Google's fault.