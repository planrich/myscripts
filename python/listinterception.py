        class InterceptList(object):
            def __init__(self, items):
                self.items = items
            def __setitem__(self, k, v):
                print "ssss setting", k, "=", v
                self.items[k] = v
            def __getitem__(self, k):
                return self.items[k]
            def __iter__(self):
                return self.items.__iter__()
        assert loop1.operations[2].getfailargs()[0] is loop1.operations[1]
        guard = loop1.operations[2]
        print "failargs ", guard.getfailargs(), loop1.operations[1]
        args = InterceptList(guard.getfailargs())
        guard.setfailargs(args)
        guard.copy = lambda self: self
        def setargs(args):
            if isinstance(args, InterceptList):
                args = args.items
            print "set args!!!! ", args
            import pdb; pdb.set_trace()
            guard._fail_args = InterceptList(args)
        def copy():
            return InterceptList(guard._fail_args.items)
        guard.setfailargs = setargs
        guard.getfailargs_copy = copy

