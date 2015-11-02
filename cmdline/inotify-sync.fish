inotifywait -r -m -e close_write --format '%w%f' --exclude "\.hg/" ~/src/pypy | while read MODFILE;
                             if test -e $MODFILE;
                                 scp $MODFILE s390x:$MODFILE
                             end
                         end
