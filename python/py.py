#! /usr/bin/env python3.5

from __future__ import with_statement
import sys
import click
import os
import pyinotify
import asyncio
import threading
import requests

@click.group()
@click.option('--host', default='192.168.0.3')
def cli(host):
    pass
    #env.host_string = host
    #env.hosts = [host]

@click.command()
@click.option('--branch', default=None)
@click.option('--builder', default=None)
def bbot(branch, builder):
    assert branch is not None
    assert builder is not None
    args = {
        "forcescheduler": "Force Scheduler",
        "username": "plan_rich",
        "reason": "force build",
        "branch": branch
    }
    requests.post('http://buildbot.pypy.org/builders/{builder}/force'.format(builder=builder), data=args)
    #    set url (echo $result | awk -F '[\']' '{gsub(/\.\.\//,"",$2); print $2}')
    # print("success => http://buildbot.pypy.org/$url")


@click.command()
def status():
    from fabric.api import settings, run, local, env, cd
    with pypy_home():
        took = run("""ps -o 'time,cmd' -a | grep 'pypystandalone.py' | cut -c1-9""").strip()
        took = took.replace("00:00:00","").strip()
        if took != "":
            print("process running %s" % (took,))
        else:
            print("no process running")

@click.command()
@click.option('--branch', default='')
@click.option('--debug/--no-debug', default=False)
@click.option('--force/--no-force', default=False)
def build(branch, debug, force):
    remote_id = run_remote_shell(hostname, "hg id -i")
    if branch != "":
        local_id = run_shell(hostname, "hg id -i")
        run_remote_shell(hostname, "hg pull")
        run_remote_shell(hostname, "hg update %s --clean" % branch)
        if remote_id != local_id and not force:
            print("ERROR: remote has version %s != %s (local)!" % (remote_id, local_id))
            return

    print("building %s" % remote_id,)
    args = ""
    if debug:
        args += ' --lldebug'
        print("(debug mode)",)
    print()
    cmd = "tmux new-session -s pypy -c /home/rich/src/pypy -d 'pypy rpython/bin/rpython -Ojit %s pypy/goal/targetpypystandalone.py'" % args
    run_remote_shell(hostname, cmd)

async def run_remote_shell(hostname, cmd, retry_count=1):
    cmd = ("ssh {hostname} -c " + cmd).format(hostname=hostname)
    while retry_count > 0:
        subproc = await asyncio.create_subprocess_shell(cmd)
        returncode = await subproc.wait()
        if returncode == 0:
            return
        retry_count -= 1

    print("ERROR: failed to complete %s" % cmd)

async def run_shell(cmd, retry_count=1):
    while retry_count > 0:
        subproc = await asyncio.create_subprocess_shell(cmd)
        returncode = await subproc.wait()
        if returncode == 0:
            return
        retry_count -= 1

    print("ERROR: failed to complete %s" % cmd)

def background_asyncio(loop):
    try:
        loop.run_forever()
    finally:
        loop.close()

@click.command()
@click.option('--rpath', default='')
@click.option('--exclude', default='*.swo,*.swp,*.pyc,*.o,.hg/,_cache/')
@click.argument('hostname')
def sync(rpath, hostname, exclude):
    rsync_path = os.path.dirname(rpath)
    excludes = exclude.split(",")
    path = os.getcwd()
    cmd = "rsync -avz {path} {hostname}:{rsync_path} "
    cmd += ' '.join(['--exclude=\'%s\'' % (e,) for e in excludes])

    # first sync
    command = cmd.format(**locals())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_shell(command))

    def sync_file(hostname, path, remote_path):
        if os.path.exists(path):
            print("starting run_shell", path, "to", remote_path)
            loop = asyncio.get_event_loop()
            loop.run_until_complete(run_shell("scp {path} {hostname}:{remote_path}".format(**locals()), retry_count=10))

    threading.Thread(target=background_asyncio, args=(loop,))

    class SyncHandler(pyinotify.ProcessEvent):
        def __init__(self, hostname, remote_path):
            self.hostname = hostname
            self.remote_path = remote_path

        def process_IN_CLOSE_WRITE(self, event):
            remote_path = os.path.join(self.remote_path, os.path.relpath(event.pathname))
            sync_file(self.hostname, event.pathname, remote_path)

    # continous sync
    wm = pyinotify.WatchManager()
    wm.add_watch(path, pyinotify.ALL_EVENTS, rec=True)

    # event handler
    eh = SyncHandler(hostname, rpath)

    # notifier
    notifier = pyinotify.Notifier(wm, eh)
    notifier.loop()

