"""
blank.py

Blank remix template.
Dependencies:
    Remixer
    lame (command line binary)
"""

from remixer import *

class Blank(Remixer):
    def remix(self):
        """
            Remixing happens here. Take your input file from self.infile and write your remix to self.outfile.
            If necessary, self.tempfile can be used for temp files. 
        """
        open(self.outfile, 'w').write(open(self.infile).read())

if __name__ == "__main__":
    CMDRemix(Blank)

