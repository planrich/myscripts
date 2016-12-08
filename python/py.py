#! /usr/bin/env python3.5

from __future__ import with_statement
import sys
import click
import os
import pyinotify
import asyncio
import threading
import requests
import tempfile

@click.group()
def cli():
    pass

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
@click.option('--host', default='metal')
def build(branch, debug, force, host):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_remote_shell(host, "cd ~/src/pypy && hg pull"))
    loop.run_until_complete(run_remote_shell(host, "cd ~/src/pypy && hg update %s --clean" % branch))

    print("building %s" % branch,)
    options = ""
    package_options = ""
    if debug:
        options = ' --lldebug'
        package_options = "--nostrip"
        print(" + (debug mode)")
    shell_script = """
BUILD_DIR=/home/rich/src/pypy
cd $BUILD_DIR
SCM_ID=$(hg id -i)
pypy rpython/bin/rpython -Ojit {options} pypy/goal/targetpypystandalone.py'
/usr/bin/python ./pypy/tool/release/package.py {package_options} --override_pypy_c ./pypy-c --targetdir ~/build
cp ~/build/pypy-nightly.tar.bz2 ~/build/pypys/pypy-$SCM_ID.tar.bz2
mv ~/build/pypy-nightly.tar.bz2 ~/build/pypys/pypy-latest.tar.bz2

set list (ssh metalmachine "find /tmp -name 'testing_1' 2> /dev/null")
set list (for elem in $list
    echo $elem | perl -n -e '/(\d+)\/testing_1/ && print $1'
end)
set code "/tmp/usession-$branch-$list[1]"
set debug_tar "$home/env/pypys/pypy-debug-$v.tar.bz2"
set newdebug_tar "$home/env/pypys/pypy-debug-newest-build.tar.bz2"
echo "creating $debug_tar from $code/debugcode"
ssh metalmachine "cd $code; rm -rf debugcode ; cp -r testing_1/ debugcode/; tar czf $debug_tar debugcode/*.c"
echo "copying $build -> $newbuild"
ssh metalmachine "cp $build $newbuild"
echo "copying $debug_tar -> $newdebug_tar"
ssh metalmachine "cp $debug_tar $newdebug_tar"
""".format(**locals())

    cmd = "tmux new-session -s pypy -c /home/rich/src/pypy 'pypy rpython/bin/rpython -Ojit {options} pypy/goal/targetpypystandalone.py'".format(**locals())
    loop.run_until_complete(run_remote_shell(host, cmd))
    print("=> success")

async def run_remote_shell(hostname, cmd, retry_count=1):
    cmd = '"' + cmd + '"'
    cmd = ("ssh {hostname} " + cmd).format(hostname=hostname)
    print("$", cmd)
    while retry_count > 0:
        subproc = await asyncio.create_subprocess_shell(cmd)
        returncode = await subproc.wait()
        if returncode == 0:
            return
        retry_count -= 1

    print("ERROR: failed to complete %s" % cmd)

async def run_shell(cmd, retry_count=1, directory=None):
    curdir = os.getcwd()
    if directory:
        os.chdir(directory)
    while retry_count > 0:
        subproc = await asyncio.create_subprocess_shell(cmd)
        returncode = await subproc.wait()
        if returncode == 0:
            return
        retry_count -= 1
    os.chdir(curdir)

    print("ERROR: failed to complete %s" % cmd)

def background_asyncio(loop):
    try:
        loop.run_forever()
    finally:
        loop.close()

@click.command()
@click.option('--rpath', default='')
@click.option('--exclude', default='*.swo,*.swp,*.pyc,*.o,.hg/,_cache/,pypy-c,libpypy-c.so')
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

@click.command()
@click.option('--path', default='.')
@click.option('--branch', default='py3.5')
@click.option('--osnarch', default='linux64')
def py3here(path, branch, osnarch):
    name = "pypy-nightly.tar.bz2"
    name = "pypy-c-jit-latest-{arch}.tar.bz2".format(arch=osnarch)
    tmpdir = tempfile.mkdtemp(suffix="pypy-script")
    loop = asyncio.get_event_loop()
    cmd = "wget http://buildbot.pypy.org/nightly/{branch}/{name}".format(
                      path=path, branch=branch, arch=osnarch, name=name, tmpdir=tmpdir)
    loop.run_until_complete(run_shell(cmd, directory=tmpdir))
    cmd = "tar xf {name}".format(name=name)
    loop.run_until_complete(run_shell(cmd, directory=tmpdir))

    pypyname = None
    for root, dirs, files in os.walk(tmpdir):
        for dir in dirs:
            if "pypy-c-jit" in dir:
                pypyname = dir
                break
        else:
            break

    if pypyname is None:
        raise ValueError("did not find pypy-c-jit-* directory to copy pypy-c and libpypy-c.so")

    cmd = "cp {tmpdir}/{pypyname}/bin/pypy3 {path}/pypy-c".format(tmpdir=tmpdir, pypyname=pypyname, path=path)
    loop.run_until_complete(run_shell(cmd))
    cmd = "cp {tmpdir}/{pypyname}/bin/libpypy-c.so {path}".format(tmpdir=tmpdir, pypyname=pypyname, path=path)
    loop.run_until_complete(run_shell(cmd))

cli.add_command(py3here)
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
