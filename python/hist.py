#! /usr/bin/env python3

import os
import sys

from datetime import datetime, time, timedelta

def main():
    startdate_str = sys.argv[1]
    startdate = datetime.strptime(startdate_str, "%Y-%m-%d")
    days = int(sys.argv[2])

    for i in range(1,days+1):
        since = startdate + timedelta(days=i-1)
        before = startdate + timedelta(days=i)
        since_s = datetime.strftime(since, "%Y-%m-%d")
        before_s = datetime.strftime(before, "%Y-%m-%d")
        print("##", since_s, "- spent X h")
        print()
        os.system(" ".join(["git", "log", "--since", since_s, "--before", before_s, "--author Richard", "--pretty='format:* **%h** [%aD] master: %s'"]))
        print()

if __name__ == "__main__":
    main()
