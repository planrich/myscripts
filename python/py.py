#! /usr/bin/env python

from __future__ import with_statement
from fabric.api import settings, run, local, env, cd
import fabric
import sys
import click

PYPY_HOME="/home/rich/src/pypy"

#fabric.state.output.stdout = False
#fabric.state.output.running = False

def pypy_home():
    return cd(PYPY_HOME)

@click.group()
@click.option('--host', default='192.168.0.3')
def cli(host):
    env.host_string = host
    env.hosts = [host]

@click.command()
def status():
    with pypy_home():
        took = run("""ps -o 'time,cmd' -a | grep 'pypystandalone.py' | cut -c1-9""").strip()
        took = took.replace("00:00:00","").strip()
        if took != "":
            print "process running %s" % (took,)
        else:
            print "no process running"

@click.command()
@click.option('--branch', default='vecopt-merge')
@click.option('--debug/--no-debug', default=False)
def build(branch, debug):
    with pypy_home():
        local_id = local("hg id -i", capture=True)
        run("hg pull")
        run("hg update %s --clean" % branch)
        remote_id = run("hg id -i")
        if remote_id != local_id:
            print "remote has version %s != %s (local)!" % (remote_id, local_id)
        else:
            print "building %s" % remote_id
            args = ""
            if debug:
                args += ' --lldebug'
            run("tmux new-session -s pypy -c /home/rich/src/pypy -d 'pypy rpython/bin/rpython -Ojit %s pypy/goal/targetpypystandalone.py'" % args)

@click.command()
@click.option('--path', default='rpython/jit/backend')
def s390x(path):
    local_path = "/hom/rich/src/pypy-s390x/" + path
    local("rsync -avz {local_path} s390x:pypy/{path}"
          " --exclude='*.orig' --exclude='*~' --exclude='*.pyc'" \
          .format(local_path=local_path, path=path))
    with pypy_home():
        run("py.test rpython/jit")


cli.add_command(s390x)
cli.add_command(status)
cli.add_command(build)

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