cli.add_command(sync)
cli.add_command(status)
cli.add_command(build)
cli.add_command(bbot)

if __name__ == "__main__":
    cli()


#    case 'build'
#        set branch (hg branch)
#        set init "cd ~/src/pypy"
#        ssh metalmachine "$init; hg pull"
#        ssh metalmachine "$init; hg update $branch --clean"
#        set id (ssh metalmachine "$init; hg id -i")
#        set lid (hg id -i)
#        if test $id = $lid
#            echo "building pypy version $id"
#            ssh metalmachine "tmux new-session -s pypy -c /home/rich/src/pypy -d 'pypy rpython/bin/rpython -Ojit --lldebug pypy/goal/targetpypystandalone.py'"
#        else
#            echo "remote has older/other version than local $id != $lid"
#        end
#    case 'pkg'
#        set v (ssh metalmachine "cd ~/src/pypy; hg id -i")
#        echo "packaging version $v..."
#        set newbuild "~/env/pypys/pypy-newest-build.tar.bz2"
#        set build "~/env/pypys/pypy-$v.tar.bz2"
#        ssh metalmachine "cd ~/src/pypy ; /usr/bin/python ./pypy/tool/release/package.py --nostrip --override_pypy_c ./pypy-c --targetdir ~/env/ --without-tk"
#        ssh metalmachine "mv ~/env/pypy-nightly.tar.bz2 $build"
#
#        set list (ssh metalmachine "find /tmp -name 'testing_1' 2> /dev/null")
#        set list (for elem in $list
#            echo $elem | perl -n -e '/(\d+)\/testing_1/ && print $1'
#        end)
#        set code "/tmp/usession-$branch-$list[1]"
#        set debug_tar "$home/env/pypys/pypy-debug-$v.tar.bz2"
#        set newdebug_tar "$home/env/pypys/pypy-debug-newest-build.tar.bz2"
#        echo "creating $debug_tar from $code/debugcode"
#        ssh metalmachine "cd $code; rm -rf debugcode ; cp -r testing_1/ debugcode/; tar czf $debug_tar debugcode/*.c"
#        echo "copying $build -> $newbuild"
#        ssh metalmachine "cp $build $newbuild"
#        echo "copying $debug_tar -> $newdebug_tar"
#        ssh metalmachine "cp $debug_tar $newdebug_tar"
#    case 'load'
#        set host 'metalmachine'
#        rsync -azrve ssh $host:~/env/pypys ~/env
#        echo -n 'unpacking...'
#        pushd .
#        cd ~/env/
#        trash pypy-nightly
#        trash debugcode
#        tar xf pypys/pypy-newest-build.tar.bz2
#        tar xf pypys/pypy-debug-newest-build.tar.bz2
#        echo 'done'
#        popd
#    case 'check'
#        switch $argv[2]
#        case all
#            set targets "own-linux-x86-64 pypy-c-jit-linux-x86-64"
#        case own
#            set targets "own-linux-x86-64"
#        case jit
#            set targets "pypy-c-jit-linux-x86-64"
#        case app
#            set targets "pypy-c-app-level-linux-x86-64"
#        case *
#            echo 'usage: $ py check [all,<target>]'
#            exit 1
#        end
#
#        for target in $targets
#           set result (curl -s -X POST --data \
#                    "forcescheduler=Force+Scheduler&username=plan_rich&reason=force+build&branch=$branch" http://buildbot.pypy.org/builders/$target/force)
#
#            set url (echo $result | awk -F '[\']' '{gsub(/\.\.\//,"",$2); print $2}')
#
#            echo "success => http://buildbot.pypy.org/$url"
#        end
#    case *
#        echo 'usage> py <status|build>'
#    end
#end
