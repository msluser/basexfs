#!/usr/bin/python

#    Copyright (C) 2001  Jeff Epler  <jepler@unpythonic.dhs.org>
#    Copyright (C) 2006  Csaba Henk  <csaba.henk@creo.hu>
#
#    This program can be distributed under the terms of the GNU LGPL.
#    See the file COPYING.
#

import os, sys
from errno import *
from stat import *
import fcntl
import time
import fuse
from fuse import Fuse




def flag2mode(flags):
    md = {os.O_RDONLY: 'r', os.O_WRONLY: 'w', os.O_RDWR: 'w+'}
    m = md[flags & (os.O_RDONLY | os.O_WRONLY | os.O_RDWR)]

    if flags | os.O_APPEND:
        m = m.replace('w', 'a', 1)
        pass
    return m

class File(object):

    def __init__(self, path, flags, *mode):
        self.path = path
        self.fd = os.open("." + path, flags, *mode)
        pass

    def read(self, length, offset):
        os.lseek(self.fd, offset, os.SEEK_SET)
        result = os.read(self.fd, length)
        return result
    
    def write(self, buf, offset):
        os.lseek(self.fd, offset, os.SEEK_SET)
        result = os.write(self.fd, buf)
        return result

    def release(self, flags):
        os.close(self.fd)
        pass
    
    def flush(self):
        os.fsync(self.fd)
        pass
    
    def fgetattr(self):
        return os.fstat(self.fd)

    def ftruncate(self, len):
        os.ftruncate(self.fd, len)
        pass
    
    def lock(self, cmd, owner, **kw):
        # The code here is much rather just a demonstration of the locking
        # API than something which actually was seen to be useful.

        # Advisory file locking is pretty messy in Unix, and the Python
        # interface to this doesn't make it better.
        # We can't do fcntl(2)/F_GETLK from Python in a platfrom independent
        # way. The following implementation *might* work under Linux. 
        #
        # if cmd == fcntl.F_GETLK:
        #     import struct
        # 
        #     lockdata = struct.pack('hhQQi', kw['l_type'], os.SEEK_SET,
        #                            kw['l_start'], kw['l_len'], kw['l_pid'])
        #     ld2 = fcntl.fcntl(self.fd, fcntl.F_GETLK, lockdata)
        #     flockfields = ('l_type', 'l_whence', 'l_start', 'l_len', 'l_pid')
        #     uld2 = struct.unpack('hhQQi', ld2)
        #     res = {}
        #     for i in xrange(len(uld2)):
        #          res[flockfields[i]] = uld2[i]
        #  
        #     return fuse.Flock(**res)
        
        # Convert fcntl-ish lock parameters to Python's weird
        # lockf(3)/flock(2) medley locking API...
        op = { fcntl.F_UNLCK : fcntl.LOCK_UN,
               fcntl.F_RDLCK : fcntl.LOCK_SH,
               fcntl.F_WRLCK : fcntl.LOCK_EX }[kw['l_type']]
        if cmd == fcntl.F_GETLK:
            return -EOPNOTSUPP
        elif cmd == fcntl.F_SETLK:
            if op != fcntl.LOCK_UN:
                op |= fcntl.LOCK_NB
                pass
            pass
        elif cmd == fcntl.F_SETLKW:
            pass
        else:
            return -EINVAL

        fcntl.lockf(self.fd, op, kw['l_start'], kw['l_len'])
        pass

    pass

class Analyze(Fuse):

    def __init__(self, *args, **kw):

        Fuse.__init__(self, *args, **kw)

        # do stuff to set up your filesystem here, if you want
        #import thread
        #thread.start_new_thread(self.mythread, ())
        self.root = '/'
        self.file_class = File

#    def mythread(self):
#
#        """
#        The beauty of the FUSE python implementation is that with the python interp
#        running in foreground, you can have threads
#        """
#        print "mythread: started"
#        while 1:
#            time.sleep(120)
#            print "mythread: ticking"

    def getattr(self, path):
        return os.lstat("." + path)

    def readlink(self, path):
        return os.readlink("." + path)

    def readdir(self, path, offset):
        for e in os.listdir("." + path):
            yield fuse.Direntry(e)

    def unlink(self, path):
        os.unlink("." + path)

    def rmdir(self, path):
        os.rmdir("." + path)

    def symlink(self, path, path1):
        os.symlink(path, "." + path1)

    def rename(self, path, path1):
        os.rename("." + path, "." + path1)

    def link(self, path, path1):
        os.link("." + path, "." + path1)

    def chmod(self, path, mode):
        os.chmod("." + path, mode)

    def chown(self, path, user, group):
        os.chown("." + path, user, group)

    def truncate(self, path, len):
        f = open("." + path, "a")
        f.truncate(len)
        f.close()

    def mknod(self, path, mode, dev):
        os.mknod("." + path, mode, dev)

    def mkdir(self, path, mode):
        os.mkdir("." + path, mode)

    def utime(self, path, times):
        os.utime("." + path, times)

#    The following utimens method would do the same as the above utime method.
#    We can't make it better though as the Python stdlib doesn't know of
#    subsecond preciseness in acces/modify times.
#  
#    def utimens(self, path, ts_acc, ts_mod):
#      os.utime("." + path, (ts_acc.tv_sec, ts_mod.tv_sec))

    def access(self, path, mode):
        if not os.access("." + path, mode):
            return -EACCES

#    This is how we could add stub extended attribute handlers...
#    (We can't have ones which aptly delegate requests to the underlying fs
#    because Python lacks a standard xattr interface.)
#
#    def getxattr(self, path, name, size):
#        val = name.swapcase() + '@' + path
#        if size == 0:
#            # We are asked for size of the value.
#            return len(val)
#        return val
#
#    def listxattr(self, path, size):
#        # We use the "user" namespace to please XFS utils
#        aa = ["user." + a for a in ("foo", "bar")]
#        if size == 0:
#            # We are asked for size of the attr list, ie. joint size of attrs
#            # plus null separators.
#            return len("".join(aa)) + len(aa)
#        return aa

    def statfs(self):
        """
        Should return an object with statvfs attributes (f_bsize, f_frsize...).
        Eg., the return value of os.statvfs() is such a thing (since py 2.2).
        If you are not reusing an existing statvfs object, start with
        fuse.StatVFS(), and define the attributes.

        To provide usable information (ie., you want sensible df(1)
        output, you are suggested to specify the following attributes:

            - f_bsize - preferred size of file blocks, in bytes
            - f_frsize - fundamental size of file blcoks, in bytes
                [if you have no idea, use the same as blocksize]
            - f_blocks - total number of blocks in the filesystem
            - f_bfree - number of free blocks
            - f_files - total number of file inodes
            - f_ffree - nunber of free file inodes
        """

        return os.statvfs(".")

    def fsinit(self):
        os.chdir(self.root)


def main():
    usage = """
Userspace nullfs-alike: mirror the filesystem tree from some point on.
""" + Fuse.fusage

    fs = Analyze(version="%prog " + fuse.__version__,
                 usage=usage)

    fs.parser.add_option(mountopt="root",
                         metavar="PATH",
                         default='/',
                         help="mirror filesystem under PATH [%default]")
    fs.parse(values=fs, errex=1)

    try:
        if fs.fuse_args.mount_expected():
            os.chdir(fs.root)
    except OSError:
        print >> sys.stderr, "can't enter root of underlying filesystem"
        sys.exit(1)

    fs.main()


if __name__ == '__main__':
    fuse.fuse_python_api = (0, 2)
    fuse.feature_assert('stateful_files', 'has_init')
    main()
