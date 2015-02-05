#!/usr/bin/env python3

import sys
import re

exception = [
    "across",
    "between",
    "in",
    "and",
    "of"
]

def check_style(pn):
    def log(pn, ln, line):
        if line.startswith("%"):
            return
        print("%s:%s %s" % (pn, ln, line.strip()))

    for (ln, line) in enumerate(open(pn)):
        m = re.search("subsection{([^}]+)}", line)
        if m:
            title = m.groups()[0]
            for w in title.split():
                if w != w.capitalize() \
                    and w != w.upper() \
                    and w not in exception:
                    log(pn, ln, line)
                    break
            continue
        
        m = re.search("PP{([^}]+)}", line)
        if m:
            title = m.groups()[0]
            if title != title.capitalize() \
               and title.upper() != title:
                log(pn, ln, line)
            if title.strip()[-1] != ".":
                log(pn, ln, line)

        m = re.search(r"[^~ ]\\cite{", line)
        if m:
            log(pn, ln, line)
            continue
        
        if " ~\\cite{" in line:
            log(pn, ln, line)
            continue

        if "Table~\\" in line:
            log(pn, ln, line)
            continue
        
for pn in sys.argv[1:]:
    check_style(pn)